# Azure Product Recommendation Swarm

Lab manual for setup, execution, catalog operations, and troubleshooting.

Last updated: 2026-06-03

## 1. Objective

This manual helps you run and operate the recommendation application end to end.

After completing this lab, you can:

- Configure environment settings for Azure-backed retrieval.
- Launch the Streamlit application locally.
- Execute customer and admin workflows.
- Publish this manual as a GitHub Pages site.

## 2. What the Application Does

The application provides catalog-grounded recommendations based on:

- Text input
- Optional voice input
- Optional image input

The UI includes two tabs:

- Customer Assistant
- Admin Catalog

### Customer Assistant

- Accepts typed queries.
- Accepts optional voice notes.
- Accepts optional image uploads.
- Returns summary, guidance, ranked products, and processing trace.

### Admin Catalog

- Displays catalog products and summary metrics.
- Imports product catalogs from CSV, JSON, or PDF.
- Adds products manually.
- Syncs catalog to Azure AI Search.

## 3. Pipeline Overview

The recommendation pipeline follows these stages:

1. `QueryPreprocessor`
2. `QueryInterpreter`
3. `CatalogSearch`
4. `ValueScorer`
5. `ImageMatcher` (if image provided)
6. `Explainer`
7. `Validator`

Design principle:

- Responses remain grounded in catalog products.
- If Azure AI Search is unavailable, the app returns an explicit availability message.

## 4. Prerequisites

Required:

- Python 3.10+
- Windows PowerShell
- Internet connection

Required for retrieval:

- Azure AI Search endpoint, key, and index

Optional integrations:

- Azure OpenAI
- Azure AI Vision
- Azure Speech
- Azure Document Intelligence

## 5. Setup

Open PowerShell from the project root and run:

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.template .env
```

## 6. Environment Configuration

Edit `.env` and provide Azure values.

Minimum required variables:

- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_API_KEY`
- `AZURE_SEARCH_INDEX_NAME`

Optional variables:

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

Security reminder:

- Never commit `.env`.
- Never expose API keys in screenshots or logs.

## 7. Run the Application

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python -m streamlit run app.py
```

Open the app at:

- `http://localhost:8501`

## 8. Customer Assistant Workflow

1. Enter a natural language request.
2. Optionally record voice input.
3. Optionally upload a product or context image.
4. Select **Get Personalized Recommendations**.
5. Review summary, product cards, and processing trace.

## 9. Admin Catalog Workflow

1. Open **Admin Catalog** tab.
2. Review current products and metrics.
3. Upload a catalog file (`.csv`, `.json`, `.pdf`).
4. Choose whether to replace or extend current catalog.
5. Select **Ingest**.
6. Select **Sync catalog to Azure AI Search**.

Manual product add form requires:

- Product name
- Description

Recommended manual fields:

- Category
- Price
- Rating
- Tags
- Use cases
- Benefits

## 10. Catalog File Guidelines

Accepted upload types:

- CSV
- JSON
- PDF

Recommended product fields:

- `id` (optional)
- `sku` (optional)
- `name` or `product_name` or `title`
- `category`
- `description`
- `price`
- `rating`
- `tags`
- `use_cases`
- `benefits`
- `image_hints`

Tips:

- Use concrete names.
- Keep descriptions practical and short.
- Add searchable tags such as `wireless`, `pet-hair`, `HEPA`, `kitchen`.

## 11. Troubleshooting

### No recommendations due to datastore unavailable

- Verify `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_API_KEY`, and `AZURE_SEARCH_INDEX_NAME`.
- Confirm the Azure AI Search index is reachable.
- Run catalog sync again from Admin Catalog.

### App fails to start due to missing modules

- Confirm `.venv` is active.
- Reinstall dependencies:

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
```

### Image uploaded but no image-based matching

- Set `AZURE_VISION_ENDPOINT` and `AZURE_VISION_KEY`.
- Retry with a clearer image.

### Voice input not available

- Verify browser microphone permissions.
- Verify `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION`.

### Catalog changes not reflected in results

- Run **Sync catalog to Azure AI Search** after catalog updates.

## 12. Stop the App

In the terminal running Streamlit, press `Ctrl + C`.

## 13. Publish This Manual on GitHub Pages

1. Push the repository to GitHub.
2. Open repository **Settings** > **Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**.
4. Select branch `main` and folder `/docs`.
5. Save and wait for deployment.

Site URL format:

- `https://<your-github-username>.github.io/<repo-name>/`
