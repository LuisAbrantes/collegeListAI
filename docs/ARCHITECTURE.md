# College List AI - Architecture Documentation

## System Overview

College List AI is an intelligent college advisor that uses Gemini's Search Grounding to find universities and caches results in a vector database to minimize API costs.

---

## High-Level Architecture

```mermaid
graph TB
    subgraph "Frontend (React + TypeScript)"
        UI[User Interface]
        Auth[Supabase Auth]
        Profile[Profile Management]
        Chat[Chat Interface]
    end
    
    subgraph "Backend (FastAPI)"
        API[FastAPI Routes]
        ProfileSvc[Profile Service]
        GeminiSvc[Gemini Service]
        VectorSvc[Vector Service]
    end
    
    subgraph "External Services"
        Gemini[Google Gemini API]
        Search[Google Search]
        Supabase[(Supabase PostgreSQL + pgvector)]
    end
    
    UI --> Auth
    UI --> Profile
    UI --> Chat
    
    Chat --> API
    Profile --> API
    
    API --> ProfileSvc
    API --> GeminiSvc
    API --> VectorSvc
    
    ProfileSvc --> Supabase
    VectorSvc --> Supabase
    VectorSvc --> Gemini
    
    GeminiSvc --> Gemini
    Gemini --> Search
    
    style Gemini fill:#4285f4,color:#fff
    style Search fill:#4285f4,color:#fff
    style Supabase fill:#3ecf8e,color:#fff
```

---

## Data Flow: University Recommendation

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant GeminiService
    participant VectorService
    participant Supabase
    participant GoogleSearch

    User->>Frontend: "Find CS universities for international students"
    Frontend->>API: POST /api/recommend
    
    API->>VectorService: search_similar_colleges(query)
    VectorService->>VectorService: generate_query_embedding()
    VectorService->>Supabase: RPC match_colleges()
    
    alt Cache Hit (similarity > 0.7)
        Supabase-->>VectorService: Cached universities
        VectorService-->>API: Return cached results
        API-->>Frontend: Recommendations (cached)
    else Cache Miss
        Supabase-->>VectorService: No results / Low similarity
        VectorService-->>API: Empty/insufficient results
        
        API->>GeminiService: generate_recommendations_with_search()
        GeminiService->>GoogleSearch: Search for universities
        GoogleSearch-->>GeminiService: Live search results + sources
        GeminiService-->>API: Recommendations + grounding_sources
        
        API->>VectorService: cache_university_from_search()
        VectorService->>VectorService: generate_document_embedding()
        VectorService->>Supabase: INSERT INTO colleges_cache
        
        API-->>Frontend: Recommendations (fresh)
    end
    
    Frontend-->>User: Display recommendations with sources
```

---

## Vector Search Flow

```mermaid
flowchart TD
    Start[User Query] --> Embed[Generate Query Embedding]
    Embed --> Search[Search pgvector with cosine similarity]
    
    Search --> Check{Results found?<br/>Similarity > threshold?}
    
    Check -->|Yes| Return[Return Cached Results]
    Check -->|No| Grounding[Gemini Search Grounding]
    
    Grounding --> Parse[Parse Search Results]
    Parse --> Cache[Cache in pgvector]
    Cache --> Return
    
    Return --> Display[Display to User]
    
    style Embed fill:#e8f4f8
    style Search fill:#e8f4f8
    style Grounding fill:#fef3cd
    style Cache fill:#d4edda
```

---

## Profile Management Flow

```mermaid
stateDiagram-v2
    [*] --> Unauthenticated
    
    Unauthenticated --> Authenticated: Sign Up / Login
    
    Authenticated --> NoProfile: Check Profile
    Authenticated --> HasProfile: Check Profile
    
    NoProfile --> Onboarding: Show Onboarding Form
    Onboarding --> HasProfile: Create Profile<br/>(nationality, GPA, major)
    
    HasProfile --> Ready: Profile Loaded
    
    Ready --> Chatting: Start Conversation
    Ready --> EditingProfile: Update Profile
    
    EditingProfile --> Ready: Save Changes
    
    Chatting --> Chatting: Send/Receive Messages
    Chatting --> Ready: End Conversation
    
    Ready --> [*]: Logout
```

---

## Gemini Service: Search Grounding

```mermaid
flowchart LR
    subgraph "Input"
        Query[User Query]
        Profile[Student Profile<br/>nationality, GPA, major]
        Exclusions[Blacklisted Schools]
    end
    
    subgraph "Gemini Service"
        Prompt[Build Prompt]
        Config[Configure Search Tool]
        Call[Call Gemini API]
        Parse[Parse Response]
    end
    
    subgraph "Gemini API"
        Model[gemini-2.5-flash]
        SearchTool[Google Search Tool]
    end
    
    subgraph "Output"
        Recommendations[University List<br/>Reach/Target/Safety]
        Sources[Grounding Sources<br/>URLs + titles]
        Queries[Search Queries Used]
    end
    
    Query --> Prompt
    Profile --> Prompt
    Exclusions --> Prompt
    
    Prompt --> Config
    Config --> Call
    
    Call --> Model
    Model --> SearchTool
    SearchTool --> Model
    Model --> Parse
    
    Parse --> Recommendations
    Parse --> Sources
    Parse --> Queries
    
    style SearchTool fill:#4285f4,color:#fff
    style Model fill:#4285f4,color:#fff
```

---

## Database Schema

```mermaid
erDiagram
    profiles ||--o{ user_exclusions : has
    colleges_cache ||--o{ user_exclusions : referenced_by
    
    profiles {
        uuid id PK
        text nationality
        float gpa
        text major
        boolean financial_need
        timestamp created_at
        timestamp updated_at
    }
    
    colleges_cache {
        uuid id PK
        text name UK
        text content
        vector_768 embedding
        timestamp last_updated
    }
    
    user_exclusions {
        uuid user_id FK
        text college_name FK
        timestamp created_at
    }
```

---

## API Endpoints

### Profile Management
```
GET    /api/profiles/me          # Get current user profile
POST   /api/profiles             # Create profile
PATCH  /api/profiles/me          # Update profile
DELETE /api/profiles/me          # Delete profile
```

### Search & Recommendations
```
POST   /api/search               # Vector similarity search
POST   /api/recommend            # AI recommendations (JSON)
POST   /api/recommend/stream     # AI recommendations (SSE)
GET    /api/exclusions           # Get blacklist
POST   /api/exclusions           # Add to blacklist
DELETE /api/exclusions/{name}    # Remove from blacklist
```

---

## Technology Stack

```mermaid
graph LR
    subgraph "Frontend"
        React[React 18]
        TS[TypeScript]
        Vite[Vite]
        Supabase_JS[@supabase/supabase-js]
    end
    
    subgraph "Backend"
        FastAPI[FastAPI]
        Python[Python 3.10+]
        Pydantic[Pydantic v2]
        GenAI[google-genai]
    end
    
    subgraph "Database"
        PostgreSQL[PostgreSQL 15+]
        pgvector[pgvector extension]
    end
    
    subgraph "AI/ML"
        Gemini[Gemini 2.5 Flash]
        Embedding[text-embedding-004]
        SearchAPI[Google Search API]
    end
    
    React --> Supabase_JS
    FastAPI --> GenAI
    FastAPI --> Pydantic
    GenAI --> Gemini
    GenAI --> Embedding
    Gemini --> SearchAPI
    FastAPI --> PostgreSQL
    PostgreSQL --> pgvector
```
