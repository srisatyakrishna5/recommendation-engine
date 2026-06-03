# Product Recommendation Engine

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

## Step-by-Step Setup and Run

### Step 1: Get the project

If you do not already have the repository locally:

```powershell
git clone https://github.com/srisatyakrishna5/recommendation-engine.git
cd recommendation-engine
```

### Step 2: Create and activate virtual environment

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Expected result: your terminal prompt shows `(.venv)`.

### Step 3: Install dependencies

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
```

### Step 4: Configure environment variables

Create `.env` from template:

```powershell
Copy-Item .env.template .env
```

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

### Step 5: Run the app

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python -m streamlit run app.py
```

Expected result:

- Streamlit starts without error.
- The local URL `http://localhost:8501` is shown.

### Step 6: Access and validate

1. Open `http://localhost:8501` in browser.
2. In Customer Assistant, enter: `Suggest affordable products for cleaning kitchen floors.`
3. Click **Get Personalized Recommendations**.
4. Confirm summary, product cards, and processing trace are visible.

You can also start from VS Code using task **Run Streamlit Prototype**.

## Lab Manual

- Offline text manual: [LAB_MANUAL.txt](LAB_MANUAL.txt)
- GitHub Pages manual source: [docs/index.md](docs/index.md)
- Live GitHub Pages manual: [https://srisatyakrishna5.github.io/recommendation-engine/](https://srisatyakrishna5.github.io/recommendation-engine/)

## Publish the Manual with GitHub Pages

1. Edit [docs/index.md](docs/index.md).
2. Commit and push to branch `main`.
3. Open repository `Settings` > `Pages`.
4. Ensure source is `Deploy from a branch`, branch `main`, folder `/docs`.
5. Wait for deployment, then refresh the live URL.

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
- Do not commit `.env` or any credential values.
