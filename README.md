# AI Learning Assistant - Full-Stack RAG Application

An intelligent, local-first learning companion that generates personalized study roadmaps, suggests tailored hands-on capstone projects, and provides contextual chat assistance with references mapping back to your curriculum. 

---

## Architecture Overview

The system is designed with a local-first philosophy, utilizing a Retrieval-Augmented Generation (RAG) pipeline to keep user data private and run models locally. The frontend communicates securely with the backend via HTTP-only cookies to verify identity and maintain state, protecting credentials from vulnerable LocalStorage-based XSS exploits.

```
       +--------------------------------------------+
       |             Browser Frontend               |
       |  (Next.js App Router, Tailwind, shadcn)   |
       +---------------------+----------------------+
                             |
                             | HTTP / JSON REST
                             v
       +---------------------+----------------------+
       |             FastAPI Backend                |
       |     (Python 3.11, Pydantic Validation)     |
       +----------+----------------------+----------+
                  |                      |
    Query Embed   |                      | Generate Prompt
    & Indexing    v                      v Context
       +----------+----------+     +-----+----------+
       |   Ollama: BGE-M3    |     | Ollama:        |
       |  Embedding Model    |     | Llama 3.2 LLM  |
       +----------+----------+     +----------------+
                  |
                  | Search Docs / Cosine Distances
                  v
       +----------+----------+
       |  ChromaDB Vector    |
       |      Database       |
       +---------------------+
```

---

## Tech Stack

| Layer | Technologies & Tools | Key Role / Purpose |
| :--- | :--- | :--- |
| **Backend** | FastAPI, Python 3.11, Pydantic v2 | High-performance REST API with request/response schema validations. |
| **Security** | python-jose, passlib[bcrypt] | Secure HTTP-only JWT cookies to protect against XSS and stateless authorization. |
| **Local AI** | Ollama, Llama 3.2 (3B), BGE-M3 | Local host for LLM reasoning and dense multilingual text embeddings. |
| **Vector DB** | ChromaDB (Chroma PersistentClient) | Storage and semantic search utilizing cosine similarity search spaces. |
| **Frontend** | Next.js (App Router), TypeScript | Fast, production-optimized React web app utilizing server and client modes. |
| **Styling & UI**| Tailwind CSS v4, shadcn/ui, Lucide | Sleek dark-mode theme, glassmorphism card layouts, responsive modules. |
| **State & Fetch**| React Context, LocalStorage, Sonner | Persistent student roadmap and chatbot context; real-time Toast messages. |

---

## Local Setup (Without Docker)

### 1. Prerequisites
Ensure you have **Python 3.11+**, **Node.js 18+**, and **Ollama** installed on your system.

### 2. Configure and Start Ollama
1. Start the Ollama server:
   ```bash
   ollama serve
   ```
2. Pull the required models:
   ```bash
   ollama pull llama3.2
   ollama pull bge-m3
   ```

### 3. Setup Backend Service
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   # Note: For JWT Authentication, ensure python-jose[cryptography] and passlib[bcrypt] are installed:
   pip install "python-jose[cryptography]" "passlib[bcrypt]"
   ```
4. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   The backend API docs will be accessible at `http://localhost:8000/docs`.

### 4. Setup Frontend Service
1. Navigate to the `frontend/` directory:
   ```bash
   cd ../frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
   Open `http://localhost:3000` in your web browser.

---

## Docker Setup (With Orchestration)

Start the entire system including automated model initialization:

```bash
docker-compose up --build -d
```

- **Next.js Frontend**: Accessible at `http://localhost:3000`
- **FastAPI Backend**: Accessible at `http://localhost:8000`
- **Ollama Engine**: Running internally on port `11434` (with auto-download triggers for Llama 3.2 and BGE-M3 on first run).

---

## API Endpoints

| Endpoint | Method | Request Body | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/auth/register` | `POST` | `{ "username", "password" }` | Create a new user account. |
| `/api/v1/auth/login` | `POST` | `{ "username", "password" }` | Log in, authenticating credentials and setting an HTTP-only JWT cookie. |
| `/api/v1/auth/logout` | `POST` | `None` | Log out by clearing the HTTP-only JWT cookie. |
| `/api/v1/auth/me` | `GET` | `None` | Retrieve the authenticated user's profile details. |
| `/api/v1/roadmap` | `POST` | `{ "goal_title", "experience", "known_skills", "learning_style", "weekly_hours" }` | Generates a structured learning path with estimated hours, target skills, modules, and subtasks. |
| `/api/v1/project` | `POST` | `{ "roadmap_id" }` | Recommends a tailored Capstone project with features, stack, difficulty, and learning outcomes. |
| `/api/v1/chat` | `POST` | `{ "roadmap_id", "message", "conversation_id" }` | Process messages using RAG retrieval over indexed roadmap chunks, keeping conversation history. |

---

## Prompt Design Decisions

- **Strict Structured Outputs**: Prompts define clear JSON schemas. The backend enforces structured responses from Llama 3.2 by declaring return boundaries.
- **BGE-M3 Query Prefixing**: Before embedding chat queries, a retrieval prefix (`Represent this sentence for searching relevant passages: `) is prepended. This optimizes semantic density matching with ChromaDB.
- **Robust JSON Parsing**: To counter JSON fragmentation or markdown code fences generated by local LLMs, the service uses a custom brace-tracking parser (`_extract_balanced_json` / `find_balanced_candidates`) that ignores quote escapes to successfully isolate and validate JSON payloads against Pydantic models.

---

## Product Thinking & Extra UX Features

- **JWT Authentication (Bonus)**: Implemented secure stateless authentication using JWTs stored in HTTP-only cookies to prevent XSS attacks, with a custom FastAPI dependency injector to protect core endpoints.
- **Double-Layer Persistence**: The `AppProvider` React Context auto-saves generated roadmaps and conversation IDs in `localStorage`, maintaining state on client-side page refreshes.
- **Intelligent URL Formatting**: Search resources recommended by the AI are formatted automatically; plain text terms link to custom search engine results, while URL references open official document pages.
- **Relevance Metrics**: Chat citations show actual semantic confidence ratings as visual progress bars, mapping distance thresholds (`score = 1 - cosine_distance`) directly in references.
- **Response Caching**: Fast UI transitions between form generation and dashboards.
- **Clickable Suggestions**: AI follow-up pills automatically trigger new prompts, reducing student typing fatigue.

---

## Development Notes

- **Approximate Time Spent**: `10-12 hours`.
- **AI Coding Assistant Usage**: Open source LLMs was used for initial structuring and debugging; all core logic, RAG pipeline, and prompt engineering were implemented manually.
- **Assumptions Made**: Ollama served locally; ChromaDB persistent sqlite vectors on local storage; stateless authorization.
