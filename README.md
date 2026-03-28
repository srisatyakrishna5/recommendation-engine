# Azure Product Recommendation Swarm

This repository contains a Streamlit prototype for an Azure-native product recommendation engine. The app accepts typed requests, optional speech input, and uploaded images, then routes the request through a catalog-grounded recommendation pipeline.

## What is included

- Streamlit UI for customer and admin workflows
- Local catalog persistence with Azure AI Search sync support
- Azure OpenAI GPT-4o powered need interpretation and recommendation guidance
- Azure Document Intelligence wrapper for PDF analysis
- Azure Speech wrapper for voice input transcription
- Azure Vision wrapper for image caption and tag extraction

## Pipeline design

The recommendation flow is implemented as a staged recommendation pipeline:

1. `QueryInterpreter` extracts the shopper's problem, budget, and buying constraints.
2. `CatalogSearch` retrieves products from Azure AI Search.
3. `ValueScorer` reranks products for cost effectiveness.
4. `Explainer` explains why each product fits and how it solves the user's problem.
5. `Validator` ensures only catalog-backed recommendations are returned.

## Azure services expected

- Azure OpenAI with a `gpt-4o` deployment
- Azure AI Search for catalog retrieval and vector-ready indexing
- Azure Document Intelligence for PDF ingestion
- Azure AI Vision for image understanding
- Azure Speech Service for speech-to-text

## Run locally

1. Copy `.env.template` to `.env` and add your Azure settings.
2. Install dependencies into the existing virtual environment.
3. Run the Streamlit app.

```powershell
.venv\Scripts\python -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
.venv\Scripts\python -m streamlit run app.py
```

## Admin workflow

- Upload a CSV or JSON product catalog
- Add manual products through the UI
- Push the active catalog into Azure AI Search when the search settings are present

## Notes

- Product retrieval depends on Azure AI Search. If the search datastore is unavailable, the app returns an explicit unavailability message instead of falling back to local catalog search.
- PDF analysis requires Azure Document Intelligence.
- Image-based matching requires Azure AI Vision. The app returns an explicit no-match response instead of using local image heuristics.
