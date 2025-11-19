# app.py
import os
import streamlit as st
from openai import OpenAI

# --- Setup API key ---
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
client = OpenAI()  # no args needed, uses env variable

# --- Streamlit UI ---
st.set_page_config(page_title="Book Knowledge Mapper", layout="wide")
st.title("📚 Book Knowledge Mapper (GPT-5 + Web Search)")

query = st.text_input("Enter topic:", "computer game design")

if st.button("Generate Book List"):
    with st.spinner("Searching the web and generating list..."):
        prompt = f"Provide a list of books about '{query}', one per line."

        try:
            response = client.responses.create(
                model="gpt-5",
                tools=[{"type": "web_search"}],
                tool_choice="auto",
                input=prompt,
            )

            # Extract text output
            text_output = response.output_text.strip()

            # Display as list
            st.subheader("Books found:")
            for line in text_output.split("\n"):
                if line.strip():
                    st.write(f"- {line.strip()}")

            # Optionally show sources
            if hasattr(response, "sources"):
                st.subheader("Sources:")
                for src in response.sources:
                    st.write(f"[{src.get('title', src['url'])}]({src['url']})")

        except Exception as e:
            st.error(f"Error: {e}")
