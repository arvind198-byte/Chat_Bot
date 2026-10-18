# Placement Cell Virtual Assistant (BCS515B Phase 1)

A customized domain virtual assistant developed for the Department of Training and Placement as part of **Project-Based Learning for BCS515B – Artificial Intelligence (Semester V)**.

This repository implements a full-stack, decoupled architecture featuring a **FastAPI** Python backend, a **React (Vite)** frontend, and an embedded **SQLite3** database for conversation persistence, telemetry tracking (latency and token counts), and user feedback logging.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Intelligent Agent Specification (PEAS)](#intelligent-agent-specification-peas)
- [4-Layer Customization Architecture](#4-layer-customization-architecture)
- [Tech Stack and Constraints](#tech-stack-and-constraints)
- [Directory Structure](#directory-structure)
- [Database Schema](#database-schema)
- [API Specification](#api-specification)
- [Frontend Architecture](#frontend-architecture)
- [Setup and Installation](#setup-and-installation)
- [Running the Application](#running-the-application)
- [Testing and Verification](#testing-and-verification)
- [Context and Guidelines for Future AI Agents](#context-and-guidelines-for-future-ai-agents)

---

## Project Overview

The Placement Cell Virtual Assistant is designed to address student inquiries regarding campus recruitment drives, company eligibility criteria, interview procedures, backlog policies, and company tier classifications.

### Key Functional Capabilities
- **Multi-turn conversation management** without artificial truncation of conversational context.
- **Strict domain grounding** via an external, maintainable knowledge base ([`backend/knowledge.txt`](file:///c:/Users/ARVIND%20RATHOR%20B/OneDrive/Desktop/ChatBot/backend/knowledge.txt)).
- **Out-of-scope refusal handling** to prevent casual misuse or assignment assistance.
- **Safety and anti-hallucination protocols**: zero job guarantees or selection predictions; standardized fallbacks for unlisted personal records.
- **Telemetry logging**: real-time calculation and database persistence of round-trip API latency (`latency_ms`) and token consumption (`tokens_used`).
- **Interactive message feedback**: discrete thumbs-up / thumbs-down rating persisted in SQLite.
- **Professional, clean user interface**: typography-focused, responsive React interface completely free of emojis.

---

## Intelligent Agent Specification (PEAS)

Under artificial intelligence agent modeling guidelines (Russell & Norvig):

- **Performance Measure (P)**: 
  - Accuracy and factual consistency with institutional placement policies.
  - Zero generation of false job guarantees or invented cutoffs.
  - Latency under 5 seconds per query (achieved ~1.8s - 2.2s).
  - Out-of-scope inquiry rejection rate.
  - Student satisfaction ratings (+1 / -1 feedback).
- **Environment (E)**: 
  - College placement portal, prospective recruitment applicants, registered placement drives, company tier matrices, and institutional academic regulations.
- **Actuators (A)**: 
  - FastAPI HTTP response payloads, Streamlit/React chat message bubbles, metric annotations (`latency_ms`, `tokens_used`), and database mutation operations.
- **Sensors (S)**: 
  - Web UI text input submissions, conversational message history arrays, feedback button interactions, and configuration environment variables.

### Environment Properties
- **Partially Observable**: The agent sees user text submissions and session context, but not real-time recruiter decisions or external student portal records.
- **Deterministic**: Given identical knowledge and low temperature (`0.2`), answers are repeatable and policy-bound.
- **Sequential**: Previous conversation turns inform context for subsequent answers.
- **Static**: The institutional knowledge base does not mutate during an individual query.
- **Discrete**: Operations occur in discrete request/response turns.
- **Single-Agent**: Functions as an independent advisory assistant.

---

## 4-Layer Customization Architecture

All system behavior is governed by the 4-layer prompt engineering architecture configured in [`backend/bot.py`](file:///c:/Users/ARVIND%20RATHOR%20B/OneDrive/Desktop/ChatBot/backend/bot.py):

| Layer | Responsibility | Implementation Details |
| :--- | :--- | :--- |
| **1. Persona** | Identity, voice, and style | Official Virtual Assistant for the Campus Placement Cell. Objective, supportive, and professional. **Strictly no emojis** in the interface or output. |
| **2. Domain Knowledge** | Factual grounding | Structured facts loaded dynamically from [`backend/knowledge.txt`](file:///c:/Users/ARVIND%20RATHOR%20B/OneDrive/Desktop/ChatBot/backend/knowledge.txt) at startup. Covers CGPA benchmarks, backlog rules, company tiers, and drive steps. |
| **3. Scope Control** | Boundary enforcement | Handles campus recruitment inquiries only. Explicitly declines general trivia, coding assignments, homework, and non-placement requests. |
| **4. Safety & Honesty** | Risk mitigation & fallback | Explicitly disclaims job guarantees. Selection is at employer discretion. If in-domain data is missing from the knowledge base, uses the exact fallback string:<br>`"I do not have specific records for this inquiry. Please contact the Placement Cell directly at placement@college.edu or visit the Placement Office."` |

---

## Tech Stack and Constraints

- **Backend**: Python 3.10+, FastAPI, Uvicorn, SQLite3, `python-dotenv`.
- **LLM Engine**: Google GenAI SDK (`google-genai`), using model `gemini-3.5-flash-lite` (selected for low latency, high throughput, and zero 503 capacity issues).
- **Frontend**: React 18, Vite 6, CSS Modules, `react-markdown`, `remark-gfm`, `react-syntax-highlighter`.
- **Course & Academic Constraints**:
  - **No LangChain or LlamaIndex**: Orchestration, message transformation, and context management are written entirely from scratch in native Python.
  - **No Storing Personal Identifying Information**: The database logs session queries and metrics; no names, USNs, or passwords are requested or collected.
  - **Single Source of Truth**: All domain facts reside in [`backend/knowledge.txt`](file:///c:/Users/ARVIND%20RATHOR%20B/OneDrive/Desktop/ChatBot/backend/knowledge.txt), not hardcoded in application logic.

---

## Directory Structure

```text
ChatBot/
├── backend/
│   ├── main.py              # FastAPI application & REST route handlers
│   ├── bot.py               # Prompt compilation, LLM calls, latency & token tracking
│   └── knowledge.txt        # Official institutional placement policy document
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.jsx          # Conversation sidebar & new inquiry trigger
│   │   │   ├── Sidebar.module.css
│   │   │   ├── MessageList.jsx      # Message rendering, metrics row & feedback buttons
│   │   │   ├── MessageList.module.css
│   │   │   ├── ChatInput.jsx        # Auto-resizing textarea with Enter-to-submit
│   │   │   └── ChatInput.module.css
│   │   ├── api.js                   # Unified fetch API client
│   │   ├── App.jsx                  # Main application state & inquiry coordinator
│   │   ├── App.module.css           # Layout and clean branding styles
│   │   ├── index.css                # CSS variables, typography, and theme tokens
│   │   └── main.jsx                 # React DOM mount point
│   ├── vite.config.js       # Vite build config with /api -> :8000 reverse proxy
│   └── package.json         # Frontend dependencies and npm scripts
├── bot.py                   # Root wrapper re-exporting backend.bot
├── database.py              # SQLite CRUD operations, connection management & migrations
├── chatbot.db               # SQLite database file (auto-generated, excluded by git)
├── test_database.py         # Unit tests for database schemas and CRUD behavior
├── test_api.py              # Unit tests for FastAPI endpoints with mock LLM calls
├── .env                     # Private environment variables (API keys)
├── .gitignore               # Ignores .env, *.db, node_modules/, dist/, etc.
├── requirements.txt         # Python package dependencies
└── README.md                # Comprehensive documentation
```

---

## Database Schema

The database ([`chatbot.db`](file:///c:/Users/ARVIND%20RATHOR%20B/OneDrive/Desktop/ChatBot/chatbot.db)) is initialized and managed by [`database.py`](file:///c:/Users/ARVIND%20RATHOR%20B/OneDrive/Desktop/ChatBot/database.py). Foreign keys are enabled on every connection via `PRAGMA foreign_keys = ON`.

```sql
-- Conversations Table
CREATE TABLE IF NOT EXISTS chats (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Message Turn Log Table
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER NOT NULL,
    role        TEXT NOT NULL,               -- 'user' or 'assistant'
    content     TEXT NOT NULL,
    latency_ms  INTEGER DEFAULT 0,          -- API turn latency in milliseconds
    tokens_used INTEGER DEFAULT 0,          -- Model token usage
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
);

-- Interactive User Feedback Table
CREATE TABLE IF NOT EXISTS feedback (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,            -- Associated assistant message
    rating     INTEGER NOT NULL,            -- +1 for helpful, -1 for unhelpful
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
);
```

---

## API Specification

The FastAPI backend serves routes under `/api`:

### 1. `GET /api/status`
Returns service availability, active model ID, and assistant configuration.
- **Response `200`**:
  ```json
  {
    "model": "gemini-3.5-flash-lite",
    "api_configured": true,
    "assistant_name": "Placement Cell Virtual Assistant"
  }
  ```

### 2. `GET /api/chats`
Lists all conversations sorted by `updated_at DESC`.
- **Response `200`**: Array of `{"id": int, "title": str, "created_at": str, "updated_at": str}`

### 3. `POST /api/chats`
Initializes a new conversation.
- **Request Body**: `{"title": "New Inquiry"}`
- **Response `201`**: `{"id": int, "title": str}`

### 4. `DELETE /api/chats/{chat_id}`
Deletes a conversation along with its messages and feedback records.
- **Response `204`**: No Content.

### 5. `GET /api/chats/{chat_id}/messages`
Retrieves all chronological message turns for a conversation.
- **Response `200`**: Array of:
  ```json
  [
    {
      "id": 1,
      "chat_id": 1,
      "role": "user",
      "content": "What is the minimum CGPA for Tier 1 drives?",
      "latency_ms": 0,
      "tokens_used": 0,
      "created_at": "2026-10-11 11:30:00"
    },
    {
      "id": 2,
      "chat_id": 1,
      "role": "assistant",
      "content": "Tier 1 Super Dream drives typically require 8.00 CGPA...",
      "latency_ms": 1920,
      "tokens_used": 142,
      "created_at": "2026-10-11 11:30:02"
    }
  ]
  ```

### 6. `POST /api/chats/{chat_id}/messages`
Submits a user query, generates a model response with latency & token usage, and persists both turns atomically.
- **Request Body**: `{"content": "Do I qualify if I have 1 active backlog?"}`
- **Response `200`**:
  ```json
  {
    "id": 4,
    "role": "assistant",
    "content": "Active backlogs restrict candidates from Tier 1 drives...",
    "latency_ms": 2040,
    "tokens_used": 168,
    "created_at": "2026-10-11 11:30:02",
    "user_message_id": 3,
    "user_created_at": "2026-10-11 11:30:00"
  }
  ```

### 7. `POST /api/feedback`
Submits a user rating for an assistant response.
- **Request Body**: `{"message_id": 4, "rating": 1}`
- **Response `201`**: `{"status": "success", "feedback_id": 1}`

---

## Setup and Installation

### Prerequisites
- Python 3.10 or higher.
- Node.js v18+ and npm.
- A valid Gemini API Key from [Google AI Studio](https://aistudio.google.com/app/apikey).

### 1. Environment Configuration
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_actual_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
```

### 2. Backend Dependencies
Install required Python packages:
```powershell
pip install -r requirements.txt
```

### 3. Frontend Dependencies
Install React packages:
```powershell
cd frontend
npm install
cd ..
```

---

## Running the Application

To run the application locally, start the backend and frontend in separate terminals:

### Terminal 1: Backend Server (FastAPI)
```powershell
python -m uvicorn backend.main:app --port 8000 --reload
```
- Backend REST API: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`

### Terminal 2: Frontend Client (React)
```powershell
cd frontend
npm run dev
```
- Open your browser at **`http://localhost:5173`**.

---

## Testing and Verification

### 1. Database Unit Tests
Validates database schema creation, CRUD operations, cascade deletions, and metadata columns:
```powershell
python test_database.py
```
*Expected: 11/11 tests pass.*

### 2. API & Integration Unit Tests
Validates FastAPI endpoints, status checks, mocked model generation, token/latency responses, and feedback logging:
```powershell
python test_api.py
```
*Expected: 4/4 tests pass.*

### 3. Frontend Production Build Check
Validates JSX syntax, CSS Modules, and build bundling:
```powershell
cd frontend
npm run build
cd ..
```
*Expected: Vite builds `dist/` cleanly without errors.*

---

## Context and Guidelines for Future AI Agents

If another AI assistant or developer is modifying this codebase, heed the following rules:

1. **Do Not Revert to Heavy LLMs**: The model is set to `gemini-3.5-flash-lite` in [`backend/bot.py`](file:///c:/Users/ARVIND RATHOR B/OneDrive/Desktop/ChatBot/backend/bot.py). Do not switch to `gemini-3.8-flash` or `gemini-2.5-flash` unless verified to be active and non-throttled, as they introduce `503 High Demand` errors and 15+ second retry delays.
2. **Preserve the 4 Customization Layers**: Do not remove the system prompt structure in [`backend/bot.py`](file:///c:/Users/ARVIND%20RATHOR%20B/OneDrive/Desktop/ChatBot/backend/bot.py). Faculty evaluation requires Persona, Custom Knowledge, Scope Control, and Safety/Honesty rules.
3. **Keep Interface Clean & Emoji-Free**: Do not introduce emojis or decorative icons into `frontend/src/` or the prompt templates. The evaluation criteria mandate an objective, professional demeanor.
4. **Knowledge Base Updates**: When updating placement rules or dates, edit [`backend/knowledge.txt`](file:///c:/Users/ARVIND%20RATHOR%20B/OneDrive/Desktop/ChatBot/backend/knowledge.txt) directly. Do not hardcode rules inside Python code.
5. **No Orchestration Frameworks**: Do not install LangChain, LlamaIndex, or agentic frameworks. The project is explicitly marked down if custom orchestrators replace direct SDK usage.
