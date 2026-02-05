"""
DocAI Agentic - Main ADK Agent Entry Point

This is the main entry point for ADK deployment to Vertex AI Agent Engine.
The `root_agent` variable is required by ADK for deployment.

Features:
- Built-in agents: InvoiceAgent, AgreementAgent, KYCAgent
- Custom agent builder: Define agents via YAML configuration
- Classification-first routing: Deterministic document type → agent routing
- Agent extensions: Extend built-in agents with custom prompts

Usage:
    # From project root:
    adk web agents --port 8000

    # Or run directly:
    adk run agents
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

# Load .env file explicitly
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv(Path(__file__).parent.parent / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import ADK components
from google.adk.agents import LlmAgent

# Import builder components
try:
    from agents.builder import (
        AgentFactory,
        AgentRouter,
        ConfigValidator,
        SchemaRegistry,
        ToolRegistry,
        PipelineBuilder,
        classify_document
    )
    from agents.builder.agent_router import create_default_router
    BUILDER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Builder module not available: {e}")
    BUILDER_AVAILABLE = False

# Configuration
MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
CUSTOM_AGENTS_CONFIG = os.getenv('CUSTOM_AGENTS_CONFIG', 'config/custom_agents.yaml')


# ============== Inline Agent Definitions ==============
# These are defined inline to avoid import issues with ADK loader

def create_invoice_agent(model: str = MODEL) -> LlmAgent:
    """Create Invoice extraction agent."""

    instruction = """You are an expert invoice extraction agent. Your task is to:

1. Extract structured data from invoice documents accurately
2. Identify and extract the following key information:
   - Invoice metadata (number, date, due date, PO number)
   - Vendor information (name, address, tax ID, contact)
   - Customer information (name, address, tax ID)
   - Line items (description, quantity, unit price, amount)
   - Financial totals (subtotal, tax, total amount, currency)
   - Payment terms and bank details

3. For each field, provide a confidence score (0.0 to 1.0)
4. Ensure data consistency (line items sum to subtotal, dates are logical)
5. Extract ALL line items completely

Return results in valid JSON format.
"""

    return LlmAgent(
        model=model,
        name="InvoiceAgent",
        description="Specialized agent for extracting structured data from invoices",
        instruction=instruction,
        output_key="invoice_result"
    )


def create_agreement_agent(model: str = MODEL) -> LlmAgent:
    """Create Agreement/Contract extraction agent."""

    instruction = """You are an expert legal agreement extraction agent. Your task is to:

1. Extract structured data from contracts and agreements accurately
2. Identify and extract the following key information:
   - Agreement metadata (type, effective date, expiry date)
   - All parties involved (role, name, address, representative)
   - Key terms (scope, payment terms, termination conditions, governing law)
   - Obligations for each party with deadlines
   - Liability and indemnity clauses
   - Renewal terms and auto-renewal provisions
   - Signatures and signing dates

3. For complex agreements:
   - Identify penalty clauses with amounts and conditions
   - Extract termination conditions and notice periods
   - Detect confidentiality and non-compete clauses

4. Provide confidence scores for all extracted fields
5. Preserve exact wording for critical legal terms

Return results in valid JSON format.
"""

    return LlmAgent(
        model=model,
        name="AgreementAgent",
        description="Specialized agent for extracting structured data from contracts and agreements",
        instruction=instruction,
        output_key="agreement_result"
    )


def create_kyc_agent(model: str = MODEL) -> LlmAgent:
    """Create KYC document extraction agent."""

    instruction = """You are an expert KYC (Know Your Customer) document extraction agent.

Extract structured information from identity documents including:
- Passports
- Driver's licenses
- National ID cards
- Residence permits

Extract:
1. Personal information (name, DOB, nationality, gender)
2. Document metadata (type, number, issue/expiry dates)
3. Address information
4. Verification data (MRZ, photos, security features)
5. Issuing authority

Provide confidence scores for all extracted fields.

Return results in valid JSON format.
"""

    return LlmAgent(
        model=model,
        name="KYCAgent",
        description="Specialized agent for extracting data from identity documents",
        instruction=instruction,
        output_key="kyc_result"
    )


def create_orchestrator_agent(
    invoice_agent: LlmAgent,
    agreement_agent: LlmAgent,
    kyc_agent: LlmAgent,
    model: str = MODEL
) -> LlmAgent:
    """Create the main orchestrator agent with sub-agents."""

    instruction = """You are the main orchestrator agent for document extraction. Your responsibilities:

1. CLASSIFY documents to determine their type:
   - invoice: Invoices, bills, receipts
   - agreement: Contracts, agreements, legal documents
   - kyc: Identity documents (passports, licenses, ID cards)

2. DELEGATE extraction to the appropriate specialized agent based on classification

3. When the user provides a document or describes a document:
   - First determine what type of document it is
   - Then delegate to the appropriate sub-agent (InvoiceAgent, AgreementAgent, or KYCAgent)
   - Return the structured extraction results

4. For questions about documents, analyze and respond appropriately

5. If unsure about document type, ask clarifying questions

You have access to these specialized agents:
- InvoiceAgent: For invoices, receipts, bills
- AgreementAgent: For contracts, agreements, legal documents
- KYCAgent: For identity documents (passports, licenses, ID cards)

Always return results in a structured JSON format with confidence scores.
"""

    return LlmAgent(
        model=model,
        name="DocAI_Orchestrator",
        description="Main coordinator for document extraction - classifies and delegates to specialized agents",
        instruction=instruction,
        sub_agents=[invoice_agent, agreement_agent, kyc_agent],
        output_key="extraction_result"
    )


# ============== Custom Agent Loading ==============

def load_custom_agents(config_path: str) -> Dict[str, LlmAgent]:
    """
    Load custom agents from YAML configuration.

    Args:
        config_path: Path to custom agents YAML file

    Returns:
        Dict mapping agent names to LlmAgent instances
    """
    if not BUILDER_AVAILABLE:
        logger.warning("Builder module not available, skipping custom agents")
        return {}

    config_file = Path(config_path)
    if not config_file.exists():
        # Try relative to project root
        project_root = Path(__file__).parent.parent
        config_file = project_root / config_path

    if not config_file.exists():
        logger.info(f"Custom agents config not found: {config_path}")
        return {}

    try:
        factory = AgentFactory()
        agents = factory.create_from_yaml(str(config_file))
        logger.info(f"Loaded {len(agents)} custom agents from {config_path}")
        return agents
    except Exception as e:
        logger.error(f"Failed to load custom agents: {e}")
        return {}


def create_routing_orchestrator(
    invoice_agent: LlmAgent,
    agreement_agent: LlmAgent,
    kyc_agent: LlmAgent,
    custom_agents: Optional[Dict[str, LlmAgent]] = None,
    model: str = MODEL
) -> LlmAgent:
    """
    Create orchestrator with classification-first routing.

    The orchestrator uses the classify_document tool to determine document type,
    then routes to the appropriate specialized agent.

    Args:
        invoice_agent: Agent for invoice documents
        agreement_agent: Agent for agreement documents
        kyc_agent: Agent for KYC documents
        custom_agents: Optional dict of custom agents
        model: Model to use for orchestrator

    Returns:
        Configured orchestrator LlmAgent
    """
    # Build list of all agents
    all_agents = [invoice_agent, agreement_agent, kyc_agent]

    # Add custom agents
    if custom_agents:
        all_agents.extend(custom_agents.values())

    # Build agent list for instruction
    agent_descriptions = []
    for agent in all_agents:
        agent_descriptions.append(f"- {agent.name}: {agent.description}")

    agents_list = "\n".join(agent_descriptions)

    # Build instruction with classification-first routing
    instruction = f"""You are the main orchestrator agent for document extraction.

Your workflow:
1. CLASSIFY the document to determine its type using the classify_document tool
2. ROUTE to the appropriate specialized agent based on classification
3. RETURN the extraction results

Available specialized agents:
{agents_list}

Document Type → Agent Routing:
- invoice, bill, receipt, purchase_order → InvoiceAgent
- agreement, contract, nda, msa, sow, lease → AgreementAgent
- kyc, passport, drivers_license, id_card → KYCAgent
"""

    # Add custom agent routing if available
    if custom_agents:
        instruction += "\nCustom agents:\n"
        for name, agent in custom_agents.items():
            instruction += f"- {name}: {agent.description}\n"

    instruction += """
When processing a document:
1. First call classify_document(document_path) to get the document type
2. Based on the classification result, delegate to the matching agent
3. Return the structured extraction results with confidence scores

If the document type is unclear, ask clarifying questions.
Always return results in a structured JSON format.
"""

    # Create tools list
    tools = []
    if BUILDER_AVAILABLE:
        tools.append(classify_document)

    return LlmAgent(
        model=model,
        name="DocAI_Orchestrator",
        description="Main coordinator with classification-first routing to specialized agents",
        instruction=instruction,
        sub_agents=all_agents,
        tools=tools if tools else None,
        output_key="extraction_result"
    )


# ============== Create Root Agent ==============

logger.info("Initializing DocAI Agentic system...")

# Create built-in specialized agents
invoice_agent = create_invoice_agent(model=MODEL)
agreement_agent = create_agreement_agent(model=MODEL)
kyc_agent = create_kyc_agent(model=MODEL)

# Load custom agents from configuration
custom_agents = load_custom_agents(CUSTOM_AGENTS_CONFIG)

# Create agent router for classification-first routing
agent_router = None
if BUILDER_AVAILABLE:
    agent_router = create_default_router(invoice_agent, agreement_agent, kyc_agent)

    # Register custom agents with router
    for name, agent in custom_agents.items():
        # Extract document type from agent's output_key
        # e.g., "receipt_result" → "receipt"
        if hasattr(agent, 'output_key') and agent.output_key:
            doc_type = agent.output_key.replace('_result', '')
            agent_router.register([doc_type], agent)

    logger.info(f"Agent router configured with routes: {agent_router.list_routes()}")

# Create orchestrator with classification-first routing
root_agent = create_routing_orchestrator(
    invoice_agent=invoice_agent,
    agreement_agent=agreement_agent,
    kyc_agent=kyc_agent,
    custom_agents=custom_agents,
    model=MODEL
)

logger.info(f"Root agent created: {root_agent.name}")
logger.info(f"Model: {MODEL}")
logger.info(f"Built-in agents: InvoiceAgent, AgreementAgent, KYCAgent")
if custom_agents:
    logger.info(f"Custom agents: {list(custom_agents.keys())}")
logger.info(f"Total sub-agents: {len(root_agent.sub_agents)}")


# ============== Exports ==============
# Export router and factory for programmatic use

__all__ = [
    'root_agent',
    'agent_router',
    'invoice_agent',
    'agreement_agent',
    'kyc_agent',
    'custom_agents',
    'load_custom_agents',
    'create_invoice_agent',
    'create_agreement_agent',
    'create_kyc_agent',
    'create_orchestrator_agent',
    'create_routing_orchestrator',
]
