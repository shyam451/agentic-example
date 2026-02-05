"""
Pipeline Builder

Composes agents into processing pipelines.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for a pipeline."""
    name: str
    type: str  # 'sequential' or 'parallel'
    agents: List[str]
    description: str = ""


class PipelineBuilder:
    """
    Builds processing pipelines from agents.

    Supports:
    - Sequential pipelines (agents run in order)
    - Parallel pipelines (agents run concurrently)
    - Extraction pipelines (preprocessor → extractor → postprocessor)

    Usage:
        builder = PipelineBuilder()

        # Create sequential pipeline
        pipeline = builder.create_sequential_pipeline(
            name="InvoicePipeline",
            agents=[preprocessor, invoice_agent, postprocessor]
        )

        # Create from config
        pipeline = builder.create_from_config(pipeline_config)
    """

    def __init__(self, agent_registry: Optional[Dict[str, LlmAgent]] = None):
        """
        Initialize pipeline builder.

        Args:
            agent_registry: Optional dict mapping agent names to instances
        """
        self._agent_registry = agent_registry or {}
        self._pipeline_cache: Dict[str, LlmAgent] = {}

    def register_agent(self, name: str, agent: LlmAgent) -> None:
        """Register an agent for use in pipelines."""
        self._agent_registry[name] = agent
        logger.debug(f"Registered agent for pipelines: {name}")

    def register_agents(self, agents: Dict[str, LlmAgent]) -> None:
        """Register multiple agents."""
        self._agent_registry.update(agents)

    def create_sequential_pipeline(
        self,
        name: str,
        agents: List[LlmAgent],
        description: str = ""
    ) -> SequentialAgent:
        """
        Create a sequential processing pipeline.

        Agents run in order, each receiving the output of the previous.

        Args:
            name: Pipeline name
            agents: Ordered list of agents
            description: Pipeline description

        Returns:
            SequentialAgent wrapping the pipeline
        """
        pipeline = SequentialAgent(
            name=name,
            description=description or f"Sequential pipeline: {' → '.join(a.name for a in agents)}",
            sub_agents=agents
        )

        self._pipeline_cache[name] = pipeline
        logger.info(f"Created sequential pipeline: {name} with {len(agents)} agents")

        return pipeline

    def create_parallel_pipeline(
        self,
        name: str,
        agents: List[LlmAgent],
        description: str = ""
    ) -> ParallelAgent:
        """
        Create a parallel processing pipeline.

        All agents run concurrently on the same input.

        Args:
            name: Pipeline name
            agents: List of agents to run in parallel
            description: Pipeline description

        Returns:
            ParallelAgent wrapping the pipeline
        """
        pipeline = ParallelAgent(
            name=name,
            description=description or f"Parallel pipeline: {', '.join(a.name for a in agents)}",
            sub_agents=agents
        )

        self._pipeline_cache[name] = pipeline
        logger.info(f"Created parallel pipeline: {name} with {len(agents)} agents")

        return pipeline

    def create_from_config(self, config: PipelineConfig) -> LlmAgent:
        """
        Create pipeline from configuration.

        Args:
            config: Pipeline configuration

        Returns:
            Configured pipeline agent
        """
        # Resolve agent names to instances
        agents = []
        for agent_name in config.agents:
            if agent_name in self._agent_registry:
                agents.append(self._agent_registry[agent_name])
            else:
                raise ValueError(f"Agent not found in registry: {agent_name}")

        # Create pipeline based on type
        if config.type == 'sequential':
            return self.create_sequential_pipeline(
                name=config.name,
                agents=agents,
                description=config.description
            )
        elif config.type == 'parallel':
            return self.create_parallel_pipeline(
                name=config.name,
                agents=agents,
                description=config.description
            )
        else:
            raise ValueError(f"Unknown pipeline type: {config.type}")

    def create_extraction_pipeline(
        self,
        extractor_agent: LlmAgent,
        preprocessor_agent: Optional[LlmAgent] = None,
        postprocessor_agent: Optional[LlmAgent] = None,
        name: Optional[str] = None
    ) -> SequentialAgent:
        """
        Create a standard extraction pipeline.

        Pipeline structure: Preprocessor → Extractor → Postprocessor

        Args:
            extractor_agent: Main extraction agent
            preprocessor_agent: Optional preprocessor for document preparation
            postprocessor_agent: Optional postprocessor for enrichment
            name: Pipeline name (auto-generated if not provided)

        Returns:
            SequentialAgent for the extraction pipeline
        """
        agents = []

        if preprocessor_agent:
            agents.append(preprocessor_agent)

        agents.append(extractor_agent)

        if postprocessor_agent:
            agents.append(postprocessor_agent)

        pipeline_name = name or f"{extractor_agent.name}Pipeline"

        return self.create_sequential_pipeline(
            name=pipeline_name,
            agents=agents,
            description=f"Extraction pipeline for {extractor_agent.name}"
        )

    def create_multi_document_pipeline(
        self,
        name: str,
        extractor_agents: List[LlmAgent],
        preprocessor_agent: Optional[LlmAgent] = None,
        postprocessor_agent: Optional[LlmAgent] = None
    ) -> SequentialAgent:
        """
        Create a pipeline for processing multiple document types in parallel.

        Structure: Preprocessor → [Parallel extractors] → Postprocessor

        Args:
            name: Pipeline name
            extractor_agents: List of extraction agents to run in parallel
            preprocessor_agent: Optional preprocessor
            postprocessor_agent: Optional postprocessor

        Returns:
            SequentialAgent for the multi-document pipeline
        """
        agents = []

        if preprocessor_agent:
            agents.append(preprocessor_agent)

        # Create parallel extractor stage
        if len(extractor_agents) > 1:
            parallel_extractors = self.create_parallel_pipeline(
                name=f"{name}_Extractors",
                agents=extractor_agents,
                description="Parallel document extractors"
            )
            agents.append(parallel_extractors)
        else:
            agents.extend(extractor_agents)

        if postprocessor_agent:
            agents.append(postprocessor_agent)

        return self.create_sequential_pipeline(
            name=name,
            agents=agents,
            description=f"Multi-document pipeline with {len(extractor_agents)} extractors"
        )

    def get_cached_pipeline(self, name: str) -> Optional[LlmAgent]:
        """Get pipeline from cache."""
        return self._pipeline_cache.get(name)

    def list_pipelines(self) -> List[str]:
        """List cached pipeline names."""
        return list(self._pipeline_cache.keys())

    def clear_cache(self) -> None:
        """Clear pipeline cache."""
        self._pipeline_cache.clear()
