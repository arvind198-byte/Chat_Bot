import os

import streamlit as st
from google import genai

from bot import MAX_HISTORY, MODEL, generate_response, messages_to_contents


st.set_page_config(
    page_title=" Chat Bot",
    page_icon="💬",
    layout="centered",
)

st.title("Son of Anton")
st.caption("A conversational chatbot powered by Google Gemini.")

with st.sidebar:
    st.subheader("Chat settings")
    st.caption(f"Model: `{MODEL}`")
    st.caption(
        "API key: configured"
        if os.getenv("GEMINI_API_KEY")
        else "API key: missing — add GEMINI_API_KEY to your .env file."
    )
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown("Hello! What would you like to talk about?")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Send a message")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not os.getenv("GEMINI_API_KEY"):
            st.error("Add GEMINI_API_KEY to your .env file, then restart the app.")
        else:
            try:
                with st.spinner("Thinking..."):
                    response_text = generate_response(
                        messages_to_contents(st.session_state.messages),
                        client=genai.Client(),
                    )
                st.markdown(response_text)
                st.session_state.messages.append(
                    {"role": "assistant", "content": response_text}
                )
                st.session_state.messages = st.session_state.messages[-MAX_HISTORY:]
            except Exception as error:
                st.error(f"Unable to get a response from Gemini: {error}")
