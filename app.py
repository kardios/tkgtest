# app.py
import os
import streamlit as st
from openai import OpenAI

# --- Setup OpenAI client ---
# Use Streamlit secrets for API key
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
client = OpenAI()  # no arguments, avoids constructor errors

# --- Streamlit UI ---
st.set_page_config(page_title="Book Knowledge Mapper", layout="wide")
st.title("📚 Book Knowledge Mapper (GPT-5 + Web Search)")

# Input box for user query
query = st.text_input("Enter topic:", "computer game design")

if st.button("Generate Book List"):
    with st.spinner("Fetching books..."):
        # GPT prompt to generate a book list
        prompt = f"Provide a list of books about '{query}', one per line."
        
        try:
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
            )

            # Extract text
            result_text = response.choices[0].message.content.strip()
            
            # Display each book on a separate line
            st.subheader("Books:")
            for line in result_text.split("\n"):
                if line.strip():  # skip empty lines
                    st.write(f"- {line.strip()}")
        except Exception as e:
            st.error(f"Error: {e}")
