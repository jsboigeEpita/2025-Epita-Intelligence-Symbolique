import streamlit as st
import requests

# Configuration
BASE_URL = "http://localhost:9001"

st.set_page_config(page_title="Recherche & QA Sémantique", layout="wide")
st.title("🧠 Recherche & Questions sur les Discours Historiques")

# Onglets Streamlit : Search ou Ask
tab1, tab2 = st.tabs(["🔍 Recherche Sémantique", "🤖 Question Answering (Ask)"])

# ---- 🔍 Onglet Search ----
with tab1:
    st.subheader("Recherche Sémantique")
    query = st.text_input("Entrez un mot-clé ou une requête pour trouver des extraits :", key="search_input")

    if st.button("Rechercher", key="search_button") and query.strip():
        try:
            payload = {"query": query}
            response = requests.post(f"{BASE_URL}/api/search", json=payload)
            response.raise_for_status()
            results = response.json().get('results', [])

            if not results:
                st.warning("Aucun résultat trouvé.")
            else:
                st.success(f"{len(results)} résultats trouvés.")
                for idx, item in enumerate(results, 1):
                    with st.expander(f"Résultat {idx} - Score: {item['relevance']:.2f}"):
                        st.write(item['text'][:800] + ('...' if len(item['text']) > 800 else ''))
                        st.json(item.get('tags', {}))
        except requests.exceptions.RequestException as e:
            st.error(f"Erreur lors de la recherche : {e}")

# ---- 🤖 Onglet Ask ----
with tab2:
    st.subheader("Question Answering (Ask)")
    question = st.text_input("Posez une question sur le contenu :", key="ask_input")

    if st.button("Poser la question", key="ask_button") and question.strip():
        try:
            payload = {"question": question}
            response = requests.post(f"{BASE_URL}/api/ask", json=payload)
            response.raise_for_status()
            answer = response.json()

            if 'text' in answer:
                st.success("Réponse générée :")
                st.write(answer['text'])
                st.subheader("Sources Utilisées :")
                for idx, doc in enumerate(answer.get('citations', []), 1):
                    with st.expander(f"Source {idx} - {doc.get('tags', {}).get('source', 'Inconnu')}"):
                        st.write(doc['text'][:800] + ('...' if len(doc['text']) > 800 else ''))
                        st.json(doc.get('tags', {}))
            else:
                st.warning("Pas de réponse générée.")

        except requests.exceptions.RequestException as e:
            st.error(f"Erreur lors de la question : {e}")

st.caption("✨ Propulsé par OpenAI Embeddings + Kernel Memory + Streamlit")
