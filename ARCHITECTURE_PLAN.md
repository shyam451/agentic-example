# DocAI Agentic - Complete Architecture & Implementation Plan

**Document Extraction Engine powered by Google Agent Engine**

---

## Table of Contents

1. [Overview](#overview)
2. [System Requirements](#system-requirements)
3. [Architecture Design](#architecture-design)
4. [Component Details](#component-details)
5. [Implementation Roadmap](#implementation-roadmap)
6. [Technology Stack](#technology-stack)
7. [Key Design Decisions](#key-design-decisions)
8. [Detailed Features](#detailed-features)
9. [Deployment Strategy](#deployment-strategy)
10. [Performance & Cost](#performance--cost)

---

## Overview

### What We're Building

A **truly agentic, low-code document extraction engine** that:

- ✅ Handles **any document type** (all MIME types)
- ✅ Processes **nested/compound documents** (ZIPs, emails, portfolios)
- ✅ Supports **multi-document extraction** with cross-document analysis
- ✅ Allows **custom prompt injection** for specialized extraction
- ✅ Detects **relationships between documents** automatically
- ✅ Provides **structured JSON output** with confidence scores
- ✅ Runs on **fully managed Agent Engine** (auto-scaling, zero ops)

### User Experience

```bash
# Single command deployment
docai deploy --project=my-project

# Single command extraction
docai extract invoice.pdf

# That's it. Agent handles everything else.
```

---

## System Requirements

### Functional Requirements

1. **Document Ingestion**
   - Accept documents from local filesystem, GCS, S3
   - Support all major document formats
   - Handle nested documents (archives, emails with attachments)
   - Process single documents or batches

2. **Extraction**
   - Extract structured data matching predefined schemas
   - Support custom user-defined extraction prompts
   - Maintain confidence scores for all extracted fields
   - Handle partial extraction gracefully

3. **Multi-Document Processing**
   - Detect relationships between documents
   - Perform cross-document validation
   - Answer cross-document queries
   - Build document graphs

4. **Output**
   - Structured JSON output
   - Schema-compliant results
   - Relationship mappings
   - Quality metrics

### Non-Functional Requirements

1. **Performance**
   - Single document: 5-15 seconds
   - Batch (100 docs): 5-10 minutes
   - Throughput: 500-1000 docs/hour

2. **Reliability**
   - 99.5% success rate
   - Graceful degradation
   - Retry mechanisms
   - Partial result support

3. **Scalability**
   - Auto-scale 1-20 instances
   - Handle 10,000+ docs/day
   - Support concurrent requests

4. **Accuracy**
   - >95% accuracy for structured fields
   - >85% accuracy for unstructured content
   - Confidence scoring on all extractions

---

## Architecture Design

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│              (CLI, Python SDK, Config Files)                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│         Vertex AI Agent Engine (Fully Managed)              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────┐        │
│  │       Orchestrator Agent (Main Agent)          │        │
│  │  • Document classification                     │        │
│  │  • Agent delegation                            │        │
│  │  • Result aggregation                          │        │
│  └──────┬──────────────────────────────────┬──────┘        │
│         │                                   │               │
│    ┌────▼────────┐  ┌──────────────┐  ┌───▼────────┐      │
│    │  Invoice    │  │  Agreement   │  │    KYC     │      │
│    │  Agent      │  │  Agent       │  │   Agent    │      │
│    └──────┬──────┘  └──────┬───────┘  └─────┬──────┘      │
│           │                 │                 │             │
│    ┌──────▼─────────────────▼─────────────────▼──────┐    │
│    │           Tool Registry (MCP)                    │    │
│    │  • PDF Parser   • OCR Engine                     │    │
│    │  • Table Extract • MIME Handler                  │    │
│    │  • Relationship Mapper                           │    │
│    └──────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐      ┌─────▼──────┐    ┌─────▼─────┐
   │ Cloud   │      │  Document  │    │  BigQuery │
   │ Storage │      │  AI API    │    │(Analytics)│
   └─────────┘      └────────────┘    └───────────┘
```

### Multi-Agent Workflow

```
Phase 1: Document Ingestion
┌────────────────────────────────────┐
│  Document Collection Manager       │
│  • Multi-doc ingestion             │
│  • Nested extraction               │
│  • MIME detection                  │
└──────────┬─────────────────────────┘
           │
Phase 2: Classification & Routing
┌──────────▼─────────────────────────┐
│  Orchestrator Agent                │
│  • Classify document type          │
│  • Select specialized agent        │
│  • Build context                   │
└──────────┬─────────────────────────┘
           │
Phase 3: Specialized Extraction
┌──────────▼─────────────────────────┐
│  Specialized Agent                 │
│  • Schema-based extraction         │
│  • Custom prompt processing        │
│  • Validation                      │
└──────────┬─────────────────────────┘
           │
Phase 4: Relationship Detection (Multi-doc)
┌──────────▼─────────────────────────┐
│  Relationship Mapper Agent         │
│  • Detect document links           │
│  • Build document graph            │
│  • Cross-validate                  │
└──────────┬─────────────────────────┘
           │
Phase 5: Aggregation & Output
┌──────────▼─────────────────────────┐
│  Result Aggregator                 │
│  • Quality checks                  │
│  • Format output                   │
│  • Return results                  │
└────────────────────────────────────┘
```

---

## Component Details

### 1. Orchestrator Agent

**Purpose:** Main coordinator for all extraction activities

**Responsibilities:**
- Document classification (invoice, agreement, KYC, etc.)
- Sub-agent delegation based on classification
- Context building for multi-document scenarios
- Result aggregation and validation
- Custom prompt distribution

**Key Methods:**
```python
async def classify_document(document_path) -> DocumentClassification
async def process_document(document_path, custom_prompts) -> Dict
async def process_batch(document_paths, enable_relationships) -> Dict
```

**Configuration:**
- Classification confidence threshold: 0.7
- Auto-detection enabled by default
- Registered sub-agents: invoice, agreement, kyc, relationship_mapper, custom

### 2. Specialized Agents

#### Invoice Agent

**Schema Fields:**
- metadata: invoice_number, invoice_date, due_date, po_number
- vendor: name, address, tax_id, contact
- customer: name, address, tax_id
- line_items: description, quantity, unit_price, amount
- financial: subtotal, tax, total_amount, currency
- payment_terms: terms, method, bank_details

**Validation:**
- Check line items sum to subtotal
- Verify date logic (due_date >= invoice_date)
- Validate required fields presence

#### Agreement Agent

**Schema Fields:**
- metadata: agreement_type, effective_date, expiry_date
- parties: role, name, address, representative
- key_terms: scope, payment_terms, termination_clause, governing_law
- obligations: party, obligation, deadline
- penalties: condition, penalty, amount
- renewal_terms: auto_renewal, renewal_period
- signatures: party, signatory, date, detected

**Special Features:**
- Extract penalty clauses
- Identify renewal terms
- Detect termination conditions

#### KYC Agent

**Schema Fields:**
- metadata: document_id, document_subtype, issue_date, expiry_date
- personal_info: full_name, date_of_birth, nationality, gender
- address: street, city, state, postal_code, country
- verification: photo_present, mrz_data, security_features_detected

**Special Features:**
- MRZ extraction for passports
- Document authenticity verification
- Photo extraction
- Security feature detection

#### Relationship Mapper Agent

**Detection Strategies:**
1. **Filename Pattern Matching** (confidence: 0.9)
   - INV-001 matches PO-001
   - document_part1 matches document_part2

2. **Explicit Reference Detection** (confidence: 0.95)
   - Document mentions another document ID
   - Cross-references in text

3. **Entity Matching** (confidence: 0.3-0.8)
   - Common vendor names
   - Shared customer entities
   - Overlapping amounts

4. **Temporal Correlation** (confidence: 0.5-1.0)
   - Documents within 30 days
   - Same billing period

5. **Semantic Analysis** (confidence: varies)
   - LLM-based relationship detection
   - Context understanding

**Output:**
- Document graph with nodes (documents) and edges (relationships)
- Confidence scores for each relationship
- Evidence for detected relationships

### 3. Tool Ecosystem (MCP)

#### PDF Parser
- **Primary**: PyMuPDF (fitz) for native text PDFs
- **Features**: Text extraction, image extraction, metadata
- **Fallback**: pdfplumber for complex layouts

#### OCR Engine
- **Primary**: Google Document AI
- **Fallback**: Tesseract OCR
- **Preprocessing**: Deskew, denoise, contrast enhancement
- **Output**: Text with confidence scores and bounding boxes

#### Table Extractor
- **Primary**: Camelot (lattice and stream modes)
- **Alternatives**: Tabula, pdfplumber
- **Features**: Structured table data, header detection
- **Validation**: Minimum 2 rows, 2 columns

#### Universal MIME Handler
- **Supported Types**: 30+ MIME types
- **Strategy**: Primary handler → Fallback chain → Emergency extraction
- **Formats**:
  - Documents: PDF, DOC, DOCX, TXT, RTF
  - Spreadsheets: XLS, XLSX, CSV
  - Images: JPG, PNG, TIFF, BMP, HEIC
  - Archives: ZIP, RAR, TAR, 7Z
  - Email: EML, MSG
  - Web: HTML, XML, JSON

#### Nested Document Preprocessor
- **Max Depth**: 10 levels
- **Features**: Recursive extraction, hierarchy preservation
- **Outputs**: Flat list + tree structure
- **Examples**: ZIP → PDFs, Email → attachments, PDF portfolio → embedded files

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
**Focus:** Core infrastructure and basic document handling

**Tasks:**
1. Set up Vertex AI project and Agent Engine API
2. Implement universal MIME handler with fallback chains
3. Build document ingestion pipeline with nested extraction
4. Create basic orchestrator agent skeleton
5. Set up MCP tool server structure

**Deliverable:** Can ingest and detect any document type

**Key Files:**
- `tools/mime_handler.py` - Complete implementation
- `tools/pdf_parser.py` - Complete implementation
- `agents/orchestrator.py` - Basic skeleton
- `tools/mcp_server.py` - MCP server setup

### Phase 2: Core Extraction (Weeks 2-4)
**Focus:** Single-agent extraction working end-to-end

**Tasks:**
1. Develop Invoice Agent as reference implementation
2. Implement PDF parser + OCR integration (Google Document AI)
3. Build schema-based extraction engine
4. Add rule-based + LLM hybrid extraction
5. Create validation logic

**Deliverable:** Production-quality invoice extraction

**Key Files:**
- `agents/invoice_agent.py` - Complete implementation
- `tools/ocr_engine.py` - Google Document AI + Tesseract
- `tools/table_extractor.py` - Table extraction
- `schemas/invoice.json` - Finalized schema

**Success Metrics:**
- >90% accuracy on invoice test dataset
- <10 second processing time
- Confidence scores implemented

### Phase 3: Multi-Agent System (Weeks 4-6)
**Focus:** Multiple specialized agents working together

**Tasks:**
1. Create Agreement and KYC agents using Invoice Agent template
2. Implement document classification in orchestrator
3. Build agent delegation logic with ADK
4. Add custom prompt injection system
5. Test inter-agent communication

**Deliverable:** Multi-agent extraction for 3+ document types

**Key Files:**
- `agents/agreement_agent.py` - Complete implementation
- `agents/kyc_agent.py` - Complete implementation
- `agents/orchestrator.py` - Full delegation logic
- `config/extraction_config.yaml` - Custom prompts config

**Success Metrics:**
- Classification accuracy >95%
- All 3 agents operational
- Custom prompts working

### Phase 4: Cross-Document Features (Weeks 6-7)
**Focus:** Multi-document extraction with relationships

**Tasks:**
1. Implement all relationship detection algorithms
2. Build DocumentGraph and clustering
3. Create CrossDocumentAnalyzer agent
4. Add cross-validation logic
5. Implement cross-document queries

**Deliverable:** Multi-document extraction with relationships

**Key Files:**
- `agents/relationship_mapper.py` - All detectors implemented
- Cross-document analyzer
- Document graph structure

**Success Metrics:**
- Relationship detection >80% accuracy
- Cross-document queries working
- Graph visualization ready

### Phase 5: Robustness (Weeks 7-8)
**Focus:** Production-grade reliability

**Tasks:**
1. Implement comprehensive error handling
2. Add retry policies and circuit breakers
3. Build fallback extraction chains
4. Create partial result merging
5. Add logging and monitoring

**Deliverable:** Production-grade reliability

**Key Files:**
- Error handling throughout all modules
- Retry policies
- Circuit breakers
- Monitoring integration

**Success Metrics:**
- 99%+ success rate with fallbacks
- Graceful degradation working
- All errors logged properly

### Phase 6: Performance (Weeks 8-9)
**Focus:** Optimization for speed and scale

**Tasks:**
1. Implement multi-tier caching (memory, disk, distributed)
2. Add batch optimization
3. Build incremental processing
4. Performance profiling and optimization
5. Load testing

**Deliverable:** 5x performance improvement

**Key Files:**
- Caching layer
- Batch optimizer
- Performance monitoring

**Success Metrics:**
- <5s for simple documents
- 1000 docs/hour throughput
- Cache hit rate >60%

### Phase 7: Configuration & UX (Weeks 9-10)
**Focus:** Low-code interface

**Tasks:**
1. Create configuration system (YAML/JSON)
2. Build CLI interface
3. Add Python SDK
4. Create configuration validation
5. Write documentation

**Deliverable:** True low-code interface

**Key Files:**
- `client/cli.py` - Complete CLI
- `client/client.py` - Python SDK
- `config/extraction_config.yaml` - User config
- Documentation

**Success Metrics:**
- Single-command deployment
- Single-command extraction
- Config validation working

### Phase 8: Quality & Evaluation (Weeks 10-11)
**Focus:** Quality assurance and metrics

**Tasks:**
1. Implement evaluation framework
2. Add continuous quality monitoring
3. Build benchmark suite
4. Create alerting system
5. Set up dashboards

**Deliverable:** Production quality assurance

**Key Files:**
- Evaluation framework
- Benchmark datasets
- Quality metrics
- Alerting system

**Success Metrics:**
- Evaluation running on all extractions
- Benchmarks passing
- Alerts configured

### Phase 9: Deployment (Weeks 11-12)
**Focus:** Production deployment

**Tasks:**
1. Create Docker containers
2. Build Kubernetes configs (optional)
3. Deploy to Vertex AI Agent Engine
4. Set up monitoring and observability
5. Configure auto-scaling

**Deliverable:** Production deployment

**Key Files:**
- `deployment/deploy.py` - Complete deployment script
- Docker configuration
- Monitoring setup

**Success Metrics:**
- Deployed to Agent Engine
- Auto-scaling working
- Monitoring operational

### Phase 10: Testing & Refinement (Weeks 12-14)
**Focus:** Final polish and launch prep

**Tasks:**
1. End-to-end testing with real documents
2. Performance benchmarking
3. Security audit
4. Documentation completion
5. User acceptance testing

**Deliverable:** Production-ready system

**Success Metrics:**
- All tests passing
- Documentation complete
- Security approved
- Users can successfully extract

---

## Technology Stack

### Core Framework
- **Google ADK (Python)** - Multi-agent orchestration
- **Vertex AI Agent Engine** - Managed runtime
- **Gemini 1.5 Pro** - Primary LLM (via Vertex AI)
- **AsyncIO** - Concurrency and async operations

### Document Processing
- **PyMuPDF (fitz)** - PDF text extraction
- **pdfplumber** - Alternative PDF parser
- **Google Document AI** - Production OCR
- **Tesseract** - Fallback OCR
- **python-docx** - DOCX processing
- **openpyxl** - Excel processing
- **python-magic** - MIME type detection
- **Pillow** - Image processing

### Table Extraction
- **camelot-py** - Primary table extraction
- **tabula-py** - Alternative table extraction
- **pdfplumber** - Backup table extraction

### NLP & Text Processing
- **spaCy** - Named Entity Recognition
- **en_core_web_sm** - English NLP model

### Data & Storage
- **Google Cloud Storage** - Document storage
- **Redis** - Distributed caching (optional)
- **Cloud SQL/Firestore** - Metadata storage
- **pandas** - Data manipulation
- **numpy** - Numerical operations

### Web & Processing
- **BeautifulSoup4** - HTML parsing
- **lxml** - XML processing
- **requests** - HTTP requests

### Archive Handling
- **zipfile** - ZIP archives (built-in)
- **rarfile** - RAR archives
- **py7zr** - 7z archives
- **tarfile** - TAR archives (built-in)

### Email Processing
- **email** - Email parsing (built-in)
- **extract-msg** - Outlook MSG files

### Configuration & Utilities
- **PyYAML** - YAML configuration
- **python-dotenv** - Environment variables
- **aiofiles** - Async file operations

### Infrastructure
- **Docker** - Containerization
- **Kubernetes** - Orchestration (optional)
- **Prometheus** - Metrics
- **Cloud Logging** - Logging
- **Cloud Monitoring** - Monitoring

### Development
- **pytest** - Testing framework
- **pytest-asyncio** - Async testing
- **pytest-cov** - Coverage
- **black** - Code formatting
- **flake8** - Linting
- **mypy** - Type checking

---

## Key Design Decisions

### 1. Multi-Agent vs Single-Agent

**Decision:** Multi-agent architecture with specialized agents per document type

**Rationale:**
- Each document type has unique structure and extraction requirements
- Specialized agents achieve higher accuracy than general-purpose
- Easier to maintain and extend
- Better prompt engineering per document type
- Agent Engine natively supports multi-agent systems

**Trade-offs:**
- More complex than single agent
- Requires orchestration logic
- Higher initial development cost

### 2. Google Agent Engine vs Self-Hosted ADK

**Decision:** Native deployment to Google Agent Engine

**Rationale:**
- Fully managed infrastructure (zero ops)
- Built-in auto-scaling (1-20+ instances)
- Native state management
- Event-driven architecture
- Integrated monitoring
- Pay-per-use pricing
- First-class MCP support

**Trade-offs:**
- Google Cloud vendor lock-in
- Less control over infrastructure
- Potentially higher cost at massive scale

### 3. Hybrid Extraction (Rules + LLM)

**Decision:** Combine rule-based extraction with LLM-based extraction

**Rationale:**
- Rules excel at structured data (tables, known patterns)
- LLM excels at unstructured/ambiguous content
- Optimal accuracy + cost balance
- Faster processing with rules where possible
- LLM handles edge cases

**Implementation:**
- Extract tables with Camelot → parse with rules
- Extract text with PDF parser → LLM for understanding
- Validate with rules → LLM fills gaps

### 4. Schema-First Approach

**Decision:** Predefined JSON schemas for all document types

**Rationale:**
- Consistent, structured output
- Enables validation
- Facilitates downstream integrations
- Clear contract for consumers
- Easier testing and quality metrics

**Flexibility:**
- Custom fields via custom_extractions
- User-defined prompts extend schemas
- Schema versioning support

### 5. Universal MIME Handler with Fallback Chains

**Decision:** Support all MIME types with multi-level fallback

**Rationale:**
- Financial domain has diverse document formats
- Graceful degradation better than failure
- Future-proof for new formats
- User experience priority

**Fallback Strategy:**
1. Primary handler (format-specific)
2. Alternative handler (different library)
3. Format conversion + retry
4. OCR as last resort
5. Metadata-only if all fail

### 6. Confidence Scoring on Everything

**Decision:** Every extraction has a confidence score

**Rationale:**
- Financial domain requires auditability
- Enables human-in-the-loop for low confidence
- Quality metrics and monitoring
- Identify improvement opportunities
- Risk management

**Implementation:**
- Field-level confidence scores
- Document-level aggregate score
- Relationship confidence scores
- Threshold-based alerting

### 7. Event-Driven ADK Runtime

**Decision:** Use ADK's event-driven architecture

**Rationale:**
- Natural fit for multi-step document processing
- Enables async parallel processing
- State management handled by framework
- Better resource utilization
- Scalability built-in

**Benefits:**
- Process batch documents in parallel
- Async tool calls
- Reactive to events (new documents)
- Stateful conversations

### 8. MCP for Tool Integration

**Decision:** Use Model Context Protocol for all tools

**Rationale:**
- Standardized protocol
- Agent Engine first-class support
- Clean separation of concerns
- Easy to add new tools
- Future-proof for tool ecosystem

**Tool Categories:**
- Document processing (PDF, OCR, tables)
- MIME detection
- Relationship detection
- Custom user tools (extensible)

### 9. Caching Strategy

**Decision:** Multi-tier caching (memory → disk → distributed)

**Rationale:**
- Documents rarely change
- OCR and parsing expensive
- Significant performance gains
- Cost reduction

**Cache Levels:**
1. **Memory** (LRU, 100 items) - Fastest
2. **Disk** (10GB, 7 day TTL) - Persistent
3. **Redis** (optional) - Shared across instances

**Cache Key:** Content hash (SHA-256 of file)

### 10. Partial Results Support

**Decision:** Allow and merge partial results from failures

**Rationale:**
- Something better than nothing
- Financial domain values any data
- User can decide threshold
- Graceful degradation

**Implementation:**
- Multiple extraction attempts
- Merge results from different methods
- Confidence-based field selection
- Clear indication of partial status

---

## Detailed Features

### 1. Custom Prompt Injection

**Purpose:** Allow users to extend extraction without code changes

**Levels:**
1. **Global** - Applied to all documents
2. **Document Type** - Applied to specific types (invoice, agreement)
3. **Field Level** - Define custom fields with extraction prompts
4. **Cross-Document** - Queries spanning multiple documents

**Configuration Example:**
```yaml
custom_extraction:
  global:
    - "Extract all monetary values in USD and EUR"
    - "Flag any regulatory compliance mentions"

  invoice:
    - "Extract payment terms and early payment discounts"
    - "Identify tax jurisdiction"

  agreement:
    fields:
      penalty_clauses: "Extract all penalty clauses with amounts"
      renewal_terms: "Identify renewal and auto-renewal terms"

  cross_document:
    - query: "Match invoices to purchase orders"
      scope: "multi"
```

**Implementation:**
- Prompts injected at agent level
- Merged with base schema prompts
- Priority: field > type > global
- Results in custom_extractions field

### 2. Nested Document Processing

**Scenarios:**
- **ZIP files** containing multiple PDFs
- **Email (.eml, .msg)** with attachments
- **PDF portfolios** with embedded files
- **Structured data** (JSON with base64 images)

**Processing Flow:**
```
Input: document_package.zip
  ↓
Detect: Archive container
  ↓
Extract recursively:
  ├── invoice1.pdf (depth=1)
  ├── po1.pdf (depth=1)
  └── subfolder/
      └── contract.pdf (depth=2)
  ↓
Process each independently
  ↓
Build document tree:
  - Root: document_package.zip
    - invoice1.pdf (extracted data)
    - po1.pdf (extracted data)
    - contract.pdf (extracted data)
  ↓
Return: Flat list + hierarchical tree
```

**Configuration:**
- `max_nesting_depth`: 10 (configurable)
- `preserve_hierarchy`: true
- Relationship detection across nested docs

### 3. Relationship Detection

**Detection Methods:**

#### Filename Pattern (Confidence: 0.9)
```python
# Patterns
INV-001.pdf ↔ PO-001.pdf  # Invoice matches PO
contract_v1.pdf ↔ contract_v2.pdf  # Versioning
document_part1.pdf ↔ document_part2.pdf  # Multi-part
```

#### Explicit Reference (Confidence: 0.95)
```python
# Document text mentions
"Reference: PO-12345"
"As per agreement AGR-001"
"See invoice INV-789"
```

#### Entity Matching (Confidence: 0.3-0.8)
```python
# Shared entities
Common vendor: "Acme Corporation"
Same customer: "Big Company Inc"
Matching amounts: $10,000.00
```

#### Temporal Correlation (Confidence: 0.5-1.0)
```python
# Documents within time window
Invoice date: 2024-01-15
PO date: 2024-01-10
Difference: 5 days → Related
```

#### Semantic Analysis (Confidence: varies)
```python
# LLM-based understanding
"This invoice is for services rendered under MSA-2024-001"
→ Links invoice to master service agreement
```

**Output:**
```json
{
  "relationships": [
    {
      "source": "invoice1.pdf",
      "target": "po1.pdf",
      "type": "invoice_for_po",
      "confidence": 0.95,
      "evidence": "Invoice references PO-12345",
      "detection_methods": ["filename_pattern", "explicit_reference"]
    }
  ],
  "document_graph": {
    "nodes": [...],
    "edges": [...]
  }
}
```

### 4. Cross-Document Queries

**Purpose:** Answer questions spanning multiple documents

**Examples:**
```python
# Aggregation
"What is the total invoice amount by vendor?"

# Matching
"Which invoices don't have matching purchase orders?"

# Validation
"Are all invoice amounts within approved contract limits?"

# Temporal
"Which contracts expire in the next 90 days?"
```

**Implementation:**
1. Extract all documents
2. Build shared context
3. LLM analyzes combined data
4. Return structured answer with sources

**Output:**
```json
{
  "query": "Total invoice amount by vendor",
  "answer": {
    "Vendor A": 125000.00,
    "Vendor B": 87500.00
  },
  "source_documents": ["inv1.pdf", "inv2.pdf", "inv3.pdf"],
  "confidence": 0.92
}
```

### 5. Error Handling & Recovery

**Multi-Layer Strategy:**

#### Layer 1: Retry Policy
```python
max_attempts: 3
backoff: exponential (1s, 2s, 4s)
retry_on: [timeout, rate_limit, transient_errors]
```

#### Layer 2: Fallback Chains
```python
Primary → Alternative → Conversion → OCR → Metadata
```

#### Layer 3: Partial Results
```python
if extraction_failed:
    merge partial results
    set low confidence
    flag for review
```

#### Layer 4: Circuit Breaker
```python
if failures > 5:
    open circuit
    return cached or fail fast
```

**Example:**
```
PDF Extraction Failed
  ↓
Try OCR
  ↓
OCR Failed
  ↓
Extract Metadata Only
  ↓
Return Partial Result:
  - file_path
  - mime_type
  - file_size
  - status: "partial_failure"
```

### 6. Caching & Performance

**Cache Strategy:**

```python
# Check cache
cache_key = sha256(file_content)
if cache_hit(cache_key):
    return cached_result

# Process
result = extract_document()

# Store in cache
cache_set(cache_key, result, ttl=7_days)
```

**Optimization Techniques:**

1. **Deduplication**
   - Hash all documents in batch
   - Process unique documents only
   - Replicate results for duplicates

2. **Parallel Processing**
   - Group documents by type
   - Process each group in parallel
   - Async tool calls

3. **Smart Preprocessing**
   - Quick quality check
   - Skip OCR for native text PDFs
   - Detect blank pages

4. **Incremental Processing**
   - Cache intermediate results
   - Resume from failure point
   - Stage-by-stage caching

**Performance Metrics:**
- Processing time per document
- Throughput (docs/hour)
- Cache hit rate
- Error rate
- Confidence score distribution

### 7. Quality Metrics & Evaluation

**Evaluation Without Ground Truth:**

```python
quality_score = (
    completeness * 0.3 +    # % of required fields populated
    consistency * 0.3 +      # Internal data consistency
    confidence * 0.4         # Average confidence scores
)
```

**Metrics:**

1. **Completeness** (0-1)
   - Required fields populated / Total required fields

2. **Consistency** (0-1)
   - Check: line items sum == subtotal
   - Check: due_date >= invoice_date
   - Check: amounts match across related docs

3. **Confidence** (0-1)
   - Average of all field confidence scores
   - Weighted by field importance

4. **Schema Compliance** (0-1)
   - Valid JSON schema
   - All types correct
   - Required fields present

**Alerting:**
```python
if quality_score < 0.5:
    trigger_alert("Low quality extraction")
    flag_for_manual_review()
```

**Benchmark Testing:**
```python
# Test against labeled datasets
datasets = {
    'invoices': 100 documents,
    'agreements': 50 documents,
    'kyc': 75 documents
}

for doc, ground_truth in dataset:
    result = extract(doc)
    accuracy = compare(result, ground_truth)

aggregate_accuracy = sum(accuracies) / len(dataset)
```

---

## Deployment Strategy

### Deployment Options

```
1. Local Development
   ├── Python virtual environment
   ├── Local file system
   └── SQLite metadata

2. Docker Container
   ├── Docker Compose
   ├── Persistent volumes
   └── Redis cache

3. Google Cloud Run (Serverless)
   ├── Auto-scaling containers
   ├── Cloud Storage
   └── Managed services

4. Vertex AI Agent Engine (Recommended)
   ├── Fully managed ADK runtime
   ├── Native GCP integration
   └── Enterprise features

5. Kubernetes (Advanced)
   ├── Full control
   ├── Multi-cloud
   └── Custom scaling
```

### Recommended: Vertex AI Agent Engine

**Architecture:**
```
Load Balancer
    ↓
Agent Engine (1-20 instances)
    ↓
├── Cloud Storage (documents)
├── Redis (cache)
└── Cloud SQL (metadata)
```

**Deployment Steps:**

1. **Prerequisites**
```bash
# Enable APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable documentai.googleapis.com

# Create GCS bucket
gsutil mb gs://docai-extraction-${PROJECT_ID}

# Upload schemas
gsutil cp schemas/*.json gs://docai-extraction-${PROJECT_ID}/schemas/
```

2. **Deploy**
```bash
# Run deployment script
python deployment/deploy.py \
  --project-id=${PROJECT_ID} \
  --region=us-central1 \
  --bucket=docai-extraction-${PROJECT_ID}
```

3. **Configure**
```bash
# Save endpoint info
export DOCAI_ENDPOINT=<endpoint-from-deployment>

# Test
python -m client.cli extract test_invoice.pdf
```

**Scaling Configuration:**
```yaml
scaling:
  min_replicas: 1
  max_replicas: 20
  target_concurrent_requests: 5
  scale_down_delay: 300
  cpu_utilization_target: 0.7
  memory_utilization_target: 0.8
```

**Monitoring:**
- Cloud Monitoring dashboards
- Prometheus metrics export
- Custom alerts
- Log aggregation

### Docker Deployment (Alternative)

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr poppler-utils libmagic1

# Python dependencies
COPY deployment/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . /app
WORKDIR /app

# Run
CMD ["python", "-m", "client.cli", "serve"]
```

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  extraction-engine:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./documents:/app/documents
      - ./cache:/app/cache
    environment:
      - GOOGLE_CLOUD_PROJECT=${PROJECT_ID}
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
```

---

## Performance & Cost

### Performance Targets

**Single Document:**
- Simple (invoice, 1 page): 3-5 seconds
- Complex (contract, 20 pages): 10-15 seconds
- With tables: +2-5 seconds
- With OCR: +5-10 seconds

**Batch Processing:**
- 10 documents: 30-60 seconds
- 100 documents: 5-10 minutes
- 1000 documents: 50-100 minutes (parallel)

**Throughput:**
- Single instance: 100-200 docs/hour
- 5 instances: 500-1000 docs/hour
- 20 instances: 2000-4000 docs/hour

**Cache Performance:**
- Cache hit: <100ms
- Cache miss: Normal processing time
- Target cache hit rate: 60%+

### Cost Breakdown

**Per Document (Estimated):**
```
Gemini 1.5 Pro:
  - Input: ~2000 tokens × $0.000125 = $0.25
  - Output: ~1000 tokens × $0.000375 = $0.375
  - Total LLM: ~$0.10-0.30

Agent Engine Runtime:
  - Compute: ~$0.05-0.10
  - State management: ~$0.01

Document AI (OCR):
  - Per page: ~$0.015
  - 5 pages: ~$0.075

Storage & Network:
  - GCS: ~$0.005
  - Network: ~$0.005

Total per document: $0.25-0.55
```

**Monthly Cost (1000 docs/day):**
```
30,000 documents/month × $0.40 avg = $12,000/month

Breakdown:
  - LLM costs: ~$6,000-9,000
  - Agent Engine: ~$2,000-3,000
  - Document AI: ~$500-1,500
  - Storage/Network: ~$150
```

**Cost Optimization:**
```
1. Caching (60% hit rate):
   - Saves 40% of LLM costs
   - Saves 30% of runtime costs
   - New cost: ~$8,000/month

2. Gemini 1.5 Flash for simple docs:
   - 50% cheaper than Pro
   - Save ~$2,000/month
   - New cost: ~$6,000/month

3. Batch processing:
   - Better resource utilization
   - 10-15% cost reduction
   - New cost: ~$5,000/month
```

**No Infrastructure Costs:**
- No idle compute charges
- No manual scaling
- No ops overhead
- Pay only for usage

### Resource Requirements

**Development:**
- 2 Python developers (14 weeks)
- 1 DevOps engineer (part-time)
- Optional: ML engineer (2-4 weeks for optimization)

**Infrastructure (Production):**
- Agent Engine: Auto-scaled (1-20 instances)
- Redis: 8GB memory (~$50/month)
- Cloud Storage: ~1TB ($20/month)
- Cloud SQL: Small instance (~$50/month)

---

## Success Metrics

### Accuracy Targets
- **Structured fields**: >95% accuracy
- **Unstructured content**: >85% accuracy
- **Classification**: >95% accuracy
- **Relationship detection**: >80% accuracy

### Performance Targets
- **Single doc**: <15 seconds (p95)
- **Batch (100 docs)**: <10 minutes
- **Throughput**: 500+ docs/hour
- **Availability**: 99.5%

### Quality Targets
- **Success rate**: >99% (with fallbacks)
- **Completeness**: >90% required fields
- **Confidence**: >0.8 average
- **Schema compliance**: 100%

### User Experience
- **Setup time**: <5 minutes
- **First extraction**: <1 minute
- **Learning curve**: <30 minutes
- **Documentation**: Complete

---

## Next Steps

### Immediate (Week 1)
1. Set up Vertex AI project
2. Enable required APIs
3. Create GCS buckets
4. Begin Phase 1 implementation

### Short-term (Weeks 2-4)
1. Complete Phase 1-2
2. Deploy first working agent
3. Test with real documents
4. Iterate on accuracy

### Medium-term (Weeks 5-10)
1. Complete all phases
2. Add all document types
3. Implement all features
4. Performance optimization

### Long-term (Weeks 11-14)
1. Production deployment
2. User testing
3. Documentation
4. Launch

---

## References

### Documentation
- [Vertex AI Agent Engine](https://cloud.google.com/vertex-ai/docs/agent-engine)
- [Google ADK](https://google.github.io/adk-docs/)
- [Document AI](https://cloud.google.com/document-ai/docs)
- [Model Context Protocol](https://modelcontextprotocol.io/)

### Code Repository
- GitHub: `docai-agentic/`
- Main branch: `main`
- Development: `develop`

### Support
- Issues: GitHub Issues
- Questions: Discussions
- Documentation: `/README.md`

---

**Last Updated:** 2026-01-30
**Version:** 1.0.0
**Status:** Planning Complete → Ready for Implementation
