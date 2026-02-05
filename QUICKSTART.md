# DocAI Agentic - Quick Start

Get up and running with DocAI Agentic in 5 minutes!

## Prerequisites

- Python 3.10+
- Google Cloud account
- Node.js 18+ (for MCP tools)

## Setup

### 1. Install Dependencies

```bash
cd /Users/shyamnair/code/docai-agentic

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install packages
pip install -r deployment/requirements.txt
python -m spacy download en_core_web_sm

# Install MCP filesystem server
npm install -g @modelcontextprotocol/server-filesystem
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your settings
nano .env
```

Required settings:
```env
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_API_KEY=your-gemini-api-key
```

Get your API key: https://makersuite.google.com/app/apikey

### 3. Authenticate

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

## Run Locally

### Option 1: CLI Mode

```bash
adk run agent
```

Try:
```
You: Extract data from documents/sample_invoice.pdf
```

### Option 2: Web UI (Recommended)

```bash
adk web --port 8000
```

Open browser: http://localhost:8000

## Test Extraction

### Create a test document

```bash
mkdir -p documents
# Place your PDF invoice in documents/invoice.pdf
```

### Extract data

```
You: Extract structured data from documents/invoice.pdf

Agent: I'll process that invoice document for you.
       Let me classify it first...

       [Agent processes document]

       Here's the extracted data:
       - Invoice Number: INV-001
       - Date: 2024-01-15
       - Vendor: Acme Corp
       - Total: $1,234.56
       ...
```

## Deploy to Production

### 1. Enable APIs

```bash
gcloud services enable aiplatform.googleapis.com
```

### 2. Deploy

```bash
export PROJECT_ID=your-project-id

adk deploy agent_engine \
  --project=$PROJECT_ID \
  --region=us-central1 \
  --display_name="DocAI Agent" \
  agent
```

### 3. Use Deployed Agent

```bash
# Get resource ID from deployment output
RESOURCE_ID=your-reasoning-engine-id

# Query via REST API
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://us-central1-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/us-central1/reasoningEngines/${RESOURCE_ID}:query" \
  -d '{"input": {"text": "Extract from invoice.pdf"}}'
```

## Example Usage

### Single Document

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from agent import root_agent

# Setup
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name="docai",
    session_service=session_service
)

# Extract from document
response = runner.run("Extract data from invoice.pdf")
print(response)
```

### Batch Processing

```python
response = runner.run("""
Process all documents in the documents/ folder:
- Extract structured data from each
- Detect relationships between documents
- Generate summary report
""")
```

### Custom Prompts

```python
response = runner.run("""
Extract data from contract.pdf with these additional fields:
- Identify all penalty clauses
- Extract renewal terms
- List all obligations with deadlines
""")
```

## Common Tasks

### Add New Document Type

1. Create specialized agent:

```python
# agents/purchase_order_agent.py
from google.adk.agents import LlmAgent

def create_po_agent(model="gemini-2.0-flash-exp"):
    return LlmAgent(
        model=model,
        name="PurchaseOrderAgent",
        description="Extract data from purchase orders",
        instruction="Extract PO number, items, amounts...",
        tools=[parse_document, validate_po]
    )
```

2. Register in orchestrator:

```python
# agent.py
from agents.purchase_order_agent import create_po_agent

po_agent = create_po_agent()
orchestrator = create_orchestrator_agent(
    invoice_agent=invoice_agent,
    agreement_agent=agreement_agent,
    kyc_agent=kyc_agent,
    po_agent=po_agent  # Add new agent
)
```

### Customize Extraction

Edit agent instructions in respective files:
- [agents/invoice_agent.py](agents/invoice_agent.py) - Invoice extraction
- [agents/agreement_agent.py](agents/agreement_agent.py) - Agreement extraction
- [agent.py](agent.py) - Overall orchestration

### Add Custom Tools

```python
# tools/custom_validator.py
def validate_tax_id(tax_id: str) -> dict:
    """Validate tax ID format."""
    # Your validation logic
    return {"valid": True, "formatted": tax_id}

# Add to agent
from tools.custom_validator import validate_tax_id

agent = LlmAgent(
    name="InvoiceAgent",
    tools=[parse_document, validate_tax_id]  # Add custom tool
)
```

## Troubleshooting

### Issue: Import errors

```bash
pip install google-adk
```

### Issue: Authentication failed

```bash
gcloud auth application-default login
```

### Issue: API not enabled

```bash
gcloud services enable aiplatform.googleapis.com
```

### Issue: MCP tools not found

```bash
npm install -g @modelcontextprotocol/server-filesystem
```

## Next Steps

- 📖 Read [ADK_SETUP.md](ADK_SETUP.md) for complete guide
- 🏗️ Review [ARCHITECTURE_PLAN.md](ARCHITECTURE_PLAN.md) for system design
- 🔄 Check [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md) for what changed
- 📝 Customize agents for your document types

## Support

- **Documentation**: [ADK_SETUP.md](ADK_SETUP.md)
- **Google ADK**: https://google.github.io/adk-docs/
- **Issues**: Create GitHub issue

---

**Ready to extract!** 🚀
