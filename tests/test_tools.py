"""
Tests for tool modules
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.pdf_parser import PDFParser
from tools.ocr_engine import OCREngine
from tools.table_extractor import TableExtractor
from tools.mime_handler import UniversalMIMEHandler


class TestPDFParser:
    """Tests for PDFParser"""

    def test_initialization(self):
        """Test parser initialization"""
        parser = PDFParser()
        assert '.pdf' in parser.supported_formats

    @pytest.mark.asyncio
    async def test_parse_structure(self):
        """Test parse returns proper structure"""
        parser = PDFParser()
        result = await parser.parse('test.pdf')

        # Verify structure
        assert 'text' in result
        assert 'pages' in result
        assert 'metadata' in result
        assert 'extraction_method' in result


class TestOCREngine:
    """Tests for OCREngine"""

    def test_initialization(self):
        """Test OCR engine initialization"""
        engine = OCREngine()
        assert engine.use_document_ai is True

    @pytest.mark.asyncio
    async def test_extract_structure(self):
        """Test extract returns proper structure"""
        engine = OCREngine()
        result = await engine.extract('test.jpg', language='en')

        # Verify structure
        assert 'text' in result
        assert 'confidence' in result
        assert 'ocr_engine' in result


class TestTableExtractor:
    """Tests for TableExtractor"""

    def test_initialization(self):
        """Test table extractor initialization"""
        extractor = TableExtractor()
        assert extractor.primary_method in ['camelot', 'tabula', 'pdfplumber']

    @pytest.mark.asyncio
    async def test_extract_structure(self):
        """Test extract returns proper structure"""
        extractor = TableExtractor()
        result = await extractor.extract('test.pdf')

        # Verify structure
        assert 'tables' in result
        assert 'table_count' in result
        assert 'confidence' in result


class TestUniversalMIMEHandler:
    """Tests for UniversalMIMEHandler"""

    def test_initialization(self):
        """Test MIME handler initialization"""
        handler = UniversalMIMEHandler()
        assert len(handler.handlers) > 0

    @pytest.mark.asyncio
    async def test_detect_mime(self):
        """Test MIME detection"""
        handler = UniversalMIMEHandler()
        result = await handler.detect_mime('test.pdf')

        # Verify structure
        assert 'mime_type' in result
        assert 'extension' in result

    @pytest.mark.asyncio
    async def test_process_structure(self):
        """Test process returns proper structure"""
        handler = UniversalMIMEHandler()
        result = await handler.process('test.pdf')

        # Verify structure
        assert 'mime_type' in result
        assert 'processing_success' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
