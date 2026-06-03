# Azure Product Recommendation Swarm

Streamlit prototype for an Azure-native product recommendation workflow. The application accepts text, optional voice input, and optional image input, then returns catalog-grounded recommendations with transparent pipeline trace details.

## Features

- Customer recommendation workflow with multimodal input support
- Admin catalog operations for upload, manual entry, and search sync
- Catalog import support for CSV, JSON, and PDF
- Azure AI Search-backed retrieval with explicit datastore availability handling
- Optional Azure OpenAI, Vision, Speech, and Document Intelligence integrations

## Recommendation Pipeline

The recommendation flow is implemented as staged agents:

1. `QueryPreprocessor`
2. `QueryInterpreter`
3. `CatalogSearch`
4. `ValueScorer`
5. `ImageMatcher` (if image provided)
6. `Explainer`
7. `Validator`

## Prerequisites

- Python 3.10+
- PowerShell (Windows)
- Azure AI Search service (required for retrieval)
- Optional Azure services: OpenAI, Vision, Speech, Document Intelligence

## Local Setup

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies.
4. Create `.env` from `.env.template`.

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.template .env
```

## Environment Variables

Minimum required keys in `.env`:

- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_API_KEY`
- `AZURE_SEARCH_INDEX_NAME`

Optional keys for richer features:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`
- `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`
- `AZURE_DOCUMENT_INTELLIGENCE_KEY`
- `AZURE_VISION_ENDPOINT`
- `AZURE_VISION_KEY`
- `AZURE_SPEECH_KEY`
- `AZURE_SPEECH_REGION`

## Run the App

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python -m streamlit run app.py
```

Open `http://localhost:8501`.

You can also use the VS Code task `Run Streamlit Prototype`.

## Lab Manual

- Offline text manual: [LAB_MANUAL.txt](LAB_MANUAL.txt)
- GitHub Pages manual source: [docs/index.md](docs/index.md)

## Publish the Manual with GitHub Pages

1. Push this repository to GitHub.
2. Open repository `Settings` > `Pages`.
3. Under `Build and deployment`, select `Deploy from a branch`.
4. Select branch `main` and folder `/docs`.
5. Save and wait for deployment.

Your site URL will be:

- `https://<your-github-username>.github.io/<repo-name>/`

## Admin Workflow Summary

1. Open `Admin Catalog` tab.
2. Upload catalog (`.csv`, `.json`, or `.pdf`).
3. Choose replace or extend behavior.
4. Click `Ingest`.
5. Click `Sync catalog to Azure AI Search`.

## Notes

- Recommendation retrieval depends on Azure AI Search availability.
- Vision-based matching requires Azure AI Vision.
- Voice transcription requires Azure Speech.
- PDF ingestion requires Azure Document Intelligence.
