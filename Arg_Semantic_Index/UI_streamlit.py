import streamlit as st
import requests

# Configuration
BASE_URL = "http://localhost:9001"

st.set_page_config(page_title="Recherche & QA Sémantique", layout="wide")
st.title("🧠 Recherche & Questions sur les Discours Historiques")

# Onglets Streamlit : Search ou Ask
tab1, tab2 = st.tabs(["🔍 Recherche Sémantique", "🤖 Question Answering (Ask)"])

# ---------- 🔍 Onglet SEARCH ----------
with tab1:
    st.subheader("Recherche sémantique")
    search_query = st.text_input("Entrez une requête à rechercher :", key="search")

    if st.button("Rechercher", key="btn_search") and search_query.strip():
        try:
            response = requests.post(f"{BASE_URL}/search", json={"query": search_query})
            response.raise_for_status()
            search_data = response.json()

            # On récupère toutes les partitions dans tous les résultats
            all_excerpts = []
            for result in search_data.get("results", []):
                doc_id = result.get("documentId", "")
                index = result.get("index", "")
                for part in result.get("partitions", []):
                    excerpt = {
                        "text": part.get("text", "").replace("\n", " ").strip(),
                        "relevance": part.get("relevance", 0),
                        "documentId": doc_id,
                        "index": index
                    }
                    all_excerpts.append(excerpt)

            # Trier par pertinence décroissante et garder les 5 meilleurs
            top_excerpts = sorted(all_excerpts, key=lambda x: x["relevance"], reverse=True)[:5]

            if not top_excerpts:
                st.warning("Aucun extrait pertinent trouvé.")
            else:
                st.success(f"Top 5 extraits les plus pertinents :")
                for i, ex in enumerate(top_excerpts, start=1):
                    st.markdown(f"### Extrait {i}")
                    st.markdown(f"> *{ex['text'][:500]}{'...' if len(ex['text']) > 500 else ''}*")
                    st.caption(f"📄 Source: `{ex['documentId']}` — Pertinence: **{ex['relevance']:.3f}**")
                    st.markdown("---")

        except Exception as e:
            st.error(f"Erreur lors de la recherche : {e}")


# ---------- 🤖 Onglet ASK ----------
with tab2:
    st.subheader("Posez une question (Ask)")
    ask_question = st.text_input("Entrez votre question :", key="ask")

    if st.button("Poser la question", key="btn_ask") and ask_question.strip():
        try:
            response = requests.post(f"{BASE_URL}/ask", json={"question": ask_question})
            response.raise_for_status()
            ask_data = response.json()

            # Affichage de la réponse principale
            if ask_data.get("text"):
                st.success("🧠 Réponse générée :")
                st.write(ask_data["text"])
            elif ask_data.get("noResult"):
                st.warning(f"Aucune réponse générée : {ask_data.get('noResultReason', 'pas de contexte trouvé.')}")

            # Affichage des sources pertinentes (relevantSources)
            relevant_sources = ask_data.get("relevantSources", [])
            if relevant_sources:
                st.subheader("📄 Sources utilisées :")
                for i, source in enumerate(relevant_sources, start=1):
                    source_name = source.get("sourceName", f"source_{i}")
                    st.markdown(f"### Source {i} — *{source_name}*")

                    partitions = source.get("partitions", [])
                    for j, part in enumerate(partitions, start=1):
                        text = part.get("text", "").replace("\n", " ").strip()
                        relevance = part.get("relevance", 0)
                        tags = part.get("tags", {})

                        st.markdown(f"> *{text[:500]}{'...' if len(text) > 500 else ''}*")
                        st.caption(f"Pertinence : {relevance:.3f}")

                    st.markdown("---")
            else:
                st.info("Aucune source n’a été utilisée pour générer cette réponse.")
        except Exception as e:
            st.error(f"Erreur lors de la requête ASK : {e}")


st.caption("✨ Propulsé par OpenAI Embeddings + Kernel Memory + Streamlit")
