"""
Agent Router

Classification-first routing to specialized agents.
Uses LLM-based document classification for intelligent routing.
"""

import logging
import mimetypes
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from google.adk.agents import LlmAgent

# Import for LLM-based classification
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# Import for document content extraction
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

logger = logging.getLogger(__name__)

# Configure Gemini for classification
CLASSIFICATION_MODEL = os.getenv('CLASSIFICATION_MODEL', 'gemini-2.0-flash')


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


def _extract_document_content(document_path: str, max_chars: int = 3000) -> Optional[str]:
    """
    Extract text content from document for classification.

    Args:
        document_path: Path to document
        max_chars: Maximum characters to extract

    Returns:
        Extracted text content or None if extraction fails
    """
    path = Path(document_path)
    extension = path.suffix.lower()

    try:
        if extension == '.pdf' and PYMUPDF_AVAILABLE:
            # Extract text from first few pages of PDF
            doc = fitz.open(document_path)
            text_parts = []
            for page_num in range(min(3, len(doc))):  # First 3 pages
                page = doc[page_num]
                text_parts.append(page.get_text())
            doc.close()
            text = "\n".join(text_parts)
            return text[:max_chars] if text else None

        elif extension in ['.txt', '.md', '.csv']:
            with open(document_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read(max_chars)

        elif extension in ['.docx'] and PYMUPDF_AVAILABLE:
            # PyMuPDF can also handle DOCX
            doc = fitz.open(document_path)
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()
            text = "\n".join(text_parts)
            return text[:max_chars] if text else None

    except Exception as e:
        logger.warning(f"Failed to extract content from {document_path}: {e}")

    return None


def _classify_with_llm(
    document_path: str,
    content: Optional[str],
    registered_types: List[str],
    content_hint: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Use LLM to classify document type.

    Args:
        document_path: Path to document
        content: Extracted text content
        registered_types: List of registered document types to choose from
        content_hint: Optional hint about document content

    Returns:
        Classification result or None if LLM classification fails
    """
    if not GENAI_AVAILABLE:
        logger.debug("google.generativeai not available, skipping LLM classification")
        return None

    # Check for API key
    api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.debug("No Gemini API key found, skipping LLM classification")
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(CLASSIFICATION_MODEL)

        # Build classification prompt
        filename = Path(document_path).name
        types_list = ", ".join(registered_types) if registered_types else "invoice, agreement, kyc, receipt, document"

        prompt = f"""Analyze this document and classify its type.

Document filename: {filename}
{f'Content hint: {content_hint}' if content_hint else ''}

Document content (first portion):
---
{content if content else '[No text content extracted - may be an image or scanned document]'}
---

Available document types: {types_list}

Based on the document content and context, determine:
1. The document type (must be one from the available types, or 'document' if none match)
2. Your confidence level (0.0 to 1.0)
3. Key features that led to this classification

Respond in this exact JSON format:
{{"type": "<document_type>", "confidence": <0.0-1.0>, "features": ["feature1", "feature2"]}}

Only respond with the JSON, no other text."""

        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Parse JSON response
        import json
        # Handle potential markdown code blocks
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        response_text = response_text.strip()

        result = json.loads(response_text)
        result['method'] = 'llm'
        result['model'] = CLASSIFICATION_MODEL

        logger.info(f"LLM classified '{filename}' as '{result['type']}' with confidence {result['confidence']}")
        return result

    except Exception as e:
        logger.warning(f"LLM classification failed: {e}")
        return None


def _analyze_content_fallback(
    document_path: str,
    content_hint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fallback keyword-based classification when LLM is unavailable.

    Uses filename patterns and content hints for classification.
    """
    path = Path(document_path)
    filename = path.stem.lower()

    # Filename-based heuristics
    invoice_keywords = ['invoice', 'inv', 'bill', 'receipt', 'payment', 'order']
    agreement_keywords = ['agreement', 'contract', 'nda', 'msa', 'sow', 'lease', 'terms', 'policy']
    kyc_keywords = ['passport', 'license', 'id', 'identity', 'permit', 'visa', 'aadhaar', 'pan']

    features = []

    # Check filename
    for kw in invoice_keywords:
        if kw in filename:
            features.append(f'filename:{kw}')
            return {
                'type': 'invoice',
                'confidence': 0.8,
                'method': 'filename_keyword',
                'features': features
            }

    for kw in agreement_keywords:
        if kw in filename:
            features.append(f'filename:{kw}')
            return {
                'type': 'agreement',
                'confidence': 0.8,
                'method': 'filename_keyword',
                'features': features
            }

    for kw in kyc_keywords:
        if kw in filename:
            features.append(f'filename:{kw}')
            return {
                'type': 'kyc',
                'confidence': 0.8,
                'method': 'filename_keyword',
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


# Global reference to router for getting registered types
_active_router: Optional['AgentRouter'] = None


def _analyze_content(
    document_path: str,
    content_hint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze document content to determine type using LLM.

    Uses Gemini for intelligent classification with fallback to keywords.
    """
    # Get registered types from active router
    registered_types = []
    if _active_router:
        registered_types = _active_router.list_types()

    # Try to extract document content
    content = _extract_document_content(document_path)

    # Try LLM classification first
    llm_result = _classify_with_llm(
        document_path=document_path,
        content=content,
        registered_types=registered_types,
        content_hint=content_hint
    )

    if llm_result:
        return llm_result

    # Fallback to keyword-based classification
    logger.debug("Using keyword-based fallback classification")
    return _analyze_content_fallback(document_path, content_hint)


class AgentRouter:
    """
    Routes documents to specialized agents based on classification.

    Supports:
    - Built-in agent registration (invoice, agreement, kyc)
    - Custom agent registration
    - Classification-first routing
    - LLM-based intelligent document classification

    Usage:
        router = AgentRouter()

        # Register built-in agents
        router.register(['invoice', 'bill', 'receipt'], invoice_agent)
        router.register(['agreement', 'contract'], agreement_agent)

        # Route a document (uses LLM classification)
        classification = classify_document(document_path)
        agent = router.route(classification)
    """

    def __init__(self, set_as_active: bool = True):
        """
        Initialize router with empty routes.

        Args:
            set_as_active: If True, set this router as the active router
                          for LLM classification context
        """
        self._routes: Dict[str, LlmAgent] = {}
        self._type_aliases: Dict[str, str] = {}

        if set_as_active:
            self._set_as_active()

    def _set_as_active(self) -> None:
        """Set this router as the active router for classification."""
        global _active_router
        _active_router = self
        logger.debug("Set router as active for LLM classification")

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
