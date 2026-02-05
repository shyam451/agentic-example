"""
Agreement Agent

Specialized ADK agent for extracting structured data from contracts and agreements.
Uses Google ADK LlmAgent with MCP tools for document processing.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from google.adk.agents import LlmAgent
import json

logger = logging.getLogger(__name__)


# Tool functions for agreement processing
def parse_agreement_document(document_path: str) -> Dict[str, Any]:
    """
    Parse agreement document and extract raw text.

    Args:
        document_path: Path to agreement document (PDF, DOCX, etc.)

    Returns:
        Dictionary containing raw text and metadata
    """
    logger.info(f"Parsing agreement document: {document_path}")

    # TODO: Integrate with actual PDF parser and DOCX tools
    return {
        "text": "Sample agreement text",
        "metadata": {
            "pages": 10,
            "file_size": 0
        }
    }


def extract_clauses(document_text: str, clause_types: List[str]) -> List[Dict[str, Any]]:
    """
    Extract specific types of clauses from agreement text.

    Args:
        document_text: Full text of the agreement
        clause_types: Types of clauses to extract (e.g., "termination", "liability", "renewal")

    Returns:
        List of extracted clauses with content and location
    """
    logger.info(f"Extracting clauses: {clause_types}")

    # TODO: Implement NLP-based clause extraction
    return []


def validate_agreement_data(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate extracted agreement data for completeness.

    Args:
        extracted_data: The extracted agreement data

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
    if not metadata.get('agreement_type'):
        validation['warnings'].append('Agreement type not identified')

    # Check parties
    parties = extracted_data.get('parties', [])
    if len(parties) < 2:
        validation['errors'].append('Less than 2 parties identified')
        validation['is_valid'] = False

    # Check dates
    effective_date = metadata.get('effective_date')
    expiry_date = metadata.get('expiry_date')

    if effective_date and expiry_date and expiry_date < effective_date:
        validation['errors'].append('Expiry date is before effective date')
        validation['is_valid'] = False

    logger.info(f"Validation complete: {validation}")
    return validation


def create_agreement_agent(
    model: str = "gemini-2.0-flash-exp",
    schema_path: Optional[str] = None,
    custom_prompts: Optional[List[str]] = None,
    extract_clauses_flag: bool = True
) -> LlmAgent:
    """
    Create an ADK LlmAgent specialized for agreement extraction.

    Args:
        model: The Gemini model to use
        schema_path: Path to agreement JSON schema
        custom_prompts: Optional additional extraction instructions
        extract_clauses_flag: Whether to extract penalty/renewal clauses

    Returns:
        Configured LlmAgent for agreement extraction
    """

    # Build instruction
    base_instruction = """You are an expert legal agreement extraction agent. Your task is to:

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
   - Note any special conditions or addendums

4. Provide confidence scores for all extracted fields
5. Preserve exact wording for critical legal terms

When processing:
- First, use parse_agreement_document to extract raw text
- Then, analyze the content to populate the agreement schema
- Use extract_clauses to identify specific clause types
- Finally, use validate_agreement_data to check completeness
- Return results in valid JSON format matching the agreement schema

Document path will be in session state as {document_path}
"""

    if custom_prompts:
        base_instruction += "\n\nAdditional extraction requirements:\n"
        for i, prompt in enumerate(custom_prompts, 1):
            base_instruction += f"{i}. {prompt}\n"

    # Select tools based on configuration
    tools = [
        parse_agreement_document,
        validate_agreement_data
    ]

    if extract_clauses_flag:
        tools.append(extract_clauses)

    # Create the ADK agent
    agent = LlmAgent(
        model=model,
        name="AgreementAgent",
        description="Specialized agent for extracting structured data from contracts and agreements",
        instruction=base_instruction,
        tools=tools,
        output_key="agreement_extraction_result"
    )

    logger.info(f"Agreement agent created with model: {model}")
    return agent


# For backward compatibility with existing code
class AgreementAgent:
    """
    Wrapper class for ADK agreement agent to maintain backward compatibility.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize agreement agent with ADK backend.

        Args:
            config: Agent configuration including schema path and model settings
        """
        self.config = config
        self.schema_path = config.get('schema_path')
        self.model = config.get('model', 'gemini-2.0-flash-exp')
        self.extract_clauses = config.get('extract_clauses', True)

        # Create the underlying ADK agent
        self.adk_agent = create_agreement_agent(
            model=self.model,
            schema_path=self.schema_path,
            extract_clauses_flag=self.extract_clauses
        )

        logger.info("Agreement agent initialized with ADK backend")

    async def extract(
        self,
        document_path: str,
        custom_prompts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from agreement using ADK agent.

        Args:
            document_path: Path to agreement document
            custom_prompts: Optional additional extraction instructions

        Returns:
            Structured agreement data matching schema
        """
        logger.info(f"Extracting agreement data from: {document_path}")

        # If custom prompts provided, recreate agent with them
        if custom_prompts:
            self.adk_agent = create_agreement_agent(
                model=self.model,
                schema_path=self.schema_path,
                custom_prompts=custom_prompts,
                extract_clauses_flag=self.extract_clauses
            )

        # Placeholder structure - full ADK integration in orchestrator
        result = {
            'document_type': 'agreement',
            'document_path': document_path,
            'metadata': {
                'agreement_type': None,  # NDA, MSA, SOW, etc.
                'effective_date': None,
                'expiry_date': None,
                'confidence': 0.0
            },
            'parties': [],
            'key_terms': {
                'scope': None,
                'payment_terms': None,
                'termination_clause': None,
                'liability_cap': None,
                'governing_law': None
            },
            'obligations': [],
            'signatures': [],
            'clauses': {} if self.extract_clauses else None,
            'custom_extractions': {},
            'extraction_timestamp': datetime.now().isoformat(),
            '_adk_agent': 'AgreementAgent'
        }

        return result

    def extract_penalty_clauses(self, document_text: str) -> List[Dict[str, Any]]:
        """
        Extract penalty clauses from agreement text.

        Args:
            document_text: Full text of agreement

        Returns:
            List of penalty clauses with details
        """
        return extract_clauses(document_text, ["penalty", "liquidated_damages"])

    def extract_renewal_terms(self, document_text: str) -> Dict[str, Any]:
        """
        Extract renewal and auto-renewal terms.

        Args:
            document_text: Full text of agreement

        Returns:
            Renewal terms details
        """
        renewal_clauses = extract_clauses(document_text, ["renewal", "auto-renewal"])

        # TODO: Parse renewal clauses into structured format
        return {
            'has_renewal': len(renewal_clauses) > 0,
            'auto_renewal': False,
            'renewal_notice_period': None
        }
