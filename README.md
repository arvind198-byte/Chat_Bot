# Son of Anton — Gemini Chatbot

A local Gemini chatbot with a React web interface, FastAPI backend, and SQLite conversation storage.

## Features

- React chat interface with Markdown-formatted assistant messages.
- Create, select, and delete conversations.
- Persistent chats and messages stored in SQLite.
- Automatic chat titles based on the first user message.
- Recent conversation context sent to Gemini while the full conversation remains stored.
- API errors are reported to the UI; unsuccessful Gemini calls do not save a partial exchange.
- A command-line chatbot remains available with `python bot.py`.
- The previous Streamlit interface remains available as an optional compatibility entry point with `streamlit run app.py`.

## Tech stack

- Python 3.10+
- FastAPI and Uvicorn
- Google GenAI SDK (`google-genai`)
- SQLite
- React 18 and Vite

## Project structure

```text
ChatBot/
├── backend/
│   └── main.py                 # FastAPI routes and Gemini integration
├── frontend/
│   ├── src/
│   │   ├── components/         # Chat sidebar, messages, and input
│   │   ├── api.js              # API client
│   │   └── App.jsx             # React application
│   ├── package.json
│   └── vite.config.js          # Development proxy to FastAPI
├── bot.py                      # Gemini client and history helpers
├── database.py                 # SQLite persistence
├── test_api.py                 # FastAPI endpoint tests
├── test_database.py            # SQLite tests
├── requirements.txt
└── .env                        # Local Gemini API key (not committed)
```

## Setup

1. Install Python 3.10 or newer and Node.js.
2. Install backend dependencies from the project root:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Install frontend dependencies:

   ```powershell
   cd frontend
   npm install
   cd ..
   ```

4. Create a `.env` file in the project root with your Gemini API key:

   ```env
   GEMINI_API_KEY=your_actual_api_key
   ```

   Keep this file private; it is excluded by `.gitignore`.

## Run the application

Open two terminals from the project root.

Start the backend in the first terminal:

```powershell
python -m uvicorn backend.main:app --reload --port 8000
```

Start the frontend in the second terminal:

```powershell
cd frontend
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). Vite forwards `/api` requests to the FastAPI server on `127.0.0.1:8000`.

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/status` | Report model and API-key configuration status |
| `GET` | `/api/chats` | List conversations |
| `POST` | `/api/chats` | Create a conversation |
| `DELETE` | `/api/chats/{chat_id}` | Delete a conversation and its messages |
| `GET` | `/api/chats/{chat_id}/messages` | Get conversation history |
| `POST` | `/api/chats/{chat_id}/messages` | Send a message and receive a Gemini response |

## Tests and build

Run the SQLite and API tests from the project root:

```powershell
python test_database.py
python -m unittest -v test_api
```

Build the frontend:

```powershell
cd frontend
npm run build
```

The API tests use a temporary database and mocked Gemini responses; they do not need a valid API key or make external API calls.

## Data and configuration

The app creates `chatbot.db` in the project root. The database and `.env` are ignored by Git. The Gemini model and conversation context window are configured in `bot.py`.
