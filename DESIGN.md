# English Learning Coach - Design Notes

## Concept
AI-powered personal English coaching app.
This app acts as a coach (not the learning itself).

## External Tools
- Shadowing: Tedict
- Listening: Podcasts etc.

## Tech Stack
- FastAPI (backend)
- Streamlit (frontend)
- Ollama / llama3.2 (AI)
- SQLite (database)

## Design Policy
- Start simple, add complexity only when needed
- weak_points: stored as plain string for now

## DB Schema
### users
- id, name
- reading/listening/speaking/writing_level (CEFR)
- weak_points (string)
- goal (string)

### learning_logs
- id, user_id, date, menu, completed