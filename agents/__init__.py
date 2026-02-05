"""
Document Extraction Agents Module

This module contains all specialized agents for document extraction,
plus the custom agent builder system.

Agents:
- OrchestratorAgent: Main coordinator
- InvoiceAgent: Invoice extraction
- AgreementAgent: Contract/agreement extraction
- KYCAgent: Identity document extraction

Builder System:
- AgentFactory: Create agents from config
- AgentRouter: Classification-first routing
- SchemaRegistry: Extraction schema management
- ToolRegistry: Tool function registry
- PipelineBuilder: Agent pipeline composition
"""

from agents.orchestrator import OrchestratorAgent
from agents.invoice_agent import InvoiceAgent
from agents.agreement_agent import AgreementAgent
from agents.kyc_agent import KYCAgent
from agents.relationship_mapper import RelationshipMapperAgent

# Import builder components
try:
    from agents.builder import (
        AgentFactory,
        AgentRouter,
        ConfigValidator,
        ConfigValidationError,
        SchemaRegistry,
        ToolRegistry,
        ToolDefinition,
        PipelineBuilder,
        CustomAgentConfig,
        AgentExtensionConfig,
        classify_document,
    )
    BUILDER_AVAILABLE = True
except ImportError:
    BUILDER_AVAILABLE = False

__all__ = [
    # Agents
    'OrchestratorAgent',
    'InvoiceAgent',
    'AgreementAgent',
    'KYCAgent',
    'RelationshipMapperAgent',
]

# Add builder exports if available
if BUILDER_AVAILABLE:
    __all__.extend([
        'AgentFactory',
        'AgentRouter',
        'ConfigValidator',
        'ConfigValidationError',
        'SchemaRegistry',
        'ToolRegistry',
        'ToolDefinition',
        'PipelineBuilder',
        'CustomAgentConfig',
        'AgentExtensionConfig',
        'classify_document',
    ])
