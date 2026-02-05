"""
Agent Factory

Creates LlmAgent instances from configuration.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable

import yaml
from google.adk.agents import LlmAgent

from .schema_registry import SchemaRegistry
from .tool_registry import ToolRegistry
from .config_validator import ConfigValidator

logger = logging.getLogger(__name__)


@dataclass
class AgentExtensionConfig:
    """Configuration for extending a built-in agent."""
    extends: str
    custom_prompts: List[str]
    additional_fields: List[str] = field(default_factory=list)
    validation_rules: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CustomAgentConfig:
    """Configuration for a custom agent."""
    name: str
    document_type: str
    instruction: str
    description: str = ""
    model: str = "gemini-2.5-flash"
    schema_path: Optional[str] = None
    tools: List[str] = field(default_factory=list)
    custom_prompts: List[str] = field(default_factory=list)
    validation_rules: List[Dict[str, Any]] = field(default_factory=list)


# Built-in agent instructions
BUILTIN_INSTRUCTIONS = {
    'InvoiceAgent': """You are an expert invoice extraction agent. Your task is to:

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
""",
    'AgreementAgent': """You are an expert legal agreement extraction agent. Your task is to:

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
""",
    'KYCAgent': """You are an expert KYC (Know Your Customer) document extraction agent.

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
}


class AgentFactory:
    """
    Factory for creating LlmAgent instances from configuration.

    Supports:
    - Creating custom agents from YAML or dict config
    - Extending built-in agents with custom prompts
    - Caching created agents

    Usage:
        factory = AgentFactory(schema_registry, tool_registry)

        # Create from config object
        agent = factory.create_agent(CustomAgentConfig(...))

        # Create from YAML file
        agents = factory.create_from_yaml('config/custom_agents.yaml')

        # Extend built-in agent
        enhanced_invoice = factory.extend_builtin_agent(
            'InvoiceAgent',
            custom_prompts=['Extract PO references']
        )
    """

    def __init__(
        self,
        schema_registry: Optional[SchemaRegistry] = None,
        tool_registry: Optional[ToolRegistry] = None,
        default_model: Optional[str] = None
    ):
        """
        Initialize agent factory.

        Args:
            schema_registry: Registry for extraction schemas
            tool_registry: Registry for tool functions
            default_model: Default model to use (from env if not specified)
        """
        self.schema_registry = schema_registry or SchemaRegistry()
        self.tool_registry = tool_registry or ToolRegistry()
        self.default_model = default_model or os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

        self._agent_cache: Dict[str, LlmAgent] = {}

    def create_agent(self, config: CustomAgentConfig) -> LlmAgent:
        """
        Create an LlmAgent from configuration.

        Args:
            config: Agent configuration

        Returns:
            Configured LlmAgent
        """
        # Build instruction with custom prompts
        instruction = config.instruction
        if config.custom_prompts:
            instruction += "\n\nAdditional extraction requirements:\n"
            for i, prompt in enumerate(config.custom_prompts, 1):
                instruction += f"{i}. {prompt}\n"

        # Resolve tools
        tools = []
        if config.tools:
            for tool_name in config.tools:
                if self.tool_registry.has_tool(tool_name):
                    tools.append(self.tool_registry.get_tool(tool_name))
                else:
                    logger.warning(f"Tool not found: {tool_name}")

        # Create agent
        agent = LlmAgent(
            model=config.model or self.default_model,
            name=config.name,
            description=config.description or f"Custom agent for {config.document_type} documents",
            instruction=instruction,
            tools=tools if tools else None,
            output_key=f"{config.document_type}_result"
        )

        # Cache the agent
        self._agent_cache[config.name] = agent

        logger.info(f"Created custom agent: {config.name} for document type: {config.document_type}")
        return agent

    def extend_builtin_agent(
        self,
        agent_name: str,
        custom_prompts: List[str],
        additional_tools: Optional[List[str]] = None,
        model: Optional[str] = None
    ) -> LlmAgent:
        """
        Create an extended version of a built-in agent.

        Args:
            agent_name: Name of built-in agent (InvoiceAgent, AgreementAgent, KYCAgent)
            custom_prompts: Additional extraction instructions
            additional_tools: Additional tool names to include
            model: Model override (optional)

        Returns:
            Extended LlmAgent
        """
        if agent_name not in BUILTIN_INSTRUCTIONS:
            raise ValueError(
                f"Unknown built-in agent: {agent_name}. "
                f"Available: {list(BUILTIN_INSTRUCTIONS.keys())}"
            )

        # Build extended instruction
        base_instruction = BUILTIN_INSTRUCTIONS[agent_name]
        instruction = base_instruction + "\n\nAdditional extraction requirements:\n"
        for i, prompt in enumerate(custom_prompts, 1):
            instruction += f"{i}. {prompt}\n"

        # Resolve tools
        tools = []
        if additional_tools:
            for tool_name in additional_tools:
                if self.tool_registry.has_tool(tool_name):
                    tools.append(self.tool_registry.get_tool(tool_name))

        # Determine document type from agent name
        doc_type_map = {
            'InvoiceAgent': 'invoice',
            'AgreementAgent': 'agreement',
            'KYCAgent': 'kyc'
        }
        doc_type = doc_type_map.get(agent_name, 'document')

        # Create extended agent with "Extended" prefix
        extended_name = f"Extended{agent_name}"

        agent = LlmAgent(
            model=model or self.default_model,
            name=extended_name,
            description=f"Extended {agent_name} with custom extraction requirements",
            instruction=instruction,
            tools=tools if tools else None,
            output_key=f"{doc_type}_result"
        )

        self._agent_cache[extended_name] = agent
        logger.info(f"Created extended agent: {extended_name}")

        return agent

    def create_from_yaml(
        self,
        yaml_path: str,
        validate: bool = True
    ) -> Dict[str, LlmAgent]:
        """
        Create agents from YAML configuration file.

        Args:
            yaml_path: Path to YAML config file
            validate: Whether to validate config against schema

        Returns:
            Dict mapping agent names to LlmAgent instances
        """
        # Validate config
        if validate:
            validator = ConfigValidator()
            config = validator.validate_config(yaml_path)
        else:
            with open(yaml_path, 'r') as f:
                config = yaml.safe_load(f)

        agents = {}

        # Process agent extensions
        for ext_config in config.get('agent_extensions', []):
            extension = AgentExtensionConfig(
                extends=ext_config['extends'],
                custom_prompts=ext_config['custom_prompts'],
                additional_fields=ext_config.get('additional_fields', []),
                validation_rules=ext_config.get('validation_rules', [])
            )

            agent = self.extend_builtin_agent(
                extension.extends,
                extension.custom_prompts
            )
            agents[agent.name] = agent

        # Process custom agents
        for agent_config in config.get('custom_agents', []):
            custom = CustomAgentConfig(
                name=agent_config['name'],
                document_type=agent_config['document_type'],
                instruction=agent_config['instruction'],
                description=agent_config.get('description', ''),
                model=agent_config.get('model', self.default_model),
                schema_path=agent_config.get('schema_path'),
                tools=agent_config.get('tools', []),
                custom_prompts=agent_config.get('custom_prompts', []),
                validation_rules=agent_config.get('validation_rules', [])
            )

            agent = self.create_agent(custom)
            agents[agent.name] = agent

        logger.info(f"Created {len(agents)} agents from {yaml_path}")
        return agents

    def create_from_dict(self, config: Dict[str, Any]) -> LlmAgent:
        """
        Create agent from dictionary configuration.

        Args:
            config: Agent configuration dict

        Returns:
            LlmAgent instance
        """
        custom = CustomAgentConfig(
            name=config['name'],
            document_type=config['document_type'],
            instruction=config['instruction'],
            description=config.get('description', ''),
            model=config.get('model', self.default_model),
            schema_path=config.get('schema_path'),
            tools=config.get('tools', []),
            custom_prompts=config.get('custom_prompts', []),
            validation_rules=config.get('validation_rules', [])
        )

        return self.create_agent(custom)

    def get_cached_agent(self, name: str) -> Optional[LlmAgent]:
        """Get agent from cache by name."""
        return self._agent_cache.get(name)

    def list_cached_agents(self) -> List[str]:
        """List names of cached agents."""
        return list(self._agent_cache.keys())

    def clear_cache(self):
        """Clear agent cache."""
        self._agent_cache.clear()

    def get_builtin_agent(self, name: str) -> LlmAgent:
        """
        Get a built-in agent (without extensions).

        Args:
            name: Agent name (InvoiceAgent, AgreementAgent, KYCAgent)

        Returns:
            LlmAgent instance
        """
        if name not in BUILTIN_INSTRUCTIONS:
            raise ValueError(f"Unknown built-in agent: {name}")

        # Check cache first
        if name in self._agent_cache:
            return self._agent_cache[name]

        doc_type_map = {
            'InvoiceAgent': 'invoice',
            'AgreementAgent': 'agreement',
            'KYCAgent': 'kyc'
        }
        doc_type = doc_type_map[name]

        agent = LlmAgent(
            model=self.default_model,
            name=name,
            description=f"Specialized agent for extracting data from {doc_type} documents",
            instruction=BUILTIN_INSTRUCTIONS[name],
            output_key=f"{doc_type}_result"
        )

        self._agent_cache[name] = agent
        return agent
