import streamlit as st
from openai import OpenAI
import networkx as nx
from pyvis.network import Network
import tempfile
import os

# --- DEFINITIVE PROXY FIX ---
# Forcefully unset proxy environment variables at the very start of the script.
# Some deployment environments (like Streamlit Community Cloud) have default proxies
# that can conflict with the 'openai' library's underlying 'httpx' client.
# By removing them, we prevent the client from ever trying to use them.
for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    os.environ.pop(proxy_var, None)
# --- END FIX ---


# --- Setup OpenAI client using Environment Variables ---
api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:
    st.error(
        "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable or add it to your Streamlit secrets.", 
        icon="🔑"
    )
    st.stop()

# Now, initialize the client in the standard way. The proxy issue is already solved.
try:
    client = OpenAI(api_key=api_key)
except Exception as e:
    st.error(f"Failed to initialize OpenAI client: {e}", icon="🚨")
    st.stop()


# --- Streamlit UI ---
st.set_page_config(page_title="Book Knowledge Mapper", layout="wide")
st.title("📚 Book Knowledge Mapper (with Web Search)")
st.markdown("Discover conceptual connections between books using an AI agent that can search the web for deeper insights. Enter a list of books below.")

# --- User input: list of books ---
st.markdown("##### Enter a list of books (one per line):")
books_input = st.text_area(
    "Books",
    height=200,
    label_visibility="collapsed",
    value="Sapiens: A Brief History of Humankind by Yuval Noah Harari\nThe Selfish Gene by Richard Dawkins\nThinking, Fast and Slow by Daniel Kahneman\nSuperintelligence by Nick Bostrom\nFahrenheit 451 by Ray Bradbury"
)
books = [b.strip() for b in books_input.split("\n") if b.strip()]

if books:
    st.success(f"{len(books)} books entered.")

# --- Generate connections ---
if st.button("Generate Knowledge Map", type="primary") and books:
    if len(books) < 2:
        st.warning("Please enter at least two books to map connections.")
    else:
        progress_bar = st.progress(0, text="Initializing analysis...")
        status_text = st.empty()
        
        with st.spinner("Building knowledge graph... This may take a moment."):
            G = nx.Graph()
            for book in books:
                G.add_node(book, label=book, title=book)

            book_pairs = [(books[i], books[j]) for i in range(len(books)) for j in range(i + 1, len(books))]
            total_pairs = len(book_pairs)

            for i, (book1, book2) in enumerate(book_pairs):
                status_text.text(f"Analyzing connection {i+1}/{total_pairs}: '{book1}' and '{book2}'")
                
                prompt = (
                    f"Using a web search, analyze and determine if there are significant conceptual connections (e.g., themes, author influence, subject matter) between the following two books: "
                    f"Book 1: '{book1}' and Book 2: '{book2}'.\n\n"
                    "Start your response with 'YES:' if they are related, or 'NO:' if they are not. "
                    "If YES, please provide a concise, one-sentence explanation of the connection based on your findings."
                )

                try:
                    response = client.responses.create(
                        model="gpt-5",
                        tools=[{"type": "web_search"}],
                        input=prompt,
                    )
                    text = response.output_text.strip()

                except Exception as e:
                    st.error(f"An API error occurred while comparing '{book1}' and '{book2}': {e}")
                    continue

                if text.lower().startswith("yes"):
                    explanation = text[4:].strip()
                    G.add_edge(book1, book2, title=explanation, color="#3a78d1")
                
                progress_bar.progress((i + 1) / total_pairs, text=f"Analysis {i+1}/{total_pairs} complete")

            status_text.success("Analysis complete! Rendering visualization...")

            if not G.edges:
                st.warning("No significant connections were found among the entered books.")
            else:
                net = Network(height="700px", width="100%", notebook=False, cdn_resources='in_line', bgcolor="#f0f2f6", font_color="black")
                net.from_nx(G)
                
                net.set_options("""
                var options = {
                  "nodes": {"shape": "dot", "size": 20, "font": {"size": 14}},
                  "edges": {"width": 2, "smooth": {"type": "continuous"}},
                  "physics": {
                    "forceAtlas2Based": {"gravitationalConstant": -50, "centralGravity": 0.01, "springLength": 200, "springConstant": 0.08},
                    "maxVelocity": 50, "minVelocity": 0.1, "solver": "forceAtlas2Based", "timestep": 0.5,
                    "stabilization": {"iterations": 150}
                  }
                }
                """)

                with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
                    net.save_graph(tmp_file.name)
                    with open(tmp_file.name, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                
                st.components.v1.html(html_content, height=720, scrolling=True)
                os.unlink(tmp_file.name)

else:
    st.info("Enter some books and click 'Generate Knowledge Map' to see the connections.")
