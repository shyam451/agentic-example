"""
Invoice Agent

Specialized ADK agent for extracting structured data from invoices.
Uses Google ADK LlmAgent with MCP tools for document processing.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from google.adk.agents import LlmAgent
from pathlib import Path
import json

logger = logging.getLogger(__name__)


# Tool functions for invoice processing
def parse_invoice_document(document_path: str) -> Dict[str, Any]:
    """
    Parse invoice document and extract raw text and tables.

    Args:
        document_path: Path to invoice document (PDF, image, etc.)

    Returns:
        Dictionary containing raw text, tables, and metadata
    """
    logger.info(f"Parsing invoice document: {document_path}")

    # TODO: Integrate with actual PDF parser and OCR tools
    # This would call tools/pdf_parser.py and tools/ocr_engine.py

    return {
        "text": "Sample invoice text",
        "tables": [],
        "metadata": {
            "pages": 1,
            "file_size": 0
        }
    }


def validate_invoice_data(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate extracted invoice data for consistency and completeness.

    Args:
        extracted_data: The extracted invoice data

    Returns:
        Validation report with errors and warnings
    """
    validation = {
        'is_valid': True,
        'errors': [],
        'warnings': []
    }

    # Check required fields
    metadata = extracted_data.get('metadata', {})
    if not metadata.get('invoice_number'):
        validation['errors'].append('Missing invoice number')
        validation['is_valid'] = False

    # Check financial consistency
    line_items = extracted_data.get('line_items', [])
    financial = extracted_data.get('financial', {})

    if line_items and financial.get('subtotal'):
        calculated_subtotal = sum(float(item.get('amount', 0)) for item in line_items)
        declared_subtotal = float(financial.get('subtotal', 0))

        if abs(calculated_subtotal - declared_subtotal) > 0.01:
            validation['warnings'].append(
                f'Line items total ({calculated_subtotal}) does not match '
                f'declared subtotal ({declared_subtotal})'
            )

    # Check date logic
    invoice_date = metadata.get('invoice_date')
    due_date = metadata.get('due_date')

    if invoice_date and due_date and due_date < invoice_date:
        validation['errors'].append('Due date is before invoice date')
        validation['is_valid'] = False

    logger.info(f"Validation complete: {validation}")
    return validation


def load_invoice_schema(schema_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load the invoice JSON schema.

    Args:
        schema_path: Optional custom schema path

    Returns:
        Invoice schema dictionary
    """
    if not schema_path:
        schema_path = "schemas/invoice.json"

    try:
        with open(schema_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Schema not found at {schema_path}, using default")
        return {}


def create_invoice_agent(
    model: str = "gemini-2.0-flash-exp",
    schema_path: Optional[str] = None,
    custom_prompts: Optional[List[str]] = None
) -> LlmAgent:
    """
    Create an ADK LlmAgent specialized for invoice extraction.

    Args:
        model: The Gemini model to use
        schema_path: Path to invoice JSON schema
        custom_prompts: Optional additional extraction instructions

    Returns:
        Configured LlmAgent for invoice extraction
    """

    # Load schema for structured output
    schema = load_invoice_schema(schema_path)

    # Build instruction with custom prompts
    base_instruction = """You are an expert invoice extraction agent. Your task is to:

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
5. Extract ALL line items completely, even if there are many

When processing:
- First, use parse_invoice_document to extract raw text and tables
- Then, analyze the content to populate the invoice schema
- Finally, use validate_invoice_data to check consistency
- Return results in valid JSON format matching the invoice schema

Document path will be in session state as {document_path}
"""

    if custom_prompts:
        base_instruction += "\n\nAdditional extraction requirements:\n"
        for i, prompt in enumerate(custom_prompts, 1):
            base_instruction += f"{i}. {prompt}\n"

    # Create the ADK agent
    agent = LlmAgent(
        model=model,
        name="InvoiceAgent",
        description="Specialized agent for extracting structured data from invoices",
        instruction=base_instruction,
        tools=[
            parse_invoice_document,
            validate_invoice_data
        ],
        output_key="invoice_extraction_result"
    )

    logger.info(f"Invoice agent created with model: {model}")
    return agent


# For backward compatibility with existing code
class InvoiceAgent:
    """
    Wrapper class for ADK invoice agent to maintain backward compatibility.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize invoice agent with ADK backend.

        Args:
            config: Agent configuration including schema path and model settings
        """
        self.config = config
        self.schema_path = config.get('schema_path')
        self.model = config.get('model', 'gemini-2.0-flash-exp')

        # Create the underlying ADK agent
        self.adk_agent = create_invoice_agent(
            model=self.model,
            schema_path=self.schema_path
        )

        logger.info("Invoice agent initialized with ADK backend")

    async def extract(
        self,
        document_path: str,
        custom_prompts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from invoice using ADK agent.

        Args:
            document_path: Path to invoice document
            custom_prompts: Optional additional extraction instructions

        Returns:
            Structured invoice data matching schema
        """
        logger.info(f"Extracting invoice data from: {document_path}")

        # If custom prompts provided, recreate agent with them
        if custom_prompts:
            self.adk_agent = create_invoice_agent(
                model=self.model,
                schema_path=self.schema_path,
                custom_prompts=custom_prompts
            )

        # For now, return placeholder structure
        # Full ADK integration requires Runner and session setup
        # which will be done in the orchestrator

        result = {
            'document_type': 'invoice',
            'document_path': document_path,
            'metadata': {
                'invoice_number': None,
                'invoice_date': None,
                'due_date': None,
                'confidence': 0.0
            },
            'vendor': {
                'name': None,
                'address': None,
                'tax_id': None,
                'contact': None
            },
            'customer': {
                'name': None,
                'address': None,
                'tax_id': None
            },
            'line_items': [],
            'financial': {
                'subtotal': None,
                'tax': None,
                'total_amount': None,
                'currency': None
            },
            'custom_extractions': {},
            'extraction_timestamp': datetime.now().isoformat(),
            '_adk_agent': 'InvoiceAgent'
        }

        return result

    def validate_extraction(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted data for consistency.

        Args:
            result: Extraction result

        Returns:
            Validation report
        """
        return validate_invoice_data(result)
