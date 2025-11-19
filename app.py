import streamlit as st
from openai import OpenAI
import os
import json
import networkx as nx
from pyvis.network import Network
import tempfile

st.set_page_config(page_title="Book Knowledge Mapper", layout="wide")

st.title("📚 Book Knowledge Mapper (GPT-5 + Web Search)")

# Store API key as environment variable (compatible)
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]


# ---------------------------------------------------------
# GPT-5: Generate knowledge graph JSON
# ---------------------------------------------------------

def generate_graph_data(client, books):
    prompt = f"""
You are an expert in conceptual mapping.

Given these books:
{books}

1. Identify 8–20 core shared concepts.
2. Map relationships between concepts.
3. Output ONLY valid JSON in this format:

{{
  "concepts": [
       {{"id": "c1", "name": "Concept Name"}}
  ],
  "edges": [
       {{"source": "c1", "target": "c4", "relationship": "influences"}}
  ]
}}
"""
    response = client.responses.create(
        model="gpt-5",
        reasoning={"effort": "medium"},
        input=prompt,
        web_search={"enable": True, "recency_days": 365}
    )

    return json.loads(response.output_text)


# ---------------------------------------------------------
# Graph rendering
# ---------------------------------------------------------

def render_graph(graph_data):
    G = nx.Graph()

    for c in graph_data["concepts"]:
        G.add_node(c["id"], label=c["name"])

    for e in graph_data["edges"]:
        G.add_edge(e["source"], e["target"], title=e["relationship"])

    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="black")
    net.force_atlas_2based()
    net.from_nx(G)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        net.save_graph(tmp.name)
        return tmp.name


# ---------------------------------------------------------
# UI
# ---------------------------------------------------------

books_input = st.text_area(
    "Enter one book per line:",
    height=200,
    placeholder="Sapiens\nThinking, Fast and Slow\nThe Innovator’s Dilemma"
)

if st.button("Generate Knowledge Map"):
    if not books_input.strip():
        st.error("Please enter at least one book.")
    else:
        with st.spinner("Analyzing with GPT-5 + Web Search..."):

            # 🔥 Lazy init (fix for proxy bug)
            client = OpenAI(api_key=OPENAI_API_KEY)

            try:
                graph_data = generate_graph_data(client, books_input.strip())
                path = render_graph(graph_data)
                st.components.v1.html(open(path).read(), height=800)

            except Exception as e:
                st.error(f"Error: {e}")
