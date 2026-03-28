# Azure Solutions Recommender

A Streamlit application that recommends Azure + Microsoft AI services for solution architects. All recommendations are **grounded at query time** in official Microsoft documentation — no local catalogs or static inventories.

## Features

- **Live retrieval** via the [Microsoft Learn MCP Server](https://learn.microsoft.com/training/support/mcp) (`microsoft_docs_search`, `microsoft_docs_fetch`, `microsoft_code_sample_search`)
- **Streaming LLM recommendations** using Azure OpenAI or standard OpenAI
- **Strict 6-section output format**: Use-case understanding, Service shortlist, Reference architecture, Alternatives & tradeoffs, WAF checklist, Next steps
- **Mermaid architecture diagrams** generated on demand and rendered in-app
- **Responsible AI** guardrails baked into the system prompt (no Azure AI Search, source citations required, tentative labeling when grounding is thin)

## Prerequisites

- Python 3.10+
- An Azure OpenAI resource **or** an OpenAI API key
- (Optional) A `.env` file for persistent configuration

## Quick Start

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your LLM provider
copy .env.example .env          # then edit .env with your keys

# 4. Run the app
$env:PYTHONPATH = "src"         # PowerShell
streamlit run app.py
```

You can also configure API keys directly in the Streamlit sidebar at runtime.

## Project Structure

```
app.py                                  # Streamlit entrypoint
requirements.txt                        # Python dependencies
.env.example                            # Environment variable template
src/
  recommendation_engine/
    __init__.py                         # Package exports
    settings.py                         # Configuration (env vars + overrides)
    retriever.py                        # Microsoft Learn MCP retrieval layer
    prompts.py                          # System prompts & templates
    recommender.py                      # LLM orchestration (streaming)
```

## Architecture

```
User (Streamlit UI)
  |
  v
AzureRecommender
  |-- MicrosoftLearnRetriever (MCP Python SDK)
  |     |-- microsoft_docs_search   (semantic search over MS Learn)
  |     |-- microsoft_docs_fetch     (full page as markdown)
  |     |-- Endpoint: https://learn.microsoft.com/api/mcp
  |
  |-- Azure OpenAI / OpenAI (streaming chat completions)
  |
  v
Structured Recommendation (6 sections) + Optional Mermaid Diagram
```

## Configuration Reference

| Variable | Description | Default |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource endpoint | — |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | — |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment / model name | `gpt-4o` |
| `AZURE_OPENAI_API_VERSION` | API version | `2024-12-01-preview` |
| `OPENAI_API_KEY` | Standard OpenAI API key | — |
| `OPENAI_MODEL` | OpenAI model name | `gpt-4o` |
| `MAX_SEARCH_RESULTS` | Results per retrieval source | `5` |
