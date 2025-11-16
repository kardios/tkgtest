# app.py
import streamlit as st
from openai import OpenAI
import json
import pandas as pd
import plotly.express as px
import networkx as nx
from pyvis.network import Network
import tempfile

# ---------------------------
# 1️⃣ OpenAI Client Setup
# ---------------------------
# Use Streamlit secrets for API key
api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

st.set_page_config(page_title="EventSense Web", layout="wide")
st.title("EventSense Web – Temporal Knowledge Graph Prototype")

# ---------------------------
# 2️⃣ User Inputs
# ---------------------------
topic = st.text_input("Enter a topic or event", value="Paris Agreement 2015")
domain_filter = st.text_area("Optional: Trusted domains (comma-separated)", value="un.org,bbc.com,reuters.com")

if st.button("Fetch Events") and topic:
    
    st.info("Fetching events from GPT-5 web search... This may take a few seconds.")
    
    # Prepare domain filter list
    domains = [d.strip() for d in domain_filter.split(",") if d.strip()]
    
    # ---------------------------
    # 3️⃣ GPT-5 Web Search Call
    # ---------------------------
    tools = [{"type": "web_search"}]
    if domains:
        tools[0]["filters"] = {"allowed_domains": domains}
    
    response = client.responses.create(
        model="gpt-5",
        tools=tools,
        input=f"""
        You are a research assistant. Extract all major events, actors, dates, locations, and themes related to the topic '{topic}'.
        Produce structured JSON in the format:
        [
            {{
                "event_id": string,
                "title": string,
                "start_date": "YYYY-MM-DD",
                "end_date": "YYYY-MM-DD" or null,
                "actors": [{{"id": string, "name": string, "role": string}}],
                "location": {{"name": string, "lat": float, "lon": float}} or null,
                "themes": [string],
                "description": string,
                "sources": [{{"doc_id": string, "url": string, "span": string}}],
                "confidence": float
            }}
        ]
        Include inline citations.
        """
    )
    
    # ---------------------------
    # 4️⃣ Parse JSON
    # ---------------------------
    try:
        events_json = json.loads(response.output_text)
        st.success("Events fetched successfully!")
        st.subheader("Extracted JSON")
        st.json(events_json)
    except Exception as e:
        st.error(f"Failed to parse JSON: {e}")
        st.text(response.output_text)
        st.stop()
    
    # ---------------------------
    # 5️⃣ Timeline Visualization (Plotly)
    # ---------------------------
    st.subheader("Timeline of Events")
    timeline_data = [
        {
            "title": e["title"],
            "date": e["start_date"],
            "actors": ", ".join([a["name"] for a in e.get("actors", [])]),
            "themes": ", ".join(e.get("themes", []))
        }
        for e in events_json
    ]
    
    if timeline_data:
        # ✅ Use pandas DataFrame instead of px.data.frame
        df = pd.DataFrame(timeline_data)
        fig = px.scatter(
            df,
            x="date",
            y=[1]*len(df),  # dummy y-axis for layout
            text="title",
            hover_data=["actors", "themes"],
            height=300
        )
        fig.update_yaxes(visible=False)
        st.plotly_chart(fig, use_container_width=True)
    
    # ---------------------------
    # 6️⃣ Actor-Event Network Graph (PyVis)
    # ---------------------------
    st.subheader("Actor-Event Network")
    G = nx.Graph()
    
    for e in events_json:
        event_node = f"Event: {e['title']}"
        G.add_node(event_node, type="event")
        for actor in e.get("actors", []):
            actor_node = f"Actor: {actor['name']}"
            G.add_node(actor_node, type="actor")
            G.add_edge(actor_node, event_node)
    
    net = Network(height="400px", width="100%", notebook=False)
    net.from_nx(G)
    
    # Save and display in iframe
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
        net.save_graph(tmp_file.name)
        st.components.v1.html(open(tmp_file.name, "r").read(), height=450)
