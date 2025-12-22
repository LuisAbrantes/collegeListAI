# Engineering Standards & Clean Code

## 🧱 Architecture
- **Domain Layer:** Pure Python logic and Pydantic models. No dependencies on frameworks.
- **Infrastructure Layer:** Database clients (Supabase), AI Graph (LangGraph), and external tools.
- **API Layer:** FastAPI routes and controllers.

## 🔄 State Management
- **Backend:** LangGraph `StateGraph` with checkpointers for conversation persistence.
- **Frontend:** Context API for user profile and Zustand for ephemeral UI states (modals, loaders).

## 🚀 Performance & Scalability
- **Streaming:** Use Server-Sent Events (SSE) to stream Agent steps to the UI.
- **Caching:** Implement Redis to cache university data and search results.
- **Async:** Non-blocking calls for all AI and Database operations.