# Obsidian Cloud Brain

> A scalable RAG architecture on Azure to query 1000+ Obsidian notes in natural language.

![CI](https://github.com/CedrickMakhlouf/obsidian-cloud-brain/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Azure](https://img.shields.io/badge/cloud-Azure-0078D4)
![License](https://img.shields.io/badge/license-MIT-green)

---

### 🚀 [Try the live API demo on Azure →](https://obsidian-api.ambitiousmoss-cd4cf8a8.eastus.azurecontainerapps.io/docs)

> **Note:** The live demo is indexed on a small set of sample notes — not my full private vault. Deploy your own instance to query your own notes.


```powershell
# PowerShell
curl.exe -X POST https://obsidian-api.ambitiousmoss-cd4cf8a8.eastus.azurecontainerapps.io/ask `
  -H "Content-Type: application/json" `
  -d '{\"question\": \"What do I know about deep learning?\"}'
```

```bash
# bash / WSL / macOS
curl -X POST https://obsidian-api.ambitiousmoss-cd4cf8a8.eastus.azurecontainerapps.io/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What do I know about deep learning?"}'
```

---

## The Problem

After years of note-taking in Obsidian I ended up with a vault of 1000+ Markdown files.
Keyword search stopped working, I knew I had written something down, just not where or how.
**Keyword search doesn't solve this. Semantic search does.**

## The Solution

A fully cloud-native **Retrieval-Augmented Generation (RAG)** pipeline:

```
Obsidian Vault (.md)
       │
       ▼
Azure Blob Storage          ← raw notes stored as blobs
       │
       ▼
Azure OpenAI (Embeddings)   ← text converted to 1536-dimensional vectors
       │
       ▼
Azure AI Search (Vector DB) ← semantically searchable index
       │
       ▼
FastAPI + GPT-4o            ← ask questions in natural language
       │
       ▼
Azure Container Apps        ← scalable, serverless deployment
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Data Pipeline | Python, Azure Blob Storage SDK |
| Vector Index | Azure AI Search, Azure OpenAI Embeddings |
| RAG API | FastAPI, GPT-4o |
| Infrastructure | Azure Bicep (IaC) |
| Containerisation | Docker, Azure Container Apps |
| CI/CD | GitHub Actions |
| Code quality | Ruff (linter), Pytest |

---

## Project Structure

```
obsidian-cloud-brain/
├── .github/workflows/
│   ├── ci.yml              # Lint + tests on every PR
│   └── cd.yml              # Auto-deploy to Azure on merge to main
├── infra/
│   ├── main.bicep          # Full Azure environment as code
│   └── params.json         # Deployment parameters
├── src/
│   ├── config.py           # Central configuration (pydantic-settings)
│   ├── ingestion/
│   │   ├── upload_vault.py # Phase 1: Obsidian → Azure Blob Storage
│   │   └── build_index.py  # Phase 2: Embeddings → Azure AI Search
│   ├── retrieval/
│   │   └── rag.py          # RAG logic (hybrid vector + keyword search)
│   └── api/
│       └── main.py         # FastAPI endpoints
├── tests/
│   ├── test_ingestion.py
│   └── test_api.py
├── Dockerfile
├── requirements.txt
└── .env.example            # Example keys (never commit real keys!)
```

---

## Getting Started

### 1. Set up environment

```bash
git clone https://github.com/CedrickMakhlouf/obsidian-cloud-brain.git
cd obsidian-cloud-brain

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

cp .env.example .env
# Fill in your Azure credentials in .env
```

### 2. Deploy Azure infrastructure (IaC)

```bash
# Create a resource group
az group create --name rg-obsidian-brain --location westeurope

# Deploy all Azure resources with a single command
az deployment group create \
  --resource-group rg-obsidian-brain \
  --template-file infra/main.bicep \
  --parameters @infra/params.json
```

### 3. Run the data pipeline

```bash
# Phase 1: Upload your Obsidian vault to Azure Blob Storage
python -m src.ingestion.upload_vault

# Phase 2: Build the vector index in Azure AI Search
python -m src.ingestion.build_index
```

### 4. Run the API locally

```bash
uvicorn src.api.main:app --reload
# Open: http://localhost:8000/docs
```

### 5. Ask a question

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What do I know about Docker networking?"}'
```

---

## Adding New Notes

When you add or update notes in your Obsidian vault, re-run the two ingestion scripts:

```bash
# Step 1: sync changes to Blob Storage (only uploads new/changed notes via MD5 check)
python src/ingestion/upload_vault.py

# Step 2: rebuild the vector index in Azure AI Search
python src/ingestion/build_index.py
```

The live API picks up the new notes immediately, no redeploy needed.

---

## Docker

```bash
# Build
docker build -t obsidian-api .

# Run (using your .env file)
docker run -p 8000:8000 --env-file .env obsidian-api
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Highlight: Infrastructure as Code

The full Azure environment (Storage Account, AI Search, Container Apps) is defined in
[infra/main.bicep](infra/main.bicep). This means:

- **Reproducible**: any environment (dev/test/prod) can be spun up with a single command.
- **Version-controlled**: infrastructure changes are tracked in Git.
- **Cost control**: `scale.minReplicas: 0` ensures the Container App scales to zero when idle.

---

## Architecture Decisions

| Decision | Choice | Reason |
|---|---|---|
| Vector DB | Azure AI Search | Hybrid search (vector + keyword) in a single service |
| Embedding model | text-embedding-3-small | Best price/quality ratio |
| LLM | GPT-4o via Azure OpenAI | Enterprise-grade, data stays in Europe |
| Chunking | 1000 chars, 100 overlap | Balance between context and precision |
| Deployment | Azure Container Apps | Serverless, scales to zero, no Kubernetes needed |

---

## Roadmap

- [ ] Add authentication (Azure AD / API-key middleware)
- [ ] Streaming responses via Server-Sent Events
- [ ] Visualise note graph (Obsidian links → Azure Cosmos DB)
- [ ] Automatic re-indexing via Azure Function on new notes

---

## License

MIT – see [LICENSE](LICENSE)
