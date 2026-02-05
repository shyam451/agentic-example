# DocAI Agentic - ADK Setup Guide

This guide explains how to set up, run, and deploy the DocAI Agentic system using Google ADK (Agent Development Kit).

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Local Development](#local-development)
5. [Deployment to Vertex AI Agent Engine](#deployment-to-vertex-ai-agent-engine)
6. [Architecture Overview](#architecture-overview)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

- **Python 3.10 or higher**
- **Google Cloud Project** with billing enabled
- **Google Cloud CLI** (`gcloud`) installed and authenticated
- **Node.js 18+** (for MCP filesystem tools)

### Google Cloud APIs to Enable

```bash
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable documentai.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
```

---

## Installation

### 1. Clone and Navigate to Project

```bash
cd /Users/shyamnair/code/docai-agentic
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate  # On Windows
```

### 3. Install Dependencies

```bash
# Install core dependencies including Google ADK
pip install -r deployment/requirements.txt

# Install spaCy language model for NER
python -m spacy download en_core_web_sm

# Install MCP filesystem server (for local file access)
npm install -g @modelcontextprotocol/server-filesystem
```

### 4. Verify ADK Installation

```bash
adk --version
```

You should see output like: `ADK version 1.23.0`

---

## Configuration

### 1. Set Up Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and configure your settings:

```bash
# Required
GOOGLE_CLOUD_PROJECT=your-actual-project-id
GOOGLE_CLOUD_REGION=us-central1
GOOGLE_API_KEY=your-gemini-api-key

# Optional
GEMINI_MODEL=gemini-2.0-flash-exp
GCS_BUCKET=docai-extraction-your-project-id
ENABLE_GCS=false
```

### 2. Get Google API Key

You need a Gemini API key for local development:

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create an API key
3. Add it to your `.env` file

### 3. Authenticate with Google Cloud

```bash
# Login to Google Cloud
gcloud auth login

# Set application default credentials
gcloud auth application-default login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

### 4. Create GCS Bucket (Optional)

If you want to use Google Cloud Storage:

```bash
export PROJECT_ID=your-project-id
gsutil mb -l us-central1 gs://docai-extraction-${PROJECT_ID}
gsutil cp schemas/*.json gs://docai-extraction-${PROJECT_ID}/schemas/
```

---

## Local Development

### Running the Agent Locally

#### Option 1: CLI Mode (Interactive)

```bash
adk run agent
```

This starts an interactive CLI where you can chat with the agent.

Example interaction:
```
You: Extract data from documents/invoice.pdf
Agent: I'll process that invoice for you...
```

#### Option 2: Web UI (Recommended for Development)

```bash
adk web --port 8000
```

Then open your browser to `http://localhost:8000`

The web UI provides:
- Interactive chat interface
- Session history
- Agent state visualization
- Tool call inspection

### Testing Individual Agents

You can test specialized agents independently:

```python
from agents.invoice_agent import create_invoice_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Create invoice agent
agent = create_invoice_agent()

# Set up runner
session_service = InMemorySessionService()
runner = Runner(
    agent=agent,
    app_name="invoice_test",
    session_service=session_service
)

# Process a document (in actual usage)
# result = runner.run("Extract data from invoice.pdf")
```

### Project Structure

```
docai-agentic/
├── agent.py                 # Main ADK entry point (root_agent)
├── agents/
│   ├── orchestrator.py     # Main orchestrator agent (ADK)
│   ├── invoice_agent.py    # Invoice extraction (ADK)
│   ├── agreement_agent.py  # Agreement extraction (ADK)
│   ├── kyc_agent.py        # KYC extraction
│   └── relationship_mapper.py
├── tools/
│   ├── mcp_tools.py        # MCP integration
│   ├── pdf_parser.py       # PDF processing
│   ├── ocr_engine.py       # OCR capabilities
│   ├── table_extractor.py  # Table extraction
│   └── mime_handler.py     # MIME type handling
├── schemas/                # JSON schemas for extraction
├── config/                 # Configuration files
├── deployment/            # Deployment scripts
└── .env                   # Environment variables
```

---

## Deployment to Vertex AI Agent Engine

### Prerequisites for Deployment

1. Ensure all APIs are enabled (see Prerequisites section)
2. Verify authentication: `gcloud auth list`
3. Set project: `gcloud config set project YOUR_PROJECT_ID`

### Deploy Using ADK CLI

```bash
export PROJECT_ID=your-project-id
export REGION=us-central1

adk deploy agent_engine \
  --project=$PROJECT_ID \
  --region=$REGION \
  --display_name="DocAI Agentic" \
  agent
```

### What Gets Deployed

The deployment includes:
- Your `agent.py` file with the `root_agent`
- All agent modules (`agents/`)
- Tool implementations (`tools/`)
- Dependencies from `requirements.txt`
- Environment configuration

### Deployment Output

After successful deployment, you'll receive:

```
Deployment successful!
Resource name: projects/123456789/locations/us-central1/reasoningEngines/751619551677906944
Endpoint: https://us-central1-aiplatform.googleapis.com/v1/projects/123456789/locations/us-central1/reasoningEngines/751619551677906944:query
```

### Querying the Deployed Agent

#### Using REST API

```bash
RESOURCE_ID=751619551677906944

curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/reasoningEngines/${RESOURCE_ID}:query" \
  -d '{
    "input": {
      "text": "Extract data from gs://my-bucket/invoice.pdf"
    }
  }'
```

#### Using Python SDK

```python
from google.cloud import aiplatform

aiplatform.init(project=PROJECT_ID, location=REGION)

# Query the agent
response = aiplatform.ReasoningEngine(RESOURCE_ID).query(
    input={"text": "Extract data from invoice.pdf"}
)

print(response)
```

### Scaling Configuration

Agent Engine auto-scales based on load:

```yaml
# Default scaling (managed automatically)
min_replicas: 1
max_replicas: 20
target_concurrent_requests: 5
cpu_utilization_target: 0.7
memory_utilization_target: 0.8
```

---

## Architecture Overview

### Multi-Agent Hierarchy

```
OrchestratorAgent (root_agent)
├── InvoiceAgent (specialized)
├── AgreementAgent (specialized)
├── KYCAgent (specialized)
└── RelationshipMapperAgent (cross-document)
```

### Agent Delegation Flow

1. **User submits document(s)**
2. **OrchestratorAgent** classifies document type
3. **Specialized Agent** extracts structured data
4. **Validation** checks data consistency
5. **Results** returned to user

### MCP Tool Integration

Agents access tools via Model Context Protocol:
- **Filesystem Tools**: Read/write local documents
- **GCS Tools**: Access cloud storage
- **Document Processing Tools**: PDF, OCR, tables
- **Custom Tools**: User-defined extractors

### State Management

ADK handles state automatically:
- Session persistence
- Context sharing between agents
- Tool call history
- Intermediate results

---

## Troubleshooting

### Common Issues

#### 1. Import Errors for `google.adk`

**Error**: `Import "google.adk.agents" could not be resolved`

**Solution**:
```bash
pip install google-adk
# Verify
python -c "import google.adk; print(google.adk.__version__)"
```

#### 2. Authentication Errors

**Error**: `403 Permission denied`

**Solution**:
```bash
gcloud auth application-default login
gcloud auth login
```

#### 3. API Not Enabled

**Error**: `Service aiplatform.googleapis.com is not enabled`

**Solution**:
```bash
gcloud services enable aiplatform.googleapis.com
```

#### 4. MCP Tools Not Working

**Error**: `McpToolset connection failed`

**Solution**:
```bash
# Ensure Node.js is installed
node --version

# Reinstall MCP server
npm install -g @modelcontextprotocol/server-filesystem
```

#### 5. Model Not Found

**Error**: `Model gemini-2.0-flash-exp not found`

**Solution**:
- Use a different model: `gemini-1.5-pro`, `gemini-1.5-flash`
- Check available models in your region

### Logging and Debugging

Enable verbose logging:

```bash
export LOG_LEVEL=DEBUG
adk run agent
```

Check Agent Engine logs:

```bash
gcloud logging read "resource.type=aiplatform.googleapis.com/ReasoningEngine" \
  --limit 50 \
  --format json
```

### Getting Help

- **ADK Documentation**: https://google.github.io/adk-docs/
- **Agent Engine Docs**: https://cloud.google.com/vertex-ai/docs/agent-engine
- **GitHub Issues**: https://github.com/google/adk-python/issues

---

## Next Steps

1. **Test locally** with sample documents
2. **Deploy to Agent Engine** for production use
3. **Monitor performance** with Cloud Monitoring
4. **Extend with custom agents** for your document types
5. **Integrate with your applications** via API

---

## Quick Reference

### Essential Commands

```bash
# Local development
adk run agent                    # CLI mode
adk web --port 8000             # Web UI

# Deployment
adk deploy agent_engine --project=... agent

# Testing
python -m pytest tests/

# Linting
black agents/ tools/
flake8 agents/ tools/
mypy agents/ tools/
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_CLOUD_PROJECT` | Yes | GCP project ID |
| `GOOGLE_API_KEY` | Yes (local) | Gemini API key |
| `GOOGLE_CLOUD_REGION` | No | Default: us-central1 |
| `GEMINI_MODEL` | No | Default: gemini-2.0-flash-exp |
| `GCS_BUCKET` | No | GCS bucket for documents |

---

**Last Updated**: 2026-01-30
**ADK Version**: 1.23.0
**Status**: Ready for deployment
