import streamlit as st
from openai import OpenAI
import networkx as nx
from pyvis.network import Network
import tempfile
import os

# --- Setup OpenAI client ---
# Ensure your OPENAI_API_KEY is set in Streamlit's secrets
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    st.error("OpenAI API key not found. Please add it to your Streamlit secrets.", icon="🔑")
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
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with st.spinner("Building knowledge graph... This may take a moment."):
            G = nx.Graph()
            for book in books:
                G.add_node(book, label=book, title=book)

            # Create all unique pairs of books
            book_pairs = []
            for i, book1 in enumerate(books):
                for j, book2 in enumerate(books):
                    if j > i:
                        book_pairs.append((book1, book2))

            total_pairs = len(book_pairs)

            # Process each pair to find connections
            for i, (book1, book2) in enumerate(book_pairs):
                status_text.text(f"Analyzing connection {i+1}/{total_pairs}: '{book1}' and '{book2}'")
                
                # Prompt designed for a web-searching agent
                prompt = (
                    f"Using a web search, analyze and determine if there are significant conceptual connections (e.g., themes, author influence, subject matter) between the following two books: "
                    f"Book 1: '{book1}' and Book 2: '{book2}'.\n\n"
                    "Start your response with 'YES:' if they are related, or 'NO:' if they are not. "
                    "If YES, please provide a concise, one-sentence explanation of the connection based on your findings."
                )

                try:
                    # CORRECTED API call using the Responses API with web_search tool
                    # This aligns with your original code and the provided documentation.
                    response = client.responses.create(
                        model="gpt-5",  # Using the model specified in the documentation
                        tools=[{"type": "web_search"}],
                        input=prompt,
                    )
                    # Correctly access the response text from the Responses API object
                    text = response.output_text.strip()

                except Exception as e:
                    st.error(f"An API error occurred while comparing '{book1}' and '{book2}': {e}")
                    st.info("This may be due to not having access to the 'gpt-5' model or the Responses API, or an out-of-date 'openai' library.")
                    continue

                # Reliable detection based on the prompt's instructions
                if text.lower().startswith("yes"):
                    explanation = text[4:].strip() # Remove "YES:"
                    G.add_edge(book1, book2, title=explanation, color="#3a78d1")
                
                progress_bar.progress((i + 1) / total_pairs)

            status_text.success("Analysis complete! Rendering visualization...")

            # --- Visualize with PyVis ---
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

                # Save to a temporary file to display in Streamlit
                with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
                    net.save_graph(tmp_file.name)
                    with open(tmp_file.name, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                
                st.components.v1.html(html_content, height=720, scrolling=True)
                os.unlink(tmp_file.name) # Clean up the temp file

else:
    st.info("Enter some books and click 'Generate Knowledge Map' to see the connections.")
