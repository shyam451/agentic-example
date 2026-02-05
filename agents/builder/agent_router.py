"""
Agent Router

Classification-first routing to specialized agents.
"""

import logging
import mimetypes
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from google.adk.agents import LlmAgent

logger = logging.getLogger(__name__)


# Document type classifications
DOCUMENT_TYPES = {
    # Container types (handled by preprocessor)
    'container': ['archive', 'email', 'pdf_portfolio'],

    # Extraction types (routed to agents)
    'invoice': ['invoice', 'bill', 'receipt', 'purchase_order'],
    'agreement': ['agreement', 'contract', 'nda', 'msa', 'sow', 'mou', 'lease'],
    'kyc': ['passport', 'drivers_license', 'id_card', 'residence_permit', 'visa'],

    # Generic
    'document': ['document', 'form', 'letter', 'report']
}

# File extension to document type mapping
EXTENSION_TYPE_MAP = {
    # Container types
    '.zip': 'archive',
    '.rar': 'archive',
    '.tar': 'archive',
    '.7z': 'archive',
    '.gz': 'archive',
    '.eml': 'email',
    '.msg': 'email',

    # Document types (require content analysis for specific classification)
    '.pdf': None,  # Needs content analysis
    '.docx': None,
    '.doc': None,
    '.png': None,
    '.jpg': None,
    '.jpeg': None,
    '.tiff': None,
    '.bmp': None,
}


def classify_document(
    document_path: str,
    content_hint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Classify document type for routing.

    This is a tool function that can be used by the orchestrator.

    Args:
        document_path: Path to document file
        content_hint: Optional hint about document content

    Returns:
        Classification result with type, confidence, and features
    """
    path = Path(document_path)
    extension = path.suffix.lower()

    # Check extension-based classification first
    if extension in EXTENSION_TYPE_MAP:
        ext_type = EXTENSION_TYPE_MAP[extension]
        if ext_type:
            return {
                'type': ext_type,
                'confidence': 1.0,
                'method': 'extension',
                'features': [f'extension:{extension}']
            }

    # For documents that need content analysis, use heuristics
    # In production, this would use lightweight LLM or ML classifier
    classification = _analyze_content(document_path, content_hint)

    return classification


def _analyze_content(
    document_path: str,
    content_hint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze document content to determine type.

    Uses filename patterns and content hints for classification.
    In production, could use ML classifier or lightweight LLM.
    """
    path = Path(document_path)
    filename = path.stem.lower()

    # Filename-based heuristics
    invoice_keywords = ['invoice', 'inv', 'bill', 'receipt', 'payment']
    agreement_keywords = ['agreement', 'contract', 'nda', 'msa', 'sow', 'lease', 'terms']
    kyc_keywords = ['passport', 'license', 'id', 'identity', 'permit', 'visa']

    features = []

    # Check filename
    for kw in invoice_keywords:
        if kw in filename:
            features.append(f'filename:{kw}')
            return {
                'type': 'invoice',
                'confidence': 0.8,
                'method': 'filename',
                'features': features
            }

    for kw in agreement_keywords:
        if kw in filename:
            features.append(f'filename:{kw}')
            return {
                'type': 'agreement',
                'confidence': 0.8,
                'method': 'filename',
                'features': features
            }

    for kw in kyc_keywords:
        if kw in filename:
            features.append(f'filename:{kw}')
            return {
                'type': 'kyc',
                'confidence': 0.8,
                'method': 'filename',
                'features': features
            }

    # Check content hint
    if content_hint:
        hint_lower = content_hint.lower()
        for kw in invoice_keywords:
            if kw in hint_lower:
                return {
                    'type': 'invoice',
                    'confidence': 0.7,
                    'method': 'content_hint',
                    'features': [f'hint:{kw}']
                }
        for kw in agreement_keywords:
            if kw in hint_lower:
                return {
                    'type': 'agreement',
                    'confidence': 0.7,
                    'method': 'content_hint',
                    'features': [f'hint:{kw}']
                }
        for kw in kyc_keywords:
            if kw in hint_lower:
                return {
                    'type': 'kyc',
                    'confidence': 0.7,
                    'method': 'content_hint',
                    'features': [f'hint:{kw}']
                }

    # Default to generic document
    return {
        'type': 'document',
        'confidence': 0.5,
        'method': 'default',
        'features': []
    }


class AgentRouter:
    """
    Routes documents to specialized agents based on classification.

    Supports:
    - Built-in agent registration (invoice, agreement, kyc)
    - Custom agent registration
    - Classification-first routing

    Usage:
        router = AgentRouter()

        # Register built-in agents
        router.register(['invoice', 'bill', 'receipt'], invoice_agent)
        router.register(['agreement', 'contract'], agreement_agent)

        # Route a document
        classification = classify_document(document_path)
        agent = router.route(classification)
    """

    def __init__(self):
        """Initialize router with empty routes."""
        self._routes: Dict[str, LlmAgent] = {}
        self._type_aliases: Dict[str, str] = {}

    def register(
        self,
        document_types: List[str],
        agent: LlmAgent
    ) -> None:
        """
        Register an agent for document types.

        Args:
            document_types: List of document types this agent handles
            agent: The LlmAgent to route to
        """
        for doc_type in document_types:
            self._routes[doc_type] = agent
            logger.debug(f"Registered route: {doc_type} → {agent.name}")

        logger.info(f"Registered {agent.name} for types: {document_types}")

    def register_alias(self, alias: str, target_type: str) -> None:
        """
        Register a type alias.

        Args:
            alias: Alias document type
            target_type: Target type to route to
        """
        self._type_aliases[alias] = target_type
        logger.debug(f"Registered alias: {alias} → {target_type}")

    def route(
        self,
        classification: Dict[str, Any]
    ) -> Optional[LlmAgent]:
        """
        Route to agent based on classification.

        Args:
            classification: Result from classify_document()

        Returns:
            LlmAgent for handling this document type, or None if no match
        """
        doc_type = classification.get('type', 'document')

        # Check aliases first
        if doc_type in self._type_aliases:
            doc_type = self._type_aliases[doc_type]

        # Get agent for type
        agent = self._routes.get(doc_type)

        if agent:
            logger.info(f"Routed document type '{doc_type}' to {agent.name}")
        else:
            logger.warning(f"No agent registered for document type: {doc_type}")

        return agent

    def route_document(
        self,
        document_path: str,
        content_hint: Optional[str] = None
    ) -> Tuple[Optional[LlmAgent], Dict[str, Any]]:
        """
        Classify and route a document in one step.

        Args:
            document_path: Path to document
            content_hint: Optional content hint

        Returns:
            Tuple of (agent, classification)
        """
        classification = classify_document(document_path, content_hint)
        agent = self.route(classification)

        return agent, classification

    def get_agent_for_type(self, doc_type: str) -> Optional[LlmAgent]:
        """Get agent registered for a specific document type."""
        if doc_type in self._type_aliases:
            doc_type = self._type_aliases[doc_type]
        return self._routes.get(doc_type)

    def list_routes(self) -> Dict[str, str]:
        """
        List all registered routes.

        Returns:
            Dict mapping document types to agent names
        """
        return {
            doc_type: agent.name
            for doc_type, agent in self._routes.items()
        }

    def list_types(self) -> List[str]:
        """List all registered document types."""
        return sorted(self._routes.keys())

    def has_route(self, doc_type: str) -> bool:
        """Check if a route exists for document type."""
        if doc_type in self._type_aliases:
            doc_type = self._type_aliases[doc_type]
        return doc_type in self._routes

    def unregister(self, doc_type: str) -> None:
        """Unregister a document type route."""
        if doc_type in self._routes:
            del self._routes[doc_type]
            logger.debug(f"Unregistered route: {doc_type}")

    def clear(self) -> None:
        """Clear all routes."""
        self._routes.clear()
        self._type_aliases.clear()


def create_default_router(
    invoice_agent: LlmAgent,
    agreement_agent: LlmAgent,
    kyc_agent: LlmAgent
) -> AgentRouter:
    """
    Create router with default built-in agent routes.

    Args:
        invoice_agent: Agent for invoice documents
        agreement_agent: Agent for agreement documents
        kyc_agent: Agent for KYC documents

    Returns:
        Configured AgentRouter
    """
    router = AgentRouter()

    # Register built-in agents
    router.register(
        ['invoice', 'bill', 'receipt', 'purchase_order'],
        invoice_agent
    )

    router.register(
        ['agreement', 'contract', 'nda', 'msa', 'sow', 'mou', 'lease'],
        agreement_agent
    )

    router.register(
        ['kyc', 'passport', 'drivers_license', 'id_card', 'residence_permit', 'visa'],
        kyc_agent
    )

    # Register common aliases
    router.register_alias('po', 'purchase_order')
    router.register_alias('license', 'drivers_license')
    router.register_alias('id', 'id_card')

    return router
