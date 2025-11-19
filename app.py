import streamlit as st
from openai import OpenAI
import networkx as nx
from pyvis.network import Network
import tempfile
import os

# --- Setup OpenAI client ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Streamlit UI ---
st.set_page_config(page_title="Book Knowledge Mapper", layout="wide")
st.title("📚 Book Knowledge Mapper (GPT + Web Search Connections)")

# --- User input: list of books ---
st.markdown("Enter a list of books (one per line):")
books_input = st.text_area("Books", height=200)
books = [b.strip() for b in books_input.split("\n") if b.strip()]

if books:
    st.success(f"{len(books)} books entered.")

# --- Generate connections ---
if st.button("Generate Knowledge Map") and books:
    with st.spinner("Analyzing book connections with GPT + Web Search..."):
        G = nx.Graph()
        for book in books:
            G.add_node(book)

        # Pairwise connections
        for i, book1 in enumerate(books):
            for j, book2 in enumerate(books):
                if j <= i:
                    continue

                prompt = (
                    f"Are the following two books conceptually related? "
                    f"Book 1: '{book1}', Book 2: '{book2}'. "
                    "If yes, briefly explain the connection."
                )

                try:
                    # GPT-5 + web search
                    response = client.responses.create(
                        model="gpt-5",
                        tools=[{"type": "web_search"}],
                        input=prompt,
                        tool_choice="auto"
                    )
                    text = response.output_text.strip().lower()
                except Exception as e:
                    text = ""

                # Detect if GPT found a meaningful connection
                if any(keyword in text for keyword in ["related", "connection", "similar", "theme", "reference"]):
                    G.add_edge(book1, book2, title=text)

        # --- Visualize with PyVis ---
        net = Network(height="600px", width="100%", notebook=False)
        net.from_nx(G)
        net.repulsion(node_distance=200, spring_length=200)

        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        net.save_graph(tmp_file.name)
        st.components.v1.html(open(tmp_file.name, "r").read(), height=600, scrolling=True)

else:
    st.info("Enter books and click 'Generate Knowledge Map' to see connections.")
