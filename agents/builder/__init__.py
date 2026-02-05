"""
Custom Agent Builder Module

Provides components for creating and configuring custom extraction agents:
- ConfigValidator: Validate YAML configs against JSON Schema
- SchemaRegistry: Manage extraction schemas with inheritance
- ToolRegistry: Manage reusable tool functions
- AgentFactory: Create LlmAgent instances from configuration
- AgentRouter: Classification-first routing to agents
- PipelineBuilder: Compose agents into pipelines
"""

from .config_validator import ConfigValidator, ConfigValidationError
from .schema_registry import SchemaRegistry
from .tool_registry import ToolRegistry, ToolDefinition
from .agent_factory import AgentFactory, CustomAgentConfig, AgentExtensionConfig
from .agent_router import AgentRouter, classify_document
from .pipeline_builder import PipelineBuilder

__all__ = [
    # Config validation
    'ConfigValidator',
    'ConfigValidationError',
    # Schema management
    'SchemaRegistry',
    # Tool management
    'ToolRegistry',
    'ToolDefinition',
    # Agent creation
    'AgentFactory',
    'CustomAgentConfig',
    'AgentExtensionConfig',
    # Routing
    'AgentRouter',
    'classify_document',
    # Pipeline
    'PipelineBuilder',
]
