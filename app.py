import streamlit as st
from pyvis.network import Network
import networkx as nx
from openai import OpenAI
import os

# --- Setup OpenAI client ---
# Make sure your OPENAI_API_KEY is set in Streamlit secrets
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
client = OpenAI()  # Uses env variable

# --- Streamlit UI ---
st.set_page_config(page_title="Book Knowledge Mapper", layout="wide")
st.title("📚 Book Knowledge Mapper")

book_input = st.text_area(
    "Enter a list of books (one per line):",
    height=200
)

if st.button("Generate Knowledge Map") and book_input.strip():
    books = [b.strip() for b in book_input.split("\n") if b.strip()]
    st.write(f"Processing {len(books)} books...")

    # --- Step 1: Get relationships using OpenAI ---
    book_relations = {}
    with st.spinner("Analyzing books and extracting connections..."):
        for book in books:
            prompt = f"""
            Given the book titled "{book}", list other books from the provided list that are related.
            Also provide the nature of the relationship (e.g., similar theme, same author, sequel, shared topic).
            Format the output as JSON like this:
            {{
                "related_books": [
                    {{"title": "Other Book Title", "relation": "similar theme"}}
                ]
            }}
            Only include books from this list: {books}
            """
            try:
                response = client.responses.create(
                    model="gpt-5",
                    input=prompt
                )
                # Extract text
                text = response.output_text
                import json
                data = json.loads(text)
                book_relations[book] = data.get("related_books", [])
            except Exception as e:
                st.error(f"Error processing book '{book}': {e}")
                book_relations[book] = []

    # --- Step 2: Build NetworkX graph ---
    G = nx.Graph()
    for book in books:
        G.add_node(book)
        for relation in book_relations.get(book, []):
            other = relation["title"]
            rel_type = relation["relation"]
            if other in books:  # only connect listed books
                G.add_edge(book, other, label=rel_type)

    # --- Step 3: Visualize with PyVis ---
    net = Network(height="600px", width="100%", notebook=False)
    net.from_nx(G)
    net.show_buttons(filter_=['physics'])

    # Save and display in Streamlit
    path = "/tmp/book_map.html"
    net.save_graph(path)
    st.components.v1.html(open(path, 'r', encoding='utf-8').read(), height=650)

    st.success("Knowledge map generated!")
