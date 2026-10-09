"""
FastAPI backend for the Gemini chatbot.

Endpoints
---------
GET  /api/chats                     – list all chats
POST /api/chats                     – create a new chat
DELETE /api/chats/{chat_id}         – delete a chat and its messages
GET  /api/chats/{chat_id}/messages  – get all messages for a chat
POST /api/chats/{chat_id}/messages  – send a user message and get a response
"""

import os
import logging
from pathlib import Path

from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from google import genai

import database as db
from bot import (
    generate_response,
    messages_to_contents,
    trim_history,
    MODEL,
    MAX_HISTORY,
)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
logger = logging.getLogger(__name__)

# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(title="Gemini Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()

_TITLE_MAX_LEN = 50


# ── Schemas ──────────────────────────────────────────────────────────────────

class CreateChatRequest(BaseModel):
    title: str = Field(default="New Chat", min_length=1, max_length=100)


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/api/chats")
def list_chats():
    return db.get_chats()


@app.post("/api/chats", status_code=201)
def new_chat(body: CreateChatRequest):
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Chat title cannot be empty.")
    chat_id = db.create_chat(title)
    return {"id": chat_id, "title": title}


@app.delete("/api/chats/{chat_id}", status_code=204)
def remove_chat(chat_id: int):
    if not db.delete_chat(chat_id):
        raise HTTPException(status_code=404, detail="Chat not found.")


@app.get("/api/chats/{chat_id}/messages")
def get_messages(chat_id: int):
    if db.get_chat(chat_id) is None:
        raise HTTPException(status_code=404, detail="Chat not found.")
    return db.get_messages(chat_id)


@app.post("/api/chats/{chat_id}/messages")
def send_message(chat_id: int, body: SendMessageRequest):
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    chat = db.get_chat(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found.")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured.")

    history_rows = db.get_messages(chat_id)
    history = [{"role": m["role"], "content": m["content"]} for m in history_rows]
    if not any(message["role"] == "user" for message in history):
        title = content.strip().replace("\n", " ")
        if len(title) > _TITLE_MAX_LEN:
            title = title[:_TITLE_MAX_LEN - 1] + "…"
    else:
        title = None

    context = trim_history(history + [{"role": "user", "content": content}], MAX_HISTORY)
    try:
        client = genai.Client()
        response_text = generate_response(messages_to_contents(context), client)
    except Exception as exc:
        logger.exception("Gemini request failed for chat %s", chat_id)
        if getattr(exc, "code", None) == 503:
            raise HTTPException(
                status_code=503,
                detail="Gemini is temporarily overloaded. Wait a moment and try again.",
            ) from exc
        if getattr(exc, "code", None) == 429:
            raise HTTPException(
                status_code=429,
                detail="Gemini rate limit reached. Wait a moment and try again.",
            ) from exc
        raise HTTPException(
            status_code=502,
            detail="Gemini request failed. Check the backend terminal for details.",
        ) from exc

    db.save_exchange(chat_id, content, response_text, title)

    return {
        "role": "assistant",
        "content": response_text,
    }


@app.get("/api/status")
def status():
    api_configured = bool(os.getenv("GEMINI_API_KEY"))
    return {"model": MODEL, "api_configured": api_configured}
