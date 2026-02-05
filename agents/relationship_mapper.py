"""
Relationship Mapper Agent

Agent responsible for detecting and mapping relationships between documents.
"""

import logging
from typing import Dict, List, Any, Optional
import re
from collections import defaultdict

logger = logging.getLogger(__name__)


class RelationshipMapperAgent:
    """
    Agent that detects relationships between documents using multiple strategies:
    - Filename pattern matching
    - Explicit reference detection
    - Entity matching
    - Temporal correlation
    - Semantic analysis
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize relationship mapper agent

        Args:
            config: Agent configuration
        """
        self.config = config
        self.confidence_threshold = config.get('confidence_threshold', 0.6)
        self.enabled_detectors = config.get('detectors', [
            'filename_pattern',
            'explicit_reference',
            'entity_matching',
            'temporal_correlation'
        ])

        logger.info(f"Relationship mapper initialized with detectors: {self.enabled_detectors}")

    async def map_relationships(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect relationships between documents

        Args:
            documents: List of processed documents with extracted data

        Returns:
            List of detected relationships
        """
        logger.info(f"Mapping relationships for {len(documents)} documents")

        relationships = []

        # Run enabled detectors
        if 'filename_pattern' in self.enabled_detectors:
            relationships.extend(self.detect_filename_patterns(documents))

        if 'explicit_reference' in self.enabled_detectors:
            relationships.extend(self.detect_explicit_references(documents))

        if 'entity_matching' in self.enabled_detectors:
            relationships.extend(self.detect_entity_matches(documents))

        if 'temporal_correlation' in self.enabled_detectors:
            relationships.extend(self.detect_temporal_correlations(documents))

        # Filter by confidence threshold
        relationships = [
            r for r in relationships
            if r['confidence'] >= self.confidence_threshold
        ]

        # Consolidate duplicate relationships
        relationships = self.consolidate_relationships(relationships)

        logger.info(f"Detected {len(relationships)} relationships")

        return relationships

    def detect_filename_patterns(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect relationships based on filename patterns

        Args:
            documents: List of documents

        Returns:
            List of detected relationships
        """
        relationships = []

        # Patterns to detect
        patterns = [
            (r'INV[-_]?(\d+)', r'PO[-_]?\1', 'invoice_for_po'),
            (r'invoice[-_]?(\d+)', r'purchase[-_]?order[-_]?\1', 'invoice_for_po'),
            (r'(.+)[-_]part[-_]?(\d+)', r'\1[-_]part[-_]?\d+', 'multi_part_document'),
        ]

        for pattern, related_pattern, rel_type in patterns:
            matches = defaultdict(list)

            # Find documents matching each pattern
            for doc in documents:
                filename = doc.get('document_path', '').split('/')[-1]
                match = re.search(pattern, filename)
                if match:
                    key = match.group(1) if match.lastindex >= 1 else match.group(0)
                    matches[key].append(doc)

            # Create relationships for documents with matching keys
            for key, related_docs in matches.items():
                if len(related_docs) > 1:
                    for i, doc1 in enumerate(related_docs):
                        for doc2 in related_docs[i+1:]:
                            relationships.append({
                                'source': doc1.get('document_path'),
                                'target': doc2.get('document_path'),
                                'type': rel_type,
                                'confidence': 0.9,
                                'evidence': f'Filename pattern match: {key}'
                            })

        return relationships

    def detect_explicit_references(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect explicit references between documents

        Args:
            documents: List of documents

        Returns:
            List of detected relationships
        """
        relationships = []

        # Extract document identifiers
        doc_identifiers = {}
        for doc in documents:
            identifiers = []

            # Get invoice numbers, PO numbers, etc.
            if doc.get('document_type') == 'invoice':
                invoice_num = doc.get('metadata', {}).get('invoice_number')
                if invoice_num:
                    identifiers.append(invoice_num)

            doc_identifiers[doc['document_path']] = identifiers

        # TODO: Implement full reference detection logic
        # This would involve parsing document text for references

        return relationships

    def detect_entity_matches(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect relationships based on common entities (vendors, customers, etc.)

        Args:
            documents: List of documents

        Returns:
            List of detected relationships
        """
        relationships = []

        # Compare entity overlap between documents
        for i, doc1 in enumerate(documents):
            for doc2 in documents[i+1:]:
                overlap = self._calculate_entity_overlap(doc1, doc2)

                if overlap['score'] > 0.3:  # Significant overlap
                    relationships.append({
                        'source': doc1.get('document_path'),
                        'target': doc2.get('document_path'),
                        'type': 'shared_entities',
                        'confidence': overlap['score'],
                        'evidence': f"Common entities: {', '.join(overlap['common'][:5])}"
                    })

        return relationships

    def detect_temporal_correlations(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect relationships based on temporal proximity

        Args:
            documents: List of documents

        Returns:
            List of detected relationships
        """
        relationships = []

        # TODO: Implement temporal correlation detection
        # Compare dates from documents and find temporally related ones

        return relationships

    def _calculate_entity_overlap(
        self,
        doc1: Dict[str, Any],
        doc2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate entity overlap between two documents

        Args:
            doc1: First document
            doc2: Second document

        Returns:
            Overlap score and common entities
        """
        # Extract entities from both documents
        entities1 = self._extract_entities(doc1)
        entities2 = self._extract_entities(doc2)

        # Find common entities
        common = set(entities1) & set(entities2)

        # Calculate overlap score
        if not entities1 or not entities2:
            score = 0.0
        else:
            score = len(common) / max(len(entities1), len(entities2))

        return {
            'score': score,
            'common': list(common)
        }

    def _extract_entities(self, doc: Dict[str, Any]) -> List[str]:
        """
        Extract entity names from document

        Args:
            doc: Document with extracted data

        Returns:
            List of entity names
        """
        entities = []

        # Extract based on document type
        if doc.get('document_type') == 'invoice':
            vendor = doc.get('vendor', {}).get('name')
            customer = doc.get('customer', {}).get('name')
            if vendor:
                entities.append(vendor)
            if customer:
                entities.append(customer)

        # Add more extraction logic for other document types

        return entities

    def consolidate_relationships(
        self,
        relationships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Consolidate duplicate relationships

        Args:
            relationships: List of detected relationships

        Returns:
            Consolidated list with merged duplicates
        """
        # Group by source-target pair
        grouped = defaultdict(list)
        for rel in relationships:
            key = (rel['source'], rel['target'])
            grouped[key].append(rel)

        # Consolidate each group
        consolidated = []
        for key, rels in grouped.items():
            if len(rels) == 1:
                consolidated.append(rels[0])
            else:
                # Merge multiple detections
                best = max(rels, key=lambda r: r['confidence'])
                best['evidence'] = ' | '.join([r['evidence'] for r in rels])
                best['detection_methods'] = [r['type'] for r in rels]
                consolidated.append(best)

        return consolidated
