from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-3.5-flash"
MAX_HISTORY = 20


def messages_to_contents(messages):
    return [
        types.Content(
            role="model" if message["role"] == "assistant" else "user",
            parts=[types.Part.from_text(text=message["content"])],
        )
        for message in messages
    ]
    


def generate_response(contents, client=None):
    if client is None:
        client = genai.Client()

    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
    )
    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")
    return response.text


def main():
    client = genai.Client()
    prompts = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text="Hi, my name is Arvind8")],
        )
    ]

    while True:
        try:
            prompt = input("Enter query: ")

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
            print(response_text)
            prompts = prompts[-MAX_HISTORY:]

        except Exception as error:
            print(f"Error occurred: {error}")


if __name__ == "__main__":
    main()