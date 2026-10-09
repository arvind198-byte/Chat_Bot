"""
Gemini API interaction layer.

Keeps all Google GenAI SDK usage in one place so the Streamlit frontend
and CLI can share the same logic without duplicating code.

The model ID and history-window size are defined here and imported
wherever needed.
"""

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Model to use for all Gemini requests.  Change this value to switch models.
MODEL = "gemini-3.8-flash"

# Maximum number of *messages* (user + assistant) retained in the context
# window sent to Gemini.  Full history is always kept in SQLite.
# We round down to the nearest even number when trimming so we never
# break a user/assistant pair in half.
MAX_HISTORY = 20


def messages_to_contents(messages: list[dict]) -> list[types.Content]:
    """Convert a list of ``{"role": ..., "content": ...}`` dicts into
    the ``types.Content`` objects expected by the GenAI SDK.

    Streamlit uses ``"assistant"`` for the bot role; the SDK uses ``"model"``.
    """
    return [
        types.Content(
            role="model" if message["role"] == "assistant" else "user",
            parts=[types.Part.from_text(text=message["content"])],
        )
        for message in messages
    ]


def trim_history(messages: list[dict], max_messages: int = MAX_HISTORY) -> list[dict]:
    """Return a bounded Gemini history with valid alternating roles.

    Older app versions could leave a user message in the database when a
    Gemini request failed. Merge adjacent messages with the same role so
    those legacy rows do not create malformed consecutive turns.
    """
    normalized: list[dict] = []
    for message in messages:
        role = message.get("role")
        content = message.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str) or not content:
            continue

        if normalized and normalized[-1]["role"] == role:
            normalized[-1]["content"] += "\n\n" + content
        else:
            normalized.append({"role": role, "content": content})

    tail = normalized[-max_messages:] if max_messages > 0 else []
    if tail and tail[0]["role"] == "assistant":
        tail = tail[1:]
    return tail


def generate_response(
    contents: list[types.Content],
    client: genai.Client | None = None,
) -> str:
    """Send *contents* to Gemini and return the text response.

    Raises ``RuntimeError`` if the model returns an empty response.
    """
    if client is None:
        client = genai.Client()

    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
    )
    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")
    return response.text


# ---------------------------------------------------------------------------
# CLI entry-point – preserved for quick terminal testing.
# ---------------------------------------------------------------------------

def main() -> None:
    """Interactive command-line chatbot loop."""
    client = genai.Client()
    prompts: list[types.Content] = []

    print(f"Gemini chatbot ({MODEL}).  Type 'exit' to quit.\n")

    while True:
        try:
            prompt = input("You: ")

            if prompt.lower() == "exit":
                print("Goodbye!")
                break

            if not prompt.strip():
                continue

            user_message = types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            )
            response_text = generate_response(prompts + [user_message], client)

            prompts.extend(
                [
                    user_message,
                    types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=response_text)],
                    ),
                ]
            )
            print(f"\nGemini: {response_text}\n")
            prompts = prompts[-MAX_HISTORY:]

        except Exception as error:
            print(f"Error: {error}")


if __name__ == "__main__":
    main()