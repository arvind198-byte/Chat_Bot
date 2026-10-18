"""
FastAPI backend for the Placement Cell Chatbot.

Endpoints
---------
GET    /api/status                    – return model status & configuration
GET    /api/chats                     – list all chats
POST   /api/chats                     – create a new chat
DELETE /api/chats/{chat_id}          – delete a chat, its messages, and feedback
GET    /api/chats/{chat_id}/messages  – retrieve full message history for a chat
POST   /api/chats/{chat_id}/messages  – send a user query and obtain assistant reply
POST   /api/feedback                  – submit rating (+1 / -1) for an assistant message
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
from backend.bot import (
    generate_response,
    MODEL,
)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
logger = logging.getLogger(__name__)

# App initialization
app = FastAPI(title="Placement Cell Virtual Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()

_TITLE_MAX_LEN = 50


# Schemas
class CreateChatRequest(BaseModel):
    title: str = Field(default="New Chat", min_length=1, max_length=100)


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)


class FeedbackRequest(BaseModel):
    message_id: int
    rating: int = Field(..., description="+1 for thumbs up, -1 for thumbs down")


# Routes
@app.get("/api/status")
def status():
    api_configured = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "model": MODEL,
        "api_configured": api_configured,
        "assistant_name": "Placement Cell Virtual Assistant",
    }


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

    # Retrieve full conversation history (no message-count limit)
    history_rows = db.get_messages(chat_id)
    history = [{"role": m["role"], "content": m["content"]} for m in history_rows]

    # Generate title on first user message
    if not any(message["role"] == "user" for message in history):
        title = content.strip().replace("\n", " ")
        if len(title) > _TITLE_MAX_LEN:
            title = title[:_TITLE_MAX_LEN - 1] + "…"
    else:
        title = None

    # Full conversational context sent to the model
    full_conversation = history + [{"role": "user", "content": content}]

    try:
        client = genai.Client()
        response_text, latency_ms, tokens_used = generate_response(full_conversation, client)
    except Exception as exc:
        logger.exception("Model request failed for chat %s", chat_id)
        if getattr(exc, "code", None) == 503:
            raise HTTPException(
                status_code=503,
                detail="AI service is temporarily overloaded. Please try again shortly.",
            ) from exc
        if getattr(exc, "code", None) == 429:
            raise HTTPException(
                status_code=429,
                detail="Rate limit reached. Please wait a moment before sending another inquiry.",
            ) from exc
        raise HTTPException(
            status_code=502,
            detail=f"Inquiry could not be processed: {exc}",
        ) from exc

    # Persist exchange atomically and retrieve assistant message id
    saved = db.save_exchange(
        chat_id=chat_id,
        user_msg=content,
        bot_msg=response_text,
        title=title,
        latency_ms=latency_ms,
        tokens_used=tokens_used,
    )

    return {
        "id": int(saved),
        "role": "assistant",
        "content": response_text,
        "latency_ms": latency_ms,
        "tokens_used": tokens_used,
        "created_at": getattr(saved, "created_at", None),
        "user_message_id": getattr(saved, "user_msg_id", None),
        "user_created_at": getattr(saved, "user_created_at", None),
    }


@app.post("/api/feedback", status_code=201)
def submit_feedback(body: FeedbackRequest):
    if body.rating not in (1, -1):
        raise HTTPException(status_code=400, detail="Rating must be either 1 or -1.")
    feedback_id = db.save_feedback(body.message_id, body.rating)
    return {"status": "success", "feedback_id": feedback_id}
