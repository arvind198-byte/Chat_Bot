"""
Placement Cell Assistant interaction layer.

Integrates with the Google GenAI SDK using gemini-2.5-flash / gemini-3.8-flash,
grounded in the official Placement Cell knowledge base (knowledge.txt).
Implements a 4-layer system prompt, tracks latency (ms) and token counts,
and maintains full conversational context without artificial trimming.
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

# Load knowledge base at startup
_KNOWLEDGE_PATH = Path(__file__).resolve().parent / "knowledge.txt"
if _KNOWLEDGE_PATH.exists():
    with open(_KNOWLEDGE_PATH, "r", encoding="utf-8") as _f:
        KNOWLEDGE_BASE = _f.read()
else:
    KNOWLEDGE_BASE = "Official Placement Cell knowledge base unavailable."

# 4-Layer System Prompt
SYSTEM_PROMPT = f"""You are the official Virtual Assistant for the Campus Placement Cell.
Your purpose is to assist students with recruitment drives, eligibility rules, company tiers, and preparation procedures.

LAYER 1: PERSONA AND TONE
- Maintain an objective, professional, courteous, and authoritative tone at all times.
- Provide structured, precise, and practical answers.
- Do NOT use any emojis, icons, or casual slang anywhere in your responses.

LAYER 2: DOMAIN KNOWLEDGE
Ground all factual information strictly in the following official Placement Cell Knowledge Base:
\"\"\"
{KNOWLEDGE_BASE}
\"\"\"

LAYER 3: SCOPE CONTROL
- You strictly address topics related to campus placements, recruitment workflows, eligibility criteria, drive procedures, policy rules, and interview preparation.
- If the user asks general knowledge questions, coding homework requests, casual chitchat, creative writing, or anything outside campus placements, politely decline:
  "I am dedicated to assisting with campus placements, recruitment drives, and related policies. I cannot assist with topics outside this scope."

LAYER 4: SAFETY AND HONESTY RULES
- NEVER promise, predict, or guarantee job offers, selection outcomes, or salary packages.
- Always reiterate when relevant that the Placement Cell facilitates opportunities and selection is strictly at the recruiter's discretion.
- If an in-domain question cannot be answered using the facts in the knowledge base (e.g., student specific records, unlisted company criteria, specific interview dates), you MUST respond with EXACTLY this sentence:
  "I do not have specific records for this inquiry. Please contact the Placement Cell directly at placement@college.edu or visit the Placement Office."
"""


def messages_to_contents(messages: list[dict]) -> list[types.Content]:
    """Convert a conversation array into GenAI Content structures.

    The first message is mapped to include system instructions or context.
    Each message is mapped with valid alternating roles ('user' vs 'model').
    """
    contents: list[types.Content] = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if not content:
            continue
        genai_role = "model" if role in ("assistant", "bot", "model") else "user"
        contents.append(
            types.Content(
                role=genai_role,
                parts=[types.Part.from_text(text=content)],
            )
        )
    return contents


def generate_response(
    messages: list[dict],
    client: genai.Client | None = None,
) -> tuple[str, int, int]:
    """Generate a response using the Gemini API.

    Sends the complete conversation context, injects the 4-layer system prompt,
    measures latency in milliseconds, extracts token usage, and returns:
    (reply_text, latency_ms, tokens_used)
    """
    if client is None:
        client = genai.Client()

    contents = messages_to_contents(messages)

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.2,
    )

    start_time = time.perf_counter()
    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=config,
    )
    latency_ms = int((time.perf_counter() - start_time) * 1000)

    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    tokens_used = 0
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        tokens_used = getattr(response.usage_metadata, "total_token_count", 0) or 0

    return response.text, latency_ms, tokens_used
