"""
Tool Registry

Manages reusable tool functions for agents.
"""

import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Metadata for a registered tool."""
    name: str
    function: Callable
    description: str
    category: str = "general"
    parameters: Dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """
    Registry for reusable tool functions.

    Tools are callable functions that agents can use during extraction.
    Built-in tools are auto-registered on initialization.

    Usage:
        registry = ToolRegistry()

        # Get a tool
        parse_pdf = registry.get_tool('parse_pdf')

        # Get multiple tools
        tools = registry.get_tools(['parse_pdf', 'perform_ocr'])

        # Register custom tool
        registry.register('my_tool', my_function, "Description", "custom")

        # List available tools
        all_tools = registry.list_tools()
        parsing_tools = registry.list_tools(category='parsing')
    """

    # Tool categories
    CATEGORY_PARSING = 'parsing'
    CATEGORY_OCR = 'ocr'
    CATEGORY_EXTRACTION = 'extraction'
    CATEGORY_VALIDATION = 'validation'
    CATEGORY_PREPROCESSING = 'preprocessing'
    CATEGORY_ENRICHMENT = 'enrichment'

    def __init__(self, auto_register: bool = True):
        """
        Initialize tool registry.

        Args:
            auto_register: If True, auto-register built-in tools
        """
        self._tools: Dict[str, ToolDefinition] = {}

        if auto_register:
            self._register_builtin_tools()

    def _register_builtin_tools(self):
        """Register built-in document processing tools."""
        try:
            # PDF parsing tools
            from tools.pdf_parser import PDFParser
            parser = PDFParser()

            self.register(
                name='parse_pdf',
                function=parser.parse,
                description='Parse PDF document and extract text content',
                category=self.CATEGORY_PARSING,
                parameters={'document_path': 'str'}
            )

            self.register(
                name='extract_pdf_text',
                function=parser.extract_text,
                description='Extract raw text from PDF',
                category=self.CATEGORY_PARSING,
                parameters={'document_path': 'str'}
            )
        except ImportError as e:
            logger.debug(f"PDF parser not available: {e}")

        try:
            # OCR tools
            from tools.ocr_engine import OCREngine
            ocr = OCREngine()

            self.register(
                name='perform_ocr',
                function=ocr.process,
                description='Perform OCR on image or scanned document',
                category=self.CATEGORY_OCR,
                parameters={'image_path': 'str'}
            )
        except ImportError as e:
            logger.debug(f"OCR engine not available: {e}")

        try:
            # Table extraction tools
            from tools.table_extractor import TableExtractor
            extractor = TableExtractor()

            self.register(
                name='extract_tables',
                function=extractor.extract,
                description='Extract tables from document',
                category=self.CATEGORY_EXTRACTION,
                parameters={'document_path': 'str'}
            )
        except ImportError as e:
            logger.debug(f"Table extractor not available: {e}")

        try:
            # MIME handling tools
            from tools.mime_handler import UniversalMIMEHandler
            handler = UniversalMIMEHandler()

            self.register(
                name='detect_mime_type',
                function=handler.detect_type,
                description='Detect MIME type of document',
                category=self.CATEGORY_PARSING,
                parameters={'document_path': 'str'}
            )
        except ImportError as e:
            logger.debug(f"MIME handler not available: {e}")

        try:
            # Preprocessor tools
            from tools.preprocessor import (
                preprocess_document,
                extract_archive,
                extract_email,
                extract_pdf_portfolio
            )

            self.register(
                name='preprocess_document',
                function=preprocess_document,
                description='Preprocess document, extracting nested files from containers',
                category=self.CATEGORY_PREPROCESSING,
                parameters={'document_path': 'str', 'max_depth': 'int'}
            )

            self.register(
                name='extract_archive',
                function=extract_archive,
                description='Extract files from ZIP/RAR/TAR archive',
                category=self.CATEGORY_PREPROCESSING,
                parameters={'archive_path': 'str', 'output_dir': 'str'}
            )

            self.register(
                name='extract_email',
                function=extract_email,
                description='Parse email and extract attachments',
                category=self.CATEGORY_PREPROCESSING,
                parameters={'email_path': 'str', 'output_dir': 'str'}
            )

            self.register(
                name='extract_pdf_portfolio',
                function=extract_pdf_portfolio,
                description='Extract embedded files from PDF portfolio',
                category=self.CATEGORY_PREPROCESSING,
                parameters={'pdf_path': 'str', 'output_dir': 'str'}
            )
        except ImportError as e:
            logger.debug(f"Preprocessor not available: {e}")

        logger.info(f"Registered {len(self._tools)} built-in tools")

    def register(
        self,
        name: str,
        function: Callable,
        description: str,
        category: str = "general",
        parameters: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a tool function.

        Args:
            name: Tool identifier
            function: Callable function
            description: Human-readable description
            category: Tool category for organization
            parameters: Parameter definitions
        """
        self._tools[name] = ToolDefinition(
            name=name,
            function=function,
            description=description,
            category=category,
            parameters=parameters or {}
        )
        logger.debug(f"Registered tool: {name} ({category})")

    def get_tool(self, name: str) -> Callable:
        """
        Get tool function by name.

        Args:
            name: Tool identifier

        Returns:
            Tool function

        Raises:
            KeyError: If tool not found
        """
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}. Available: {list(self._tools.keys())}")

        return self._tools[name].function

    def get_tools(self, names: List[str]) -> List[Callable]:
        """
        Get multiple tool functions.

        Args:
            names: List of tool identifiers

        Returns:
            List of tool functions
        """
        return [self.get_tool(name) for name in names]

    def get_tool_definition(self, name: str) -> ToolDefinition:
        """Get full tool definition including metadata."""
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]

    def has_tool(self, name: str) -> bool:
        """Check if tool exists."""
        return name in self._tools

    def list_tools(self, category: Optional[str] = None) -> List[ToolDefinition]:
        """
        List available tools.

        Args:
            category: Filter by category (optional)

        Returns:
            List of tool definitions
        """
        tools = list(self._tools.values())

        if category:
            tools = [t for t in tools if t.category == category]

        return sorted(tools, key=lambda t: t.name)

    def list_tool_names(self, category: Optional[str] = None) -> List[str]:
        """List tool names only."""
        return [t.name for t in self.list_tools(category)]

    def get_categories(self) -> List[str]:
        """Get all tool categories."""
        return sorted(set(t.category for t in self._tools.values()))
