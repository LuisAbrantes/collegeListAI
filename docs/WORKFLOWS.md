# College List AI - Workflow Documentation

## User Workflows

### 1. New User Onboarding

```mermaid
flowchart TD
    Start([User visits app]) --> Auth{Authenticated?}
    
    Auth -->|No| SignUp[Sign Up / Login]
    SignUp --> CheckProfile{Has Profile?}
    
    Auth -->|Yes| CheckProfile
    
    CheckProfile -->|No| ShowForm[Show Onboarding Form]
    ShowForm --> FillForm[User fills:<br/>- Nationality<br/>- GPA<br/>- Major]
    FillForm --> Validate{Valid?}
    
    Validate -->|No| ShowError[Show Validation Errors]
    ShowError --> FillForm
    
    Validate -->|Yes| CreateProfile[POST /api/profiles]
    CreateProfile --> Success{Success?}
    
    Success -->|No| ShowAPIError[Show Error Message]
    ShowAPIError --> FillForm
    
    Success -->|Yes| LoadChat[Load Chat Interface]
    
    CheckProfile -->|Yes| LoadChat
    
    LoadChat --> Ready([Ready to Chat])
    
    style CreateProfile fill:#d4edda
    style LoadChat fill:#d4edda
```

---

### 2. University Search & Recommendation

```mermaid
flowchart TD
    Start([User in Chat]) --> Type[User types query]
    Type --> Send[Click Send]
    
    Send --> ShowLoading[Show loading indicator]
    ShowLoading --> API[POST /api/recommend/stream]
    
    API --> SSE{SSE Connection}
    
    SSE --> Stream[Receive text chunks]
    Stream --> Display[Display streaming text]
    Display --> More{More chunks?}
    
    More -->|Yes| Stream
    More -->|No| Complete[Stream complete]
    
    Complete --> Parse[Parse recommendations]
    Parse --> RenderCards[Render College Cards]
    
    RenderCards --> ShowSources[Show grounding sources]
    ShowSources --> UserAction{User Action}
    
    UserAction -->|Click source| OpenURL[Open source URL]
    UserAction -->|Exclude college| AddExclusion[POST /api/exclusions]
    UserAction -->|New query| Type
    UserAction -->|Done| End([End])
    
    AddExclusion --> UpdateUI[Update UI]
    UpdateUI --> UserAction
    
    style API fill:#e8f4f8
    style Stream fill:#fef3cd
    style RenderCards fill:#d4edda
```

---

### 3. Cache Management Workflow

```mermaid
flowchart TD
    Query[User Query Received] --> CheckCache{Check Vector Cache}
    
    CheckCache --> GenEmbed[Generate Query Embedding<br/>text-embedding-004]
    GenEmbed --> VectorSearch[Cosine Similarity Search<br/>pgvector]
    
    VectorSearch --> Results{Results Found?<br/>Similarity > 0.7?}
    
    Results -->|Yes, sufficient| ReturnCache[Return Cached Results]
    ReturnCache --> End([Response Sent])
    
    Results -->|No / Insufficient| SearchWeb[Gemini Search Grounding]
    SearchWeb --> WebResults[Get Live University Data]
    
    WebResults --> ProcessResults[Process Search Results]
    ProcessResults --> GenDocEmbed[Generate Document Embeddings]
    
    GenDocEmbed --> StoreCache[Store in colleges_cache<br/>with embeddings]
    StoreCache --> ReturnFresh[Return Fresh Results]
    
    ReturnFresh --> End
    
    style CheckCache fill:#e8f4f8
    style VectorSearch fill:#e8f4f8
    style SearchWeb fill:#fef3cd
    style StoreCache fill:#d4edda
```

---

### 4. Profile Update Workflow

```mermaid
stateDiagram-v2
    [*] --> ViewingProfile: Click Profile
    
    ViewingProfile --> EditMode: Click Edit
    
    EditMode --> ChangingNationality: Update Nationality
    EditMode --> ChangingGPA: Update GPA
    EditMode --> ChangingMajor: Update Major
    
    ChangingNationality --> EditMode
    ChangingGPA --> EditMode
    ChangingMajor --> EditMode
    
    EditMode --> Validating: Click Save
    
    Validating --> ValidationError: Invalid Data
    ValidationError --> EditMode: Show Errors
    
    Validating --> Saving: Valid Data
    Saving --> APICall: PATCH /api/profiles/me
    
    APICall --> SaveError: API Error
    SaveError --> EditMode: Show Error
    
    APICall --> SaveSuccess: Success
    SaveSuccess --> ViewingProfile: Profile Updated
    
    ViewingProfile --> [*]: Close
```

---

### 5. Exclusion Management

```mermaid
flowchart LR
    subgraph "View Exclusions"
        Start([User clicks Exclusions]) --> Load[GET /api/exclusions]
        Load --> Display[Display List]
    end
    
    subgraph "Add Exclusion"
        College[College Card] --> Exclude[Click Exclude Button]
        Exclude --> Confirm{Confirm?}
        Confirm -->|Yes| Add[POST /api/exclusions]
        Confirm -->|No| Cancel([Cancel])
        Add --> UpdateList[Refresh List]
    end
    
    subgraph "Remove Exclusion"
        Display --> Remove[Click Remove]
        Remove --> Delete[DELETE /api/exclusions/:name]
        Delete --> UpdateList
    end
    
    UpdateList --> Display
    
    style Add fill:#d4edda
    style Delete fill:#f8d7da
```

---

## Backend Workflows

### 6. Embedding Generation Workflow

```mermaid
flowchart TD
    Input[Text Input] --> Validate{Valid Text?}
    
    Validate -->|No| Error[Throw EmbeddingGenerationError]
    Validate -->|Yes| Truncate[Truncate to 10k chars]
    
    Truncate --> CallAPI[Call google.genai<br/>embed_content]
    
    CallAPI --> Retry{Success?}
    
    Retry -->|Rate Limit| Wait[Exponential Backoff]
    Wait --> CallAPI
    
    Retry -->|Transient Error| Wait2[Retry with Backoff]
    Wait2 --> CallAPI
    
    Retry -->|Fatal Error| Error
    
    Retry -->|Success| CheckDim{Dimension = 768?}
    
    CheckDim -->|No| Warn[Log Warning]
    CheckDim -->|Yes| Return[Return Embedding]
    
    Warn --> Return
    
    style CallAPI fill:#e8f4f8
    style Wait fill:#fef3cd
    style Return fill:#d4edda
```

---

### 7. Search Grounding Workflow

```mermaid
sequenceDiagram
    participant API
    participant GeminiService
    participant GenAI as google.genai Client
    participant Gemini as Gemini 2.5 Flash
    participant Search as Google Search

    API->>GeminiService: generate_recommendations_with_search()
    
    GeminiService->>GeminiService: Build prompt with profile
    GeminiService->>GenAI: generate_content(tools=[GoogleSearch])
    
    GenAI->>Gemini: Send prompt
    Gemini->>Gemini: Analyze query
    Gemini->>Search: Execute search queries
    
    Note over Search: Searches for:<br/>- University rankings<br/>- Admission stats<br/>- Financial aid policies
    
    Search-->>Gemini: Search results
    Gemini->>Gemini: Synthesize recommendations
    Gemini-->>GenAI: Response + grounding_metadata
    
    GenAI-->>GeminiService: GenerateContentResponse
    
    GeminiService->>GeminiService: Extract grounding_sources
    GeminiService->>GeminiService: Parse JSON response
    
    GeminiService-->>API: {recommendations, sources, queries}
```

---

### 8. Error Handling Workflow

```mermaid
flowchart TD
    Request[API Request] --> Try{Try Operation}
    
    Try -->|Success| Response[Return Response]
    
    Try -->|ValidationError| Val[400 Bad Request]
    Try -->|NotFoundError| NF[404 Not Found]
    Try -->|RateLimitError| RL[429 Too Many Requests]
    Try -->|AIServiceError| AI[500 Internal Server Error]
    Try -->|DatabaseError| DB[500 Internal Server Error]
    Try -->|UnknownError| Unknown[500 Internal Server Error]
    
    Val --> Log[Log Error]
    NF --> Log
    RL --> Log
    AI --> Log
    DB --> Log
    Unknown --> Log
    
    Log --> ErrorResponse[Return Error JSON]
    
    ErrorResponse --> Client[Client Receives Error]
    Client --> Display[Display Error Message]
    
    style Val fill:#fef3cd
    style NF fill:#fef3cd
    style RL fill:#f8d7da
    style AI fill:#f8d7da
    style DB fill:#f8d7da
```

---

## Development Workflows

### 9. Local Development Setup

```mermaid
flowchart TD
    Start([Clone Repository]) --> Backend[Setup Backend]
    Start --> Frontend[Setup Frontend]
    
    Backend --> VEnv[Create venv]
    VEnv --> InstallDeps[pip install -r requirements.txt]
    InstallDeps --> EnvVars[Set .env variables]
    EnvVars --> RunBackend[uvicorn app.main:app --reload]
    
    Frontend --> NPMInstall[npm install]
    NPMInstall --> FrontendEnv[Set .env variables]
    FrontendEnv --> RunFrontend[npm run dev]
    
    RunBackend --> TestAPI[Test API at localhost:8000/docs]
    RunFrontend --> TestUI[Test UI at localhost:5173]
    
    TestAPI --> Ready([Development Ready])
    TestUI --> Ready
    
    style RunBackend fill:#d4edda
    style RunFrontend fill:#d4edda
```

---

### 10. Deployment Workflow

```mermaid
flowchart LR
    subgraph "Code Changes"
        Dev[Local Development] --> Commit[Git Commit]
        Commit --> Push[Git Push]
    end
    
    subgraph "CI/CD"
        Push --> Tests[Run Tests]
        Tests --> Build[Build Application]
        Build --> Deploy{Deploy?}
    end
    
    subgraph "Deployment"
        Deploy -->|Backend| DeployAPI[Deploy to Cloud Run]
        Deploy -->|Frontend| DeployUI[Deploy to Vercel]
        Deploy -->|Database| Migrate[Run Migrations]
    end
    
    subgraph "Verification"
        DeployAPI --> HealthCheck[Health Check]
        DeployUI --> E2E[E2E Tests]
        Migrate --> Verify[Verify Schema]
    end
    
    HealthCheck --> Live([Production Live])
    E2E --> Live
    Verify --> Live
    
    style Tests fill:#e8f4f8
    style Build fill:#fef3cd
    style Live fill:#d4edda
```
