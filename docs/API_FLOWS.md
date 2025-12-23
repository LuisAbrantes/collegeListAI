# College List AI - API Flow Documentation

## API Request/Response Flows

### 1. Profile Creation Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant ProfileService
    participant Supabase
    participant Auth

    Client->>FastAPI: POST /api/profiles
    Note over Client: Headers:<br/>Authorization: Bearer {token}
    Note over Client: Body:<br/>{nationality, gpa, major}
    
    FastAPI->>FastAPI: Extract user_id from JWT
    FastAPI->>ProfileService: create_profile(user_id, data)
    
    ProfileService->>Supabase: SELECT * FROM profiles WHERE user_id = ?
    
    alt Profile Already Exists
        Supabase-->>ProfileService: Existing profile
        ProfileService-->>FastAPI: DuplicateError
        FastAPI-->>Client: 409 Conflict
    else Profile Doesn't Exist
        Supabase-->>ProfileService: No results
        ProfileService->>Supabase: INSERT INTO profiles
        Supabase-->>ProfileService: New profile
        ProfileService-->>FastAPI: UserProfile
        FastAPI-->>Client: 201 Created + Profile JSON
    end
```

---

### 2. Vector Search Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant VectorService
    participant GenAI
    participant Supabase

    Client->>FastAPI: POST /api/search
    Note over Client: Body:<br/>{query, threshold, limit}
    
    FastAPI->>VectorService: search_similar_colleges()
    
    VectorService->>VectorService: generate_query_embedding(query)
    VectorService->>GenAI: embed_content(model, text)
    GenAI-->>VectorService: embedding[768]
    
    VectorService->>Supabase: RPC match_colleges(embedding, threshold, limit)
    
    Note over Supabase: SELECT id, name, content,<br/>1 - (embedding <=> query) as similarity<br/>FROM colleges_cache<br/>WHERE 1 - (embedding <=> query) > threshold<br/>ORDER BY similarity DESC<br/>LIMIT limit
    
    Supabase-->>VectorService: Results[]
    
    VectorService->>VectorService: Parse metadata
    VectorService->>VectorService: Filter exclusions
    
    VectorService-->>FastAPI: CollegeSearchResult[]
    FastAPI-->>Client: 200 OK + Results JSON
```

---

### 3. AI Recommendation with Search Grounding

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant GeminiService
    participant VectorService
    participant GenAI
    participant GoogleSearch
    participant Supabase

    Client->>FastAPI: POST /api/recommend
    Note over Client: Body:<br/>{query, nationality,<br/>gpa, major, excluded_colleges}
    
    FastAPI->>VectorService: search_similar_colleges()
    VectorService-->>FastAPI: cached_colleges[]
    
    FastAPI->>GeminiService: generate_recommendations_with_search()
    
    GeminiService->>GeminiService: Build prompt with profile + cache
    
    GeminiService->>GenAI: generate_content(tools=[GoogleSearch])
    
    GenAI->>GoogleSearch: Execute search queries
    Note over GoogleSearch: Searches for:<br/>- "best CS universities for [nationality]"<br/>- "university admission stats [gpa]"<br/>- "financial aid [nationality]"
    
    GoogleSearch-->>GenAI: Search results
    GenAI->>GenAI: Synthesize recommendations
    GenAI-->>GeminiService: Response + grounding_metadata
    
    GeminiService->>GeminiService: Extract sources
    GeminiService->>GeminiService: Parse JSON
    
    GeminiService-->>FastAPI: {recommendations, sources, queries}
    
    loop For each new university
        FastAPI->>VectorService: cache_university_from_search()
        VectorService->>GenAI: embed_content()
        GenAI-->>VectorService: embedding
        VectorService->>Supabase: UPSERT colleges_cache
    end
    
    FastAPI-->>Client: 200 OK + Recommendations JSON
```

---

### 4. SSE Streaming Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant GeminiService
    participant GenAI

    Client->>FastAPI: POST /api/recommend/stream
    Note over Client: Accept: text/event-stream
    
    FastAPI->>FastAPI: Create EventSourceResponse
    FastAPI-->>Client: 200 OK (SSE connection open)
    
    FastAPI->>GeminiService: stream_recommendations()
    
    GeminiService->>GenAI: generate_content_stream(tools=[GoogleSearch])
    
    loop For each chunk
        GenAI-->>GeminiService: chunk.text
        GeminiService-->>FastAPI: yield chunk
        FastAPI-->>Client: event: chunk<br/>data: {"text": "..."}
    end
    
    GeminiService-->>FastAPI: Stream complete
    FastAPI-->>Client: event: complete<br/>data: {"status": "done"}
    
    FastAPI-->>Client: Close SSE connection
```

---

### 5. Exclusion Management Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Supabase

    Note over Client,Supabase: Add Exclusion
    
    Client->>FastAPI: POST /api/exclusions
    Note over Client: Headers: Authorization<br/>Body: {college_name}
    
    FastAPI->>FastAPI: Extract user_id from JWT
    FastAPI->>Supabase: INSERT INTO user_exclusions
    Note over Supabase: (user_id, college_name)
    
    alt Success
        Supabase-->>FastAPI: Inserted row
        FastAPI-->>Client: 201 Created + Exclusion JSON
    else Duplicate
        Supabase-->>FastAPI: Unique constraint violation
        FastAPI-->>Client: 409 Conflict
    end
    
    Note over Client,Supabase: Remove Exclusion
    
    Client->>FastAPI: DELETE /api/exclusions/{college_name}
    FastAPI->>FastAPI: Extract user_id from JWT
    FastAPI->>Supabase: DELETE FROM user_exclusions<br/>WHERE user_id = ? AND college_name = ?
    
    Supabase-->>FastAPI: Deleted
    FastAPI-->>Client: 204 No Content
```

---

## Error Handling Flows

### 6. Rate Limit Handling

```mermaid
flowchart TD
    Request[API Request] --> Service[Service Layer]
    
    Service --> APICall[Call External API]
    APICall --> Response{Response Status}
    
    Response -->|200 OK| Success[Return Data]
    Response -->|429 Rate Limit| Retry{Retry Count < 3?}
    
    Retry -->|Yes| Wait[Exponential Backoff<br/>1s, 2s, 4s]
    Wait --> APICall
    
    Retry -->|No| RateLimitError[Throw RateLimitError]
    
    RateLimitError --> Handler[Exception Handler]
    Handler --> LogError[Log Error]
    LogError --> Response429[Return 429 JSON]
    
    Response429 --> Client[Client Receives Error]
    Client --> Display[Display: "Too many requests.<br/>Please try again later."]
    
    style Wait fill:#fef3cd
    style RateLimitError fill:#f8d7da
```

---

### 7. Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Dependency
    participant Supabase

    Client->>FastAPI: Request with Authorization header
    Note over Client: Authorization: Bearer {jwt_token}
    
    FastAPI->>Dependency: get_current_user_id()
    
    alt Valid JWT
        Dependency->>Dependency: Parse JWT
        Dependency->>Dependency: Extract user_id
        Dependency-->>FastAPI: user_id (UUID)
        FastAPI->>FastAPI: Process request
        FastAPI-->>Client: 200 OK + Response
    else Invalid/Missing JWT
        Dependency-->>FastAPI: HTTPException(401)
        FastAPI-->>Client: 401 Unauthorized<br/>{"detail": "Invalid token"}
    end
```

---

## Database Interaction Flows

### 8. Vector Similarity Search (SQL)

```mermaid
flowchart TD
    Input[Query Embedding] --> RPC[RPC: match_colleges]
    
    RPC --> SQL[SQL Function Execution]
    
    SQL --> Compute[Compute Cosine Similarity<br/>1 - (embedding <=> query_embedding)]
    
    Compute --> Filter[Filter by threshold<br/>similarity > match_threshold]
    
    Filter --> Sort[ORDER BY similarity DESC]
    Sort --> Limit[LIMIT match_count]
    
    Limit --> Return[RETURN TABLE<br/>(id, name, content, similarity)]
    
    Return --> Results[Results to Application]
    
    style Compute fill:#e8f4f8
    style Filter fill:#e8f4f8
```

---

### 9. Cache Upsert Flow

```mermaid
flowchart LR
    subgraph "Input"
        Name[University Name]
        Content[Content JSON]
        Embedding[Embedding Vector]
    end
    
    subgraph "Supabase Operation"
        Upsert[UPSERT colleges_cache]
        Conflict{Conflict on name?}
    end
    
    subgraph "Outcome"
        Insert[INSERT new row]
        Update[UPDATE existing row]
    end
    
    Name --> Upsert
    Content --> Upsert
    Embedding --> Upsert
    
    Upsert --> Conflict
    
    Conflict -->|No conflict| Insert
    Conflict -->|Conflict| Update
    
    Insert --> Success([Success])
    Update --> Success
    
    style Insert fill:#d4edda
    style Update fill:#fef3cd
```

---

## Performance Optimization Flows

### 10. Caching Strategy

```mermaid
flowchart TD
    Query[User Query] --> Hash[Generate Query Hash]
    Hash --> CheckCache{Check Cache}
    
    CheckCache -->|Cache Hit<br/>Fresh data| Return[Return Cached Response]
    
    CheckCache -->|Cache Miss| CheckVector{Check Vector DB}
    
    CheckVector -->|Similar results<br/>similarity > 0.7| ReturnVector[Return Vector Results]
    
    CheckVector -->|No similar results| SearchWeb[Gemini Search Grounding]
    SearchWeb --> StoreVector[Store in Vector DB]
    StoreVector --> StoreCache[Store in Response Cache]
    StoreCache --> ReturnFresh[Return Fresh Results]
    
    Return --> End([Response Sent])
    ReturnVector --> End
    ReturnFresh --> End
    
    style Return fill:#d4edda
    style ReturnVector fill:#d4edda
    style SearchWeb fill:#fef3cd
```
