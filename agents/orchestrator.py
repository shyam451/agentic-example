"""
Orchestrator Agent

Main ADK agent that coordinates document extraction across specialized sub-agents.
Uses Google ADK's LlmAgent with hierarchical multi-agent delegation.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent

logger = logging.getLogger(__name__)


@dataclass
class DocumentClassification:
    """Result of document classification"""
    document_type: str
    confidence: float
    detected_features: Dict[str, Any]


# Tool functions for orchestration
def classify_document_type(document_path: str) -> Dict[str, Any]:
    """
    Classify document type using pattern matching and content analysis.

    Args:
        document_path: Path to document (local or GCS)

    Returns:
        Classification result with document type and confidence
    """
    logger.info(f"Classifying document: {document_path}")

    # TODO: Implement actual classification using:
    # 1. Filename patterns
    # 2. MIME type detection
    # 3. Content sampling with Gemini
    # 4. Keyword detection

    # Placeholder classification
    return {
        "document_type": "invoice",
        "confidence": 0.95,
        "detected_features": {
            "has_line_items": True,
            "has_totals": True,
            "has_vendor_info": True
        }
    }


def aggregate_extraction_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate results from multiple document extractions.

    Args:
        results: List of extraction results from sub-agents

    Returns:
        Aggregated results with summary statistics
    """
    logger.info(f"Aggregating {len(results)} extraction results")

    aggregated = {
        "total_documents": len(results),
        "successful_extractions": sum(1 for r in results if r.get("_metadata", {}).get("confidence", 0) > 0.7),
        "document_types": {},
        "results": results
    }

    # Count document types
    for result in results:
        doc_type = result.get("document_type", "unknown")
        aggregated["document_types"][doc_type] = aggregated["document_types"].get(doc_type, 0) + 1

    return aggregated


def create_orchestrator_agent(
    invoice_agent: LlmAgent,
    agreement_agent: LlmAgent,
    kyc_agent: LlmAgent,
    model: str = "gemini-2.0-flash-exp",
    enable_relationship_detection: bool = False
) -> LlmAgent:
    """
    Create the main ADK orchestrator agent with sub-agent delegation.

    Args:
        invoice_agent: Invoice extraction agent
        agreement_agent: Agreement extraction agent
        kyc_agent: KYC extraction agent
        model: The Gemini model to use for orchestration
        enable_relationship_detection: Whether to enable cross-document relationship detection

    Returns:
        Configured LlmAgent for orchestration
    """

    instruction = """You are the main orchestrator agent for document extraction. Your responsibilities:

1. CLASSIFY documents to determine their type (invoice, agreement, kyc, or other)
2. DELEGATE extraction to the appropriate specialized agent based on classification
3. COORDINATE multi-document processing when batches are provided
4. AGGREGATE results from all sub-agents
5. ENSURE quality by validating confidence scores

Available specialized agents:
- InvoiceAgent: For invoices, receipts, bills
- AgreementAgent: For contracts, agreements, legal documents
- KYCAgent: For identity documents (passports, licenses, ID cards)

When processing a single document:
1. Use classify_document_type to determine the document type
2. Based on classification confidence (threshold: 0.7):
   - High confidence (>= 0.7): Delegate to appropriate specialized agent
   - Low confidence (< 0.7): Try multiple agents and pick best result
3. Return the extraction result with classification metadata

When processing multiple documents:
1. Classify each document first
2. Group documents by type
3. Process each group with the appropriate specialized agent
4. Use aggregate_extraction_results to combine results
5. Optionally detect relationships between documents

Document path(s) will be in session state as {document_path} or {document_paths}
"""

    # Create the orchestrator with sub-agents
    orchestrator = LlmAgent(
        model=model,
        name="OrchestratorAgent",
        description="Main coordinator for document extraction across specialized sub-agents",
        instruction=instruction,
        tools=[
            classify_document_type,
            aggregate_extraction_results
        ],
        sub_agents=[
            invoice_agent,
            agreement_agent,
            kyc_agent
        ],
        output_key="orchestrator_result"
    )

    logger.info("Orchestrator agent created with 3 specialized sub-agents")
    return orchestrator


def create_batch_processing_pipeline(
    orchestrator: LlmAgent,
    relationship_mapper: Optional[LlmAgent] = None
) -> SequentialAgent:
    """
    Create a sequential pipeline for batch document processing.

    Args:
        orchestrator: The main orchestrator agent
        relationship_mapper: Optional relationship detection agent

    Returns:
        SequentialAgent pipeline for batch processing
    """

    agents = [orchestrator]

    # Add relationship mapper if provided
    if relationship_mapper:
        agents.append(relationship_mapper)

    pipeline = SequentialAgent(
        name="BatchProcessingPipeline",
        sub_agents=agents,
        description="Sequential pipeline for batch document processing with relationship detection"
    )

    logger.info(f"Batch processing pipeline created with {len(agents)} stages")
    return pipeline


def create_parallel_extraction_pipeline(
    invoice_agent: LlmAgent,
    agreement_agent: LlmAgent,
    kyc_agent: LlmAgent
) -> ParallelAgent:
    """
    Create a parallel processing pipeline for mixed document types.

    Useful when you have pre-classified documents and want to process them concurrently.

    Args:
        invoice_agent: Invoice extraction agent
        agreement_agent: Agreement extraction agent
        kyc_agent: KYC extraction agent

    Returns:
        ParallelAgent for concurrent extraction
    """

    parallel = ParallelAgent(
        name="ParallelExtractionPipeline",
        sub_agents=[
            invoice_agent,
            agreement_agent,
            kyc_agent
        ],
        description="Process multiple documents of different types in parallel"
    )

    logger.info("Parallel extraction pipeline created")
    return parallel


# Backward compatibility class
class OrchestratorAgent:
    """
    Wrapper class for ADK orchestrator agent to maintain backward compatibility.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize orchestrator agent with ADK backend.

        Args:
            config: Configuration dictionary with agent settings
        """
        self.config = config
        self.classification_threshold = config.get('classification_confidence_threshold', 0.7)
        self.auto_detection = config.get('enable_auto_detection', True)
        self.sub_agents = {}
        self.adk_orchestrator = None

        logger.info("Orchestrator agent initialized (ADK backend)")

    def register_sub_agent(self, agent_type: str, agent):
        """
        Register a specialized sub-agent.

        Args:
            agent_type: Type of agent (e.g., 'invoice_agent', 'agreement_agent')
            agent: The agent instance (should have adk_agent attribute)
        """
        self.sub_agents[agent_type] = agent
        logger.info(f"Registered sub-agent: {agent_type}")

        # Rebuild orchestrator if we have all required agents
        if len(self.sub_agents) >= 3:
            self._rebuild_orchestrator()

    def _rebuild_orchestrator(self):
        """Rebuild the ADK orchestrator with registered sub-agents."""

        # Extract ADK agents from wrappers
        invoice_adk = self.sub_agents.get('invoice_agent').adk_agent if 'invoice_agent' in self.sub_agents else None
        agreement_adk = self.sub_agents.get('agreement_agent').adk_agent if 'agreement_agent' in self.sub_agents else None
        kyc_adk = self.sub_agents.get('kyc_agent').adk_agent if 'kyc_agent' in self.sub_agents else None

        if invoice_adk and agreement_adk and kyc_adk:
            self.adk_orchestrator = create_orchestrator_agent(
                invoice_agent=invoice_adk,
                agreement_agent=agreement_adk,
                kyc_agent=kyc_adk,
                model=self.config.get('model', 'gemini-2.0-flash-exp')
            )
            logger.info("ADK orchestrator rebuilt with all sub-agents")

    async def classify_document(self, document_path: str) -> DocumentClassification:
        """
        Classify document type.

        Args:
            document_path: Path to document (local or GCS)

        Returns:
            DocumentClassification with type and confidence
        """
        logger.info(f"Classifying document: {document_path}")

        # Use the classification tool
        result = classify_document_type(document_path)

        return DocumentClassification(
            document_type=result["document_type"],
            confidence=result["confidence"],
            detected_features=result["detected_features"]
        )

    async def process_document(
        self,
        document_path: str,
        custom_prompts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process a single document.

        Args:
            document_path: Path to document
            custom_prompts: Optional custom extraction prompts

        Returns:
            Extraction results
        """
        logger.info(f"Processing document: {document_path}")

        # 1. Classify document
        classification = await self.classify_document(document_path)

        # 2. Select appropriate agent
        if classification.confidence < self.classification_threshold:
            logger.warning(f"Low classification confidence: {classification.confidence}")
            agent_type = "custom"
        else:
            agent_type = classification.document_type

        # 3. Delegate to specialized agent
        agent_key = f"{agent_type}_agent"
        agent = self.sub_agents.get(agent_key)

        if not agent:
            logger.error(f"No agent registered for type: {agent_type}")
            raise ValueError(f"No agent available for document type: {agent_type}")

        result = await agent.extract(document_path, custom_prompts)

        # 4. Add metadata
        result['_metadata'] = {
            'classification': classification.document_type,
            'confidence': classification.confidence,
            'agent_type': agent_type,
            'orchestrator': 'ADK-powered'
        }

        return result

    async def process_batch(
        self,
        document_paths: List[str],
        enable_relationships: bool = False,
        cross_document_queries: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process multiple documents with optional cross-document analysis.

        Args:
            document_paths: List of document paths
            enable_relationships: Whether to detect relationships
            cross_document_queries: Optional cross-document queries

        Returns:
            Aggregated results with relationships
        """
        logger.info(f"Processing batch of {len(document_paths)} documents")

        # 1. Process all documents
        results = []
        for doc_path in document_paths:
            try:
                result = await self.process_document(doc_path)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing {doc_path}: {e}")
                results.append({
                    "document_path": doc_path,
                    "error": str(e),
                    "status": "failed"
                })

        # 2. Aggregate results
        aggregated = aggregate_extraction_results(results)

        # 3. Build relationship graph if enabled
        relationships = []
        if enable_relationships and 'relationship_mapper' in self.sub_agents:
            mapper = self.sub_agents['relationship_mapper']
            try:
                relationships = await mapper.map_relationships(results)
            except Exception as e:
                logger.error(f"Error in relationship mapping: {e}")

        # 4. Answer cross-document queries if provided
        cross_doc_insights = []
        if cross_document_queries:
            # TODO: Implement cross-document query answering with ADK
            logger.info(f"Cross-document queries requested: {len(cross_document_queries)}")

        return {
            'documents': results,
            'summary': aggregated,
            'relationships': relationships,
            'cross_document_insights': cross_doc_insights,
            'total_processed': len(results),
            'successful': aggregated['successful_extractions'],
            'failed': len(results) - aggregated['successful_extractions']
        }
