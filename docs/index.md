# Azure Product Recommendation Swarm

Step-by-step lab manual to set up, access, and run the application.

Last updated: 2026-06-03

## 1. Start Here

This manual is written as an execution checklist.

When you finish all steps, you will have:

1. A working local environment.
2. The app running on your machine.
3. A validated recommendation flow in the UI.

Estimated time: 15 to 25 minutes.

## 2. Prerequisites

Before you begin, make sure you have:

- Windows PowerShell
- Python 3.10 or newer
- Git (if cloning the repository)
- Internet connection

Azure requirements:

- Required for recommendation retrieval:
  - Azure AI Search endpoint, key, and index name
- Optional for advanced features:
  - Azure OpenAI
  - Azure AI Vision
  - Azure Speech
  - Azure Document Intelligence

## 3. Step 1 - Get the Project

If you already have the project folder, continue to Step 2.

If not, run:

```powershell
git clone https://github.com/srisatyakrishna5/recommendation-engine.git
cd recommendation-engine
```

Expected result:

- You are inside the project root.
- You can see `app.py`, `requirements.txt`, and the `src` folder.

## 4. Step 2 - Create and Activate Virtual Environment

Run these commands from the project root:

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Expected result:

- Your terminal prompt shows `(.venv)`.

If activation fails due to script policy, run the policy command again in the same terminal and retry activation.

## 5. Step 3 - Install Dependencies

Run:

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
```

Expected result:

- Packages install without errors.
- `streamlit` is installed in the virtual environment.

Optional validation:

```powershell
.\.venv\Scripts\python -m pip show streamlit
```

## 6. Step 4 - Configure Environment File

Create your runtime environment file:

```powershell
Copy-Item .env.template .env
```

Open `.env` and update values.

Minimum required keys (must be set):

- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_API_KEY`
- `AZURE_SEARCH_INDEX_NAME`

Optional keys (enable additional capabilities):

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

Security rules:

- Do not commit `.env`.
- Do not paste secrets into public issues or screenshots.

## 7. Step 5 - Run the Application

Run:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python -m streamlit run app.py
```

Expected result in terminal:

- Streamlit starts successfully.
- A local URL appears, usually `http://localhost:8501`.

Alternative in VS Code:

1. Open Command Palette.
2. Select Tasks: Run Task.
3. Run `Run Streamlit Prototype`.

## 8. Step 6 - Access the Application

Open your browser and go to:

- `http://localhost:8501`

Expected UI:

- Header with service readiness pills.
- Tab 1: Customer Assistant.
- Tab 2: Admin Catalog.

If the browser does not auto-open, copy the URL from terminal and open it manually.

## 9. Step 7 - Validate End-to-End Flow

### 9.1 Customer Assistant Quick Test

1. In Customer Assistant, enter the prompt below:

   `Suggest affordable products for cleaning kitchen floors.`
2. Click **Get Personalized Recommendations**.
3. Confirm you see summary, product cards, and processing trace.

### 9.2 Admin Catalog Quick Test

1. Open Admin Catalog.
2. Confirm products are visible in the table.
3. Optionally upload a catalog file (`.csv`, `.json`, `.pdf`).
4. Click **Ingest**.
5. Click **Sync catalog to Azure AI Search**.

## 10. Step 8 - Stop the Application

In the terminal running Streamlit, press:

- `Ctrl + C`

## 11. Troubleshooting

### Problem: App does not start

Actions:

1. Confirm virtual environment is active (`(.venv)` in prompt).
2. Reinstall dependencies.
3. Run command again.

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
.\.venv\Scripts\python -m streamlit run app.py
```

### Problem: "Azure datastore unavailable" in recommendations

Actions:

1. Verify `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_API_KEY`, and `AZURE_SEARCH_INDEX_NAME` in `.env`.
2. Confirm Azure AI Search index exists and is reachable.
3. Use Admin Catalog and click **Sync catalog to Azure AI Search**.

### Problem: Voice or image features not working

Actions:

1. Verify the related keys in `.env`.
2. For voice, check browser microphone permissions.
3. Retry with a clear audio sample or image.

## 12. Operational Notes

- Recommendations are catalog-grounded.
- CSV, JSON, and PDF are supported for catalog ingestion.
- If a service is not configured, related functionality can appear as offline.

## 13. Publish or Update This Manual on GitHub Pages

This hosted page is built from `docs/index.md`.

To update what is shown on GitHub Pages:

1. Edit `docs/index.md` in this repository.
2. Commit and push to the `main` branch.
3. Ensure GitHub Pages is configured to deploy from branch `main` and folder `/docs`.
4. Wait for Pages deployment to complete.
5. Refresh `https://srisatyakrishna5.github.io/recommendation-engine/`.

## 14. Quick Command Block

Use this full sequence when setting up from scratch:

```powershell
git clone https://github.com/srisatyakrishna5/recommendation-engine.git
cd recommendation-engine
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.template .env
$env:PYTHONPATH = "src"
.\.venv\Scripts\python -m streamlit run app.py
```
