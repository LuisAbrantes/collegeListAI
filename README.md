# College List AI

An AI-powered college advisor that builds personalized college lists for students. Features intelligent recommendations, reach/target/safety categorization, and comprehensive financial aid insights including support for international students.

## 📂 Project Structure

- **/backend**: FastAPI server, LangGraph agents, and SQLModel database logic.
- **/frontend**: React (TypeScript) + Tailwind CSS + shadcn/ui interface.
- **/supabase**: Database schema and configuration.

## 🚀 Getting Started

### Backend

1. Go to `backend/` directory.
2. Read [backend/README.md](backend/README.md) for maintenance commands and setup.
3. Apply migrations: `alembic upgrade head`.

### Frontend

1. Go to `frontend/` directory.
2. `npm install` and `npm run dev`.

## 🤖 Core Features

- **Major-Segmented Cache**: Granular data storage per university department.
- **Hybrid Search**: Cache-first strategy with real-time web discovery failsafe.
- **MatchScorer**: AI-driven admissions probability analysis.
- **Financial Fit Logic**: Specialized logic for international student aid.
