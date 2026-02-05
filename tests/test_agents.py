"""
Tests for agent modules
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.orchestrator import OrchestratorAgent
from agents.invoice_agent import InvoiceAgent
from agents.agreement_agent import AgreementAgent
from agents.kyc_agent import KYCAgent


class TestOrchestratorAgent:
    """Tests for OrchestratorAgent"""

    def test_initialization(self):
        """Test agent initialization"""
        config = {
            'classification_confidence_threshold': 0.7,
            'enable_auto_detection': True
        }
        agent = OrchestratorAgent(config)

        assert agent.classification_threshold == 0.7
        assert agent.auto_detection is True

    def test_register_sub_agent(self):
        """Test sub-agent registration"""
        config = {}
        orchestrator = OrchestratorAgent(config)

        invoice_agent = InvoiceAgent({})
        orchestrator.register_sub_agent('invoice_agent', invoice_agent)

        assert 'invoice_agent' in orchestrator.sub_agents


class TestInvoiceAgent:
    """Tests for InvoiceAgent"""

    def test_initialization(self):
        """Test invoice agent initialization"""
        config = {
            'schema_path': 'schemas/invoice.json',
            'model': 'gemini-1.5-pro'
        }
        agent = InvoiceAgent(config)

        assert agent.schema_path == 'schemas/invoice.json'
        assert agent.model == 'gemini-1.5-pro'

    @pytest.mark.asyncio
    async def test_extract_structure(self):
        """Test extraction returns proper structure"""
        config = {}
        agent = InvoiceAgent(config)

        result = await agent.extract('test_invoice.pdf')

        # Verify structure
        assert 'document_type' in result
        assert result['document_type'] == 'invoice'
        assert 'metadata' in result
        assert 'vendor' in result
        assert 'financial' in result


class TestAgreementAgent:
    """Tests for AgreementAgent"""

    def test_initialization(self):
        """Test agreement agent initialization"""
        config = {
            'schema_path': 'schemas/agreement.json',
            'extract_clauses': True
        }
        agent = AgreementAgent(config)

        assert agent.extract_clauses is True


class TestKYCAgent:
    """Tests for KYCAgent"""

    def test_initialization(self):
        """Test KYC agent initialization"""
        config = {
            'verify_documents': True
        }
        agent = KYCAgent(config)

        assert agent.verify_documents is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
