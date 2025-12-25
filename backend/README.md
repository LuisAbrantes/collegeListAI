# College List AI - Backend Documentation

## 🚀 Overview
The backend is built with FastAPI and LangGraph, implementing a **Smart Sourcing RAG Pipeline**. The core feature is a **Major-Segmented Cache** that optimizes university data retrieval based on specific student majors.

---

## 🛠 Maintenance Commands (Chat Interface)
You can force the system to bypass the cache and fetch fresh data from the web using maintenance intents. This is useful for clearing stale data or forcing a deep research phase for a specific major.

### High-Priority Maintenance Keywords
| Language | Examples |
|----------|----------|
| **Portuguese** | `"atualizar banco"`, `"buscar dados reais"`, `"buscar novos dados"`, `"forçar atualização"`, `"limpar cache"` |
| **English** | `"refresh database"`, `"update db"`, `"force refresh"`, `"clear cache"`, `"fetch real data"` |

**Example Usage:**
- *"Atualize o banco de dados para Ciência da Computação"*
- *"Force refresh the database for Physics"*

When these keywords are detected, the system sets `force_refresh = True`, triggers **Phase 2 (Web Discovery)**, and updates the cache with fresh findings.

---

## 💾 Database & Migrations
We use Alembic for schema migrations.

### Apply Latest Migrations
```bash
# From the backend directory
source venv/bin/activate
alembic upgrade head
```

### Major Change: 0006_major_segmented_cache
This migration transition from a single-entry cache to a major-segmented approach:
- **Composite Unique Key**: `(name, target_major)` ensures MIT-Physics doesn't overwrite MIT-CS.
- **Performance Indexes**: 
  - `ix_colleges_cache_target_major`: For major filtering.
  - `ix_colleges_cache_major_updated`: Composite index for high-speed staleness checks.

---

## 🧪 Testing

### Run All Tests
```bash
source venv/bin/activate
python -m pytest tests/unit/ -v
```

### Specific Major-Segmented Cache Tests
```bash
python -m pytest tests/unit/test_major_segmented_cache.py -v
```

---

## 🏛 Architecture: Smart Sourcing RAG
1. **Phase 1 (Cache)**: Checks `colleges_cache` for the specific `target_major`.
2. **Phase 2 (Discovery)**: If cache is empty or stale, triggers LLM Grounding (Gemini/Ollama).
3. **Phase 3 (Flywheel)**: Auto-populates cache with results from Phase 2.
4. **Phase 4 (Scoring)**: Combined results are passed to the MatchScorer.

---

## 🤖 LLM Configuration

### Switching Providers
Set `LLM_PROVIDER` in your `.env`:
```bash
# Use cloud (Gemini)
LLM_PROVIDER=gemini

# Use local (Ollama)  
LLM_PROVIDER=ollama
```

### Switching Gemini Models
Set `GEMINI_MODEL` in your `.env`:
```bash
# Current options:
GEMINI_MODEL=gemini-1.5-flash      # Fast, cost-effective
GEMINI_MODEL=gemini-1.5-pro        # More capable
GEMINI_MODEL=gemini-2.0-flash      # Default - fast + grounding
GEMINI_MODEL=gemini-2.0-flash-exp  # Experimental

# Future (when available):
GEMINI_MODEL=gemini-3.0-flash
```

### Switching Ollama Models
```bash
OLLAMA_MODEL=gemma3:27b   # Current default
OLLAMA_MODEL=llama3:8b    # Alternative
```

---

## 📦 Tech Stack
- **Framework**: FastAPI
- **Orchestration**: LangGraph
- **Database**: PostgreSQL (Supabase) + SQLModel
- **AI**: Google Generative AI (Gemini 1.5/2.0) / Ollama
