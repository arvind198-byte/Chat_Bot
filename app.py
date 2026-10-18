"""
Streamlit frontend for the Gemini chatbot.

Responsibilities:
  - Renders the chat UI (message list, input box).
  - Manages sidebar: new-chat, chat list, delete-chat.
  - Bridges the database layer (database.py) and Gemini layer (bot.py).

Session-state keys used:
  chat_id          – ID of the active chat (int | None).
  messages         – list[dict] mirroring the DB rows for the active chat.
  pending_delete   – chat_id awaiting deletion confirmation.
"""

import os

import streamlit as st
from google import genai
from dotenv import load_dotenv

from bot import (
    MODEL,
    generate_response,
    messages_to_contents,
)
from database import (
    init_db,
    create_chat,
    get_chats,
    get_messages,
    save_message,
    update_chat_title,
    delete_chat,
)

# ── Bootstrap ────────────────────────────────────────────────────────────────

load_dotenv()
init_db()

API_KEY_SET = bool(os.getenv("GEMINI_API_KEY"))
_TITLE_MAX_LEN = 50

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Son of Anton",
    page_icon="🤖",
    layout="centered",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* ── Sidebar ─────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fb;
    }

    section[data-testid="stSidebar"] .stMarkdown h2 {
        font-size: 1.3rem;
        font-weight: 600;
        letter-spacing: -0.02em;
    }

    /* Chat list buttons – left-aligned, subdued */
    section[data-testid="stSidebar"] .stButton > button {
        text-align: left;
        border: none;
        background: transparent;
        font-weight: 400;
        color: #444;
        padding: 0.35rem 0.6rem;
        border-radius: 8px;
        transition: background 0.15s ease;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #e8eaed;
    }

    /* Active chat highlight */
    section[data-testid="stSidebar"] .stButton > button[disabled] {
        background: #e0e4ff;
        color: #1a1a2e;
        font-weight: 500;
        opacity: 1 !important;
    }

    /* New Chat button – accent style */
    section[data-testid="stSidebar"] .new-chat-btn .stButton > button {
        background: #1a1a2e;
        color: #fff;
        font-weight: 500;
        border: none;
        border-radius: 8px;
    }
    section[data-testid="stSidebar"] .new-chat-btn .stButton > button:hover {
        background: #2d2d4e;
    }

    /* ── Main area ───────────────────────────────────── */
    .main .block-container {
        max-width: 760px;
    }

    /* Subtle header */
    .app-header {
        text-align: center;
        padding: 0.8rem 0 0.3rem;
    }
    .app-header h1 {
        font-size: 1.6rem;
        font-weight: 600;
        color: #1a1a2e;
        margin-bottom: 0.15rem;
    }
    .app-header p {
        font-size: 0.85rem;
        color: #888;
        margin: 0;
    }

    /* Welcome card */
    .welcome-card {
        text-align: center;
        padding: 3rem 1.5rem;
        margin-top: 2rem;
        color: #666;
    }
    .welcome-card h3 {
        font-weight: 500;
        color: #1a1a2e;
        margin-bottom: 0.4rem;
    }
    .welcome-card p {
        font-size: 0.9rem;
    }

    /* Delete confirmation */
    .delete-confirm {
        padding: 0.3rem 0;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Session-state defaults ───────────────────────────────────────────────────

if "chat_id" not in st.session_state:
    st.session_state.chat_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_delete" not in st.session_state:
    st.session_state.pending_delete = None


# ── Helper functions ─────────────────────────────────────────────────────────

def _load_chat(chat_id: int) -> None:
    """Switch the active conversation to *chat_id*."""
    st.session_state.chat_id = chat_id
    rows = get_messages(chat_id)
    st.session_state.messages = [
        {
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"],
            "latency_ms": row.get("latency_ms", 0),
            "tokens_used": row.get("tokens_used", 0),
        }
        for row in rows
    ]
    st.session_state.pending_delete = None


def _new_chat() -> None:
    """Create a fresh conversation and make it active."""
    chat_id = create_chat("New Chat")
    st.session_state.chat_id = chat_id
    st.session_state.messages = []
    st.session_state.pending_delete = None


def _auto_title(text: str) -> str:
    """Derive a short chat title from the first user message."""
    title = text.strip().replace("\n", " ")
    if len(title) > _TITLE_MAX_LEN:
        title = title[:_TITLE_MAX_LEN - 1] + "…"
    return title or "New Chat"


# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## Son of Anton")

    st.caption(f"Model: `{MODEL}`")
    if API_KEY_SET:
        st.caption("API key: configured")
    else:
        st.caption("API key: **missing** — add `GEMINI_API_KEY` to `.env`")

    st.divider()

    # New Chat button
    with st.container():
        st.markdown('<div class="new-chat-btn">', unsafe_allow_html=True)
        if st.button("New Chat", use_container_width=True):
            _new_chat()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # Chat list
    chats = get_chats()

    if not chats:
        st.caption("No conversations yet.")
    else:
        st.caption(f"{len(chats)} conversation{'s' if len(chats) != 1 else ''}")

        for chat in chats:
            cid = chat["id"]
            is_active = cid == st.session_state.chat_id
            label = chat["title"] or "Untitled"

            col_title, col_del = st.columns([5, 1])

            with col_title:
                # Show a subtle marker for the active chat
                display_label = f"● {label}" if is_active else label
                if st.button(
                    display_label,
                    key=f"chat_{cid}",
                    use_container_width=True,
                    disabled=is_active,
                ):
                    _load_chat(cid)
                    st.rerun()

            with col_del:
                if st.button("×", key=f"del_{cid}", help="Delete this chat"):
                    st.session_state.pending_delete = cid
                    st.rerun()

            # Delete confirmation
            if st.session_state.pending_delete == cid:
                st.markdown('<div class="delete-confirm">', unsafe_allow_html=True)
                st.warning(f'Delete "{label}"?', icon=None)
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Delete", key=f"yes_{cid}", use_container_width=True):
                        delete_chat(cid)
                        st.session_state.pending_delete = None
                        if st.session_state.chat_id == cid:
                            st.session_state.chat_id = None
                            st.session_state.messages = []
                        st.rerun()
                with c2:
                    if st.button("Cancel", key=f"no_{cid}", use_container_width=True):
                        st.session_state.pending_delete = None
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

# ── Main area ────────────────────────────────────────────────────────────────

st.markdown("""
<div class="app-header">
    <h1>Son of Anton</h1>
    <p>Conversational AI powered by Google Gemini</p>
</div>
""", unsafe_allow_html=True)

# ── Welcome / empty state ────────────────────────────────────────────────────

if st.session_state.chat_id is None:
    st.markdown("""
    <div class="welcome-card">
        <h3>Start a conversation</h3>
        <p>Click <strong>New Chat</strong> in the sidebar to begin,<br>
        or select a previous conversation.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Display messages ─────────────────────────────────────────────────────────

if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown("Hello! What would you like to talk about?")

def _format_time(raw) -> str:
    if not raw:
        return ""
    import datetime
    try:
        s = str(raw).strip()
        if "T" in s:
            dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
        local_dt = dt.astimezone()
        return local_dt.strftime("%I:%M:%S %p").lstrip("0")
    except Exception:
        return str(raw)


for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        ts = _format_time(msg.get("created_at"))
        if msg["role"] == "user":
            latency = msg.get("latency_ms", 0)
            if not latency and i + 1 < len(st.session_state.messages) and st.session_state.messages[i + 1]["role"] == "assistant":
                latency = st.session_state.messages[i + 1].get("latency_ms", 0)
            dur_str = f" · Took {latency / 1000:.2f}s" if latency > 0 else ""
            if ts:
                st.caption(f"{ts}{dur_str}")
        else:
            latency = msg.get("latency_ms", 0)
            dur_str = f" · Took {latency / 1000:.2f}s ({latency} ms)" if latency > 0 else ""
            tokens = msg.get("tokens_used", 0)
            tok_str = f" · {tokens} tokens" if tokens > 0 else ""
            if ts or dur_str:
                st.caption(f"{ts}{dur_str}{tok_str}")

# ── Chat input ───────────────────────────────────────────────────────────────

prompt = st.chat_input("Type a message...")
if prompt:
    if not API_KEY_SET:
        st.error("Add `GEMINI_API_KEY` to your `.env` file, then restart the app.")
        st.stop()

    # 1. Show & persist the user message
    user_res = save_message(st.session_state.chat_id, "user", prompt)
    user_msg_data = {
        "role": "user",
        "content": prompt,
        "created_at": getattr(user_res, "created_at", None),
    }
    st.session_state.messages.append(user_msg_data)

    with st.chat_message("user"):
        st.markdown(prompt)
        ts = _format_time(user_msg_data.get("created_at"))
        if ts:
            st.caption(f"{ts} · Processing...")

    # 2. Auto-title on the first user message
    user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
    if len(user_msgs) == 1:
        update_chat_title(st.session_state.chat_id, _auto_title(prompt))

    # 3. Build context & call Gemini
    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                context = st.session_state.messages
                res = generate_response(
                    messages_to_contents(context),
                    client=genai.Client(),
                )
                if isinstance(res, tuple):
                    response_text, latency_ms, tokens_used = res
                else:
                    response_text, latency_ms, tokens_used = res, 0, 0

            st.markdown(response_text)

            # 4. Persist the assistant response
            bot_res = save_message(st.session_state.chat_id, "assistant", response_text, latency_ms, tokens_used)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": response_text,
                    "latency_ms": latency_ms,
                    "tokens_used": tokens_used,
                    "created_at": getattr(bot_res, "created_at", None),
                }
            )
            dur_str = f" · Took {latency_ms / 1000:.2f}s ({latency_ms} ms)" if latency_ms > 0 else ""
            tok_str = f" · {tokens_used} tokens" if tokens_used > 0 else ""
            ts = _format_time(getattr(bot_res, "created_at", None))
            if ts or dur_str:
                st.caption(f"{ts}{dur_str}{tok_str}")

        except Exception as err:
            st.error(
                f"Could not get a response. You can resend your message to retry.\n\n"
                f"Details: `{err}`"
            )
