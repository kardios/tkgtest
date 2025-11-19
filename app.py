import streamlit as st
from openai import OpenAI
import networkx as nx
from pyvis.network import Network
import tempfile
import os

# --- Setup OpenAI client ---
api_key = st.secrets["OPENAI_API_KEY"]
openai_client = OpenAI(api_key=api_key)

# --- Streamlit UI --- 
st.set_page_config(page_title="Book Knowledge Map", layout="wide")
st.title("📚 Knowledge Map Generator (GPT‑5 + Web Search)")

books_input = st.text_area(
    "Enter a list of books (one per line):", 
    value="The Republic\nLeviathan\nThe Social Contract\nDemocracy in America"
)

if st.button("Generate Map"):
    book_list = [b.strip() for b in books_input.split("\n") if b.strip()]
    if not book_list:
        st.error("Please enter at least one book.")
    else:
        st.info(f"Processing {len(book_list)} books…")

        # Call GPT-5 via Responses API with web_search tool
        concepts_by_book = {}
        for book in book_list:
            prompt = (
                f'Extract 6–10 key concepts from the book titled "{book}". '
                "For each concept, show relationships between them in the form:\n"
                "ConceptA -> ConceptB\n"
                "Focus on major themes, ideas, and how they connect."
            )

            resp = openai_client.responses.create(
                model="gpt-5",
                tools=[{"type": "web_search"}],
                tool_choice="auto",
                input=prompt
            )

            # The generated content
            generated = resp.output[0].content["text"]
            concepts_by_book[book] = generated

        st.success("Concept extraction complete.")

        # Build graph
        G = nx.Graph()
        for book, text in concepts_by_book.items():
            for line in text.splitlines():
                if "->" in line:
                    parts = line.split("->")
                    if len(parts) == 2:
                        src = parts[0].strip()
                        tgt = parts[1].strip()
                        if src and tgt:
                            G.add_node(src, book=book)
                            G.add_node(tgt, book=book)
                            G.add_edge(src, tgt, book=book)

        if G.number_of_nodes() == 0:
            st.warning("No concepts found or parsed. Try different book titles or check your API response.")
        else:
            # Visualize graph with PyVis
            net = Network(height="600px", width="100%", notebook=False)
            net.from_nx(G)

            # Save to temporary HTML file
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
            net.save_graph(tmp_file.name)
            tmp_file.close()

            # Render in Streamlit
            html = open(tmp_file.name, "r", encoding="utf-8").read()
            st.components.v1.html(html, height=650, scrolling=True)

            # Clean up
            os.unlink(tmp_file.name)

        # Optionally show raw concept output per book
        with st.expander("Show raw concept extraction per book"):
            for book, text in concepts_by_book.items():
                st.markdown(f"**{book}**")
                st.text(text)



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
