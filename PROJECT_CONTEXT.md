# Project Context: College List AI

## 1. Business Logic
College List AI is a specialized advisor. It takes a student's profile (GPA, Nationality, Financial Needs) and generates a balanced college list.

## 2. The Labels (Reach, Target, Safety)
- **Reach:** High competition (Acceptance < 15%) or stats below university average.
- **Target:** Stats aligned with university averages (Acceptance 15-35%).
- **Safety:** Stats clearly above average (Acceptance > 35%).

## 3. Critical Features
- **Nationality-Aware:** Financial aid varies by citizenship. The AI must check if a school is Need-Blind or Need-Aware for the user's specific country.
- **Real-Time Search:** Uses Gemini Search Grounding to find 2025-2026 deadlines.
- **Persistent Threads:** Users can have multiple search conversations.
- **Blacklist:** A global `user_exclusions` list to ensure the AI never suggests unwanted schools.

## 4. Hackathon Goals (Google DeepMind/Gemini)
- Showcase **Search Grounding** for data accuracy.
- Showcase **Long Context** for analyzing multiple university PDFs.
- Showcase **Multimodal** capabilities (parsing transcripts/images).