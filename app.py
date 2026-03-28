"""Azure Solutions Recommender — Streamlit UI."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st

from recommendation_engine import AzureRecommender, Settings

# ---- Page config ----------------------------------------------------------

st.set_page_config(
    page_title="Azure Solutions Recommendation Engine",
    page_icon="\u2601\ufe0f",
    layout="wide",
)

# ---- Sidebar: configuration info -------------------------------------------

with st.sidebar:
    st.header("\u2699\ufe0f Configuration")

    max_results = st.slider("Max search results per source", 1, 10, 5)

    st.divider()

    st.subheader("\U0001f9d1\u200d\U0001f52c Persona")
    enable_ds = st.toggle(
        "Senior Data Scientist & AI Retriever",
        value=False,
        help=(
            "Enable this to get recommendations from a virtual Senior Data "
            "Scientist focused on Azure AI services, ML pipelines, MLOps, "
            "and responsible AI."
        ),
    )
    if enable_ds:
        st.info("Persona active — responses will focus on data science & AI.")

    st.divider()

    settings = Settings(max_search_results=max_results)

    if settings.use_azure:
        st.success("Using **Azure OpenAI** (from .env)")
    elif settings.openai_api_key:
        st.success("Using **OpenAI** (from .env)")
    else:
        st.warning(
            "No LLM provider configured. Set `AZURE_OPENAI_ENDPOINT` + "
            "`AZURE_OPENAI_API_KEY` or `OPENAI_API_KEY` in your `.env` file."
        )

    st.caption(
        "All recommendations are grounded in content retrieved at query time from "
        "[Microsoft Learn](https://learn.microsoft.com) and the "
        "[Azure Architecture Center](https://learn.microsoft.com/azure/architecture/)."
    )

# ---- Main area ------------------------------------------------------------

st.title("\u2601\ufe0f Azure Solutions Recommender")
st.markdown(
    "Describe your use case and get architect-friendly Azure + Microsoft AI "
    "service recommendations grounded in official Microsoft documentation."
)

if not settings.is_configured:
    st.info(
        "No LLM provider configured. Set your credentials in a `.env` file — "
        "see `.env.example` for the required variables."
    )
    st.stop()

# ---- Use-case input -------------------------------------------------------

use_case = st.text_area(
    "Describe your use case",
    height=150,
    placeholder=(
        "e.g., We need a real-time chat application with AI-powered "
        "summarization for customer support. Expected load is ~10K "
        "concurrent users. Must comply with GDPR..."
    ),
)

recommend_btn = st.button(
    "\U0001f50d Recommend", type="primary", disabled=not use_case
)

# ---- Session state --------------------------------------------------------

if "recommendation" not in st.session_state:
    st.session_state.recommendation = ""
if "diagram" not in st.session_state:
    st.session_state.diagram = ""

# ---- Run recommendation ---------------------------------------------------

if recommend_btn and use_case:
    st.session_state.recommendation = ""
    st.session_state.diagram = ""

    recommender = AzureRecommender(settings)

    # Step 1 — Retrieve documentation
    with st.status(
        "Retrieving documentation from Microsoft Learn & Architecture Center\u2026",
        expanded=True,
    ) as status:
        retrieval = recommender.retrieve_context(use_case)
        learn_count = len(retrieval.learn_docs)
        arch_count = len(retrieval.architecture_docs)
        st.write(
            f"Found **{learn_count}** Learn docs and "
            f"**{arch_count}** Architecture Center docs."
        )

        if retrieval.learn_docs:
            with st.expander("\U0001f4da Retrieved Learn Documents"):
                for doc in retrieval.learn_docs:
                    st.markdown(f"- [{doc.title}]({doc.url})")

        if retrieval.architecture_docs:
            with st.expander("\U0001f3d7\ufe0f Retrieved Architecture Documents"):
                for doc in retrieval.architecture_docs:
                    st.markdown(f"- [{doc.title}]({doc.url})")

        grounding_label = (
            "Strong" if (learn_count + arch_count) >= 4
            else "Moderate" if (learn_count + arch_count) >= 2
            else "Limited"
        )
        status.update(
            label=(
                f"Retrieved {learn_count + arch_count} documents "
                f"({grounding_label} grounding)"
            ),
            state="complete",
        )

    # Step 2 — Stream recommendation
    persona = "data_scientist" if enable_ds else "architect"
    st.subheader("Recommendation")
    try:
        full_response = st.write_stream(
            recommender.recommend_stream(use_case, retrieval, persona=persona)
        )
        st.session_state.recommendation = full_response or ""
    except Exception as exc:
        st.error(f"LLM call failed: {exc}")
        st.stop()

# ---- Display cached recommendation on rerun -------------------------------

elif st.session_state.recommendation:
    st.subheader("Recommendation")
    st.markdown(st.session_state.recommendation)

# ---- Diagram generation ---------------------------------------------------

if st.session_state.recommendation:
    st.divider()

    if st.button("\U0001f4ca Generate Architecture Diagram (Mermaid)"):
        recommender = AzureRecommender(settings)

        with st.spinner("Generating Mermaid diagram\u2026"):
            diagram_chunks: list[str] = []
            try:
                for chunk in recommender.generate_diagram_stream(
                    st.session_state.recommendation
                ):
                    diagram_chunks.append(chunk)
            except Exception as exc:
                st.error(f"Diagram generation failed: {exc}")

            raw = "".join(diagram_chunks).strip()

            # Strip markdown fences if the model wrapped the output
            if raw.startswith("```"):
                lines = raw.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                raw = "\n".join(lines).strip()

            st.session_state.diagram = raw

    if st.session_state.diagram:
        st.subheader("Architecture Diagram")
        st.markdown(f"```mermaid\n{st.session_state.diagram}\n```")

        with st.expander("\U0001f4cb Mermaid Source Code"):
            st.code(st.session_state.diagram, language="mermaid")
