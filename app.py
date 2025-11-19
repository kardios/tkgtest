import streamlit as st
from openai import OpenAI
import os
import json
import networkx as nx
from pyvis.network import Network
import tempfile

# -------------------------------------------------------------------
# Setup
# -------------------------------------------------------------------

st.set_page_config(page_title="Book Knowledge Mapper", layout="wide")

# API key (environment variable avoids constructor bug)
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
client = OpenAI()

st.title("📚 Book Knowledge Mapper (GPT-5 + Web Search)")


# -------------------------------------------------------------------
# GPT-5 Function
# -------------------------------------------------------------------

def generate_graph_data(books):
    """Call GPT-5 to produce structured topic graph from book list."""

    prompt = f"""
You are an expert in conceptual mapping.

Given these books:
{books}

1. Identify 8–20 core shared concepts.
2. Map relationships between concepts.
3. Output ONLY valid JSON in this format:

{{
  "concepts": [
       {{"id": "c1", "name": "Concept Name"}},
       ...
  ],
  "edges": [
       {{"source": "c1", "target": "c4", "relationship": "influences"}},
       ...
  ]
}}
"""

    response = client.responses.create(
        model="gpt-5",
        reasoning={"effort": "medium"},
        input=prompt,
        web_search={"enable": True, "recency_days": 365}
    )

    text = response.output_text
    return json.loads(text)


# -------------------------------------------------------------------
# Graph Visualization
# -------------------------------------------------------------------

def render_graph(graph_data):
    """Converts JSON graph into a PyVis HTML visualization."""

    G = nx.Graph()

    # Add nodes
    for c in graph_data["concepts"]:
        G.add_node(c["id"], label=c["name"])

    # Add edges
    for e in graph_data["edges"]:
        G.add_edge(e["source"], e["target"], title=e["relationship"])

    net = Network(height="750px", width="100%", bgcolor="#FFFFFF", font_color="black")
    net.force_atlas_2based()

    net.from_nx(G)

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        net.save_graph(tmp.name)
        return tmp.name


# -------------------------------------------------------------------
# UI Layout
# -------------------------------------------------------------------

st.subheader("Enter a list of books")
books_input = st.text_area(
    "One book per line. Use whatever form you want (title only is fine).",
    height=200,
    placeholder="Example:\nThinking, Fast and Slow\nSapiens\nThe Innovator's Dilemma"
)

if st.button("Generate Knowledge Map"):
    if not books_input.strip():
        st.error("Please enter at least one book.")
    else:
        with st.spinner("Analyzing books with GPT-5 + Web Search..."):
            try:
                graph_data = generate_graph_data(books_input.strip())
                graph_path = render_graph(graph_data)
                st.success("Knowledge Map Generated!")

                st.components.v1.html(open(graph_path, "r").read(), height=800)

            except Exception as e:
                st.error(f"Error: {e}")
