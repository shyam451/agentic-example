"""
Document Preprocessor Tools

Handles extraction and decomposition of container documents:
- ZIP/RAR/TAR archives
- Email messages (EML, MSG)
- PDF portfolios with embedded documents
- Tracks parent-child document lineage
"""

import logging
import os
import tempfile
import zipfile
import tarfile
import email
from email import policy
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import uuid
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class DocumentLineage:
    """Tracks parent-child relationships for extracted documents."""
    document_id: str
    original_path: str
    extracted_path: str
    parent_id: Optional[str] = None
    container_type: str = "root"  # root, archive, email, pdf_portfolio
    extraction_depth: int = 0
    file_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PreprocessorResult:
    """Result of preprocessing operation."""
    documents: List[str]  # List of document paths ready for processing
    lineage: Dict[str, DocumentLineage]  # document_id -> lineage info
    total_extracted: int
    original_count: int
    errors: List[Dict[str, Any]]
    processing_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "documents": self.documents,
            "lineage": {k: v.to_dict() for k, v in self.lineage.items()},
            "total_extracted": self.total_extracted,
            "original_count": self.original_count,
            "errors": self.errors,
            "processing_time_ms": self.processing_time_ms
        }


# ---------- Tool Functions (called by Orchestrator) ----------

def preprocess_document(
    document_path: str,
    max_depth: int = 3,
    temp_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main preprocessing entry point - detects container type and extracts nested documents.

    This is the primary tool function called by the orchestrator before classification.

    Args:
        document_path: Path to document (may be container like ZIP, email, etc.)
        max_depth: Maximum recursion depth for nested containers
        temp_dir: Directory for extracted files (uses system temp if None)

    Returns:
        PreprocessorResult as dictionary with:
        - documents: List of paths to process
        - lineage: Parent-child relationship tracking
        - total_extracted: Count of extracted documents
        - errors: Any extraction errors
    """
    logger.info(f"Preprocessing document: {document_path}")
    start_time = datetime.now()

    try:
        preprocessor = DocumentPreprocessor(temp_dir=temp_dir, max_depth=max_depth)
        result = preprocessor.process(document_path)

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        result.processing_time_ms = elapsed_ms

        logger.info(f"Preprocessing complete: {result.total_extracted} documents extracted in {elapsed_ms:.2f}ms")
        return result.to_dict()

    except Exception as e:
        logger.error(f"Preprocessing failed: {e}")
        # Return original document as fallback
        return {
            "documents": [document_path],
            "lineage": {},
            "total_extracted": 1,
            "original_count": 1,
            "errors": [{"path": document_path, "error": str(e)}],
            "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000
        }


def preprocess_documents(
    document_paths: List[str],
    max_depth: int = 3,
    temp_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Preprocess multiple documents, extracting nested documents from containers.

    Args:
        document_paths: List of document paths to preprocess
        max_depth: Maximum recursion depth for nested containers
        temp_dir: Directory for extracted files

    Returns:
        Combined preprocessing result with all extracted documents
    """
    logger.info(f"Preprocessing {len(document_paths)} documents")
    start_time = datetime.now()

    all_documents = []
    all_lineage = {}
    all_errors = []

    for path in document_paths:
        result = preprocess_document(path, max_depth=max_depth, temp_dir=temp_dir)
        all_documents.extend(result["documents"])
        all_lineage.update(result["lineage"])
        all_errors.extend(result["errors"])

    elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

    return {
        "documents": all_documents,
        "lineage": all_lineage,
        "total_extracted": len(all_documents),
        "original_count": len(document_paths),
        "errors": all_errors,
        "processing_time_ms": elapsed_ms
    }


def extract_archive(
    archive_path: str,
    output_dir: Optional[str] = None,
    parent_lineage: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Extract files from ZIP/RAR/TAR archives.

    Args:
        archive_path: Path to archive file
        output_dir: Output directory for extracted files
        parent_lineage: Lineage info from parent container

    Returns:
        Dictionary with extracted file paths and metadata
    """
    logger.info(f"Extracting archive: {archive_path}")

    extractor = ArchiveExtractor()
    return extractor.extract(archive_path, output_dir, parent_lineage)


def extract_email(
    email_path: str,
    output_dir: Optional[str] = None,
    parent_lineage: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Parse email (EML/MSG) and extract attachments.

    Args:
        email_path: Path to email file (.eml or .msg)
        output_dir: Output directory for attachments
        parent_lineage: Lineage info from parent container

    Returns:
        Dictionary with email metadata, body, and attachment paths
    """
    logger.info(f"Extracting email: {email_path}")

    extractor = EmailExtractor()
    return extractor.extract(email_path, output_dir, parent_lineage)


def extract_pdf_portfolio(
    pdf_path: str,
    output_dir: Optional[str] = None,
    parent_lineage: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Extract embedded documents from PDF portfolios.

    Args:
        pdf_path: Path to PDF portfolio
        output_dir: Output directory for embedded files
        parent_lineage: Lineage info from parent container

    Returns:
        Dictionary with extracted document paths and metadata
    """
    logger.info(f"Extracting PDF portfolio: {pdf_path}")

    extractor = PDFPortfolioExtractor()
    return extractor.extract(pdf_path, output_dir, parent_lineage)


def get_document_lineage(
    document_id: str,
    lineage_map: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Retrieve full lineage chain for a document.

    Args:
        document_id: ID of document to trace
        lineage_map: Full lineage mapping from preprocessing

    Returns:
        Lineage chain from root to document
    """
    chain = []
    current_id = document_id

    while current_id and current_id in lineage_map:
        lineage = lineage_map[current_id]
        chain.insert(0, lineage)
        current_id = lineage.get("parent_id")

    return {
        "document_id": document_id,
        "lineage_chain": chain,
        "depth": len(chain)
    }


def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of file for deduplication."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


# ---------- Implementation Classes ----------

class DocumentPreprocessor:
    """
    Main preprocessor that orchestrates extraction of nested documents.
    """

    CONTAINER_EXTENSIONS = {
        # Archives
        '.zip': 'archive',
        '.rar': 'archive',
        '.7z': 'archive',
        '.tar': 'archive',
        '.gz': 'archive',
        '.tgz': 'archive',
        '.tar.gz': 'archive',
        # Emails
        '.eml': 'email',
        '.msg': 'email',
    }

    def __init__(self, temp_dir: Optional[str] = None, max_depth: int = 3):
        self.temp_dir = temp_dir or tempfile.mkdtemp(prefix="docai_preprocess_")
        self.max_depth = max_depth
        self.lineage: Dict[str, DocumentLineage] = {}
        self.documents: List[str] = []
        self.errors: List[Dict[str, Any]] = []
        self.seen_hashes: set = set()  # For deduplication

    def process(self, document_path: str, depth: int = 0, parent_id: Optional[str] = None) -> PreprocessorResult:
        """Process a document, extracting nested documents if container type."""

        if depth > self.max_depth:
            logger.warning(f"Max depth {self.max_depth} reached, skipping nested extraction: {document_path}")
            self._add_document(document_path, depth, parent_id, "max_depth_reached")
            return self._build_result()

        if not os.path.exists(document_path):
            logger.error(f"Document not found: {document_path}")
            self.errors.append({
                "path": document_path,
                "error": "File not found",
                "depth": depth
            })
            return self._build_result()

        # Generate document ID
        doc_id = str(uuid.uuid4())[:8]

        # Compute file hash for deduplication
        try:
            file_hash = compute_file_hash(document_path)
            if file_hash in self.seen_hashes:
                logger.info(f"Skipping duplicate document: {document_path}")
                return self._build_result()
            self.seen_hashes.add(file_hash)
        except Exception as e:
            logger.warning(f"Could not compute hash for {document_path}: {e}")
            file_hash = None

        # Detect container type
        container_type = self._detect_container_type(document_path)

        # Create lineage entry
        lineage = DocumentLineage(
            document_id=doc_id,
            original_path=document_path,
            extracted_path=document_path,
            parent_id=parent_id,
            container_type=container_type or "document",
            extraction_depth=depth,
            file_hash=file_hash,
            metadata={
                "file_size": os.path.getsize(document_path),
                "file_name": os.path.basename(document_path),
                "extension": Path(document_path).suffix.lower()
            }
        )
        self.lineage[doc_id] = lineage

        # Update parent's children list
        if parent_id and parent_id in self.lineage:
            self.lineage[parent_id].children.append(doc_id)

        if container_type:
            # Extract nested documents
            try:
                extracted = self._extract_container(document_path, container_type, doc_id)

                # Recursively process extracted documents
                for extracted_path in extracted:
                    self.process(extracted_path, depth + 1, doc_id)

            except Exception as e:
                logger.error(f"Error extracting {document_path}: {e}")
                self.errors.append({
                    "path": document_path,
                    "error": str(e),
                    "container_type": container_type,
                    "depth": depth
                })
                # Still add container as processable document (might have text content)
                self.documents.append(document_path)
        else:
            # Regular document, add to processing queue
            self.documents.append(document_path)

        return self._build_result()

    def _detect_container_type(self, path: str) -> Optional[str]:
        """Detect if document is a container type."""
        path_lower = path.lower()

        # Check for compound extensions first
        for ext, container_type in self.CONTAINER_EXTENSIONS.items():
            if path_lower.endswith(ext):
                return container_type

        # Check for PDF portfolio
        if path_lower.endswith('.pdf'):
            if self._is_pdf_portfolio(path):
                return 'pdf_portfolio'

        return None

    def _is_pdf_portfolio(self, path: str) -> bool:
        """Check if PDF is a portfolio with embedded files."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(path)
            has_embedded = doc.embfile_count() > 0
            doc.close()
            return has_embedded
        except ImportError:
            logger.debug("PyMuPDF not available for PDF portfolio detection")
            return False
        except Exception as e:
            logger.debug(f"Could not check PDF portfolio: {e}")
            return False

    def _extract_container(self, path: str, container_type: str, parent_id: str) -> List[str]:
        """Extract documents from container."""
        output_dir = os.path.join(self.temp_dir, parent_id)
        os.makedirs(output_dir, exist_ok=True)

        if container_type == 'archive':
            result = extract_archive(path, output_dir)
            return result.get('extracted_files', [])

        elif container_type == 'email':
            result = extract_email(path, output_dir)
            return result.get('attachments', [])

        elif container_type == 'pdf_portfolio':
            result = extract_pdf_portfolio(path, output_dir)
            return result.get('embedded_files', [])

        return []

    def _add_document(self, path: str, depth: int, parent_id: Optional[str], note: str):
        """Add a document without further processing."""
        doc_id = str(uuid.uuid4())[:8]
        lineage = DocumentLineage(
            document_id=doc_id,
            original_path=path,
            extracted_path=path,
            parent_id=parent_id,
            container_type="document",
            extraction_depth=depth,
            metadata={"note": note}
        )
        self.lineage[doc_id] = lineage
        self.documents.append(path)

    def _build_result(self) -> PreprocessorResult:
        return PreprocessorResult(
            documents=self.documents,
            lineage=self.lineage,
            total_extracted=len(self.documents),
            original_count=1,  # Will be updated by caller for batches
            errors=self.errors
        )


class ArchiveExtractor:
    """Extract files from ZIP, RAR, TAR, and other archive formats."""

    # Files to skip during extraction
    SKIP_PATTERNS = [
        '__MACOSX',
        '.DS_Store',
        'Thumbs.db',
        '~$',  # Office temp files
    ]

    def extract(
        self,
        archive_path: str,
        output_dir: Optional[str] = None,
        parent_lineage: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract archive contents."""

        output_dir = output_dir or tempfile.mkdtemp(prefix="archive_")
        os.makedirs(output_dir, exist_ok=True)

        extracted_files = []
        errors = []

        ext = Path(archive_path).suffix.lower()
        # Handle compound extensions
        if archive_path.lower().endswith('.tar.gz'):
            ext = '.tar.gz'

        try:
            if ext == '.zip':
                extracted_files = self._extract_zip(archive_path, output_dir)
            elif ext == '.rar':
                extracted_files = self._extract_rar(archive_path, output_dir)
            elif ext in ['.tar', '.gz', '.tgz', '.tar.gz']:
                extracted_files = self._extract_tar(archive_path, output_dir)
            elif ext == '.7z':
                extracted_files = self._extract_7z(archive_path, output_dir)
            else:
                errors.append(f"Unsupported archive format: {ext}")

        except Exception as e:
            logger.error(f"Archive extraction error: {e}")
            errors.append(str(e))

        return {
            'extracted_files': extracted_files,
            'output_dir': output_dir,
            'file_count': len(extracted_files),
            'archive_path': archive_path,
            'errors': errors,
            'parent_lineage': parent_lineage
        }

    def _should_skip(self, filename: str) -> bool:
        """Check if file should be skipped."""
        for pattern in self.SKIP_PATTERNS:
            if pattern in filename:
                return True
        return False

    def _extract_zip(self, path: str, output_dir: str) -> List[str]:
        """Extract ZIP archive."""
        extracted = []
        with zipfile.ZipFile(path, 'r') as zf:
            for member in zf.namelist():
                # Skip directories and unwanted files
                if member.endswith('/') or self._should_skip(member):
                    continue

                # Extract file
                try:
                    extracted_path = zf.extract(member, output_dir)
                    extracted.append(extracted_path)
                    logger.debug(f"Extracted: {member}")
                except Exception as e:
                    logger.warning(f"Failed to extract {member}: {e}")

        return extracted

    def _extract_rar(self, path: str, output_dir: str) -> List[str]:
        """Extract RAR archive."""
        try:
            import rarfile
            extracted = []
            with rarfile.RarFile(path) as rf:
                for member in rf.namelist():
                    if member.endswith('/') or self._should_skip(member):
                        continue
                    rf.extract(member, output_dir)
                    extracted.append(os.path.join(output_dir, member))
            return extracted
        except ImportError:
            logger.warning("rarfile package not installed, RAR extraction unavailable")
            return []

    def _extract_tar(self, path: str, output_dir: str) -> List[str]:
        """Extract TAR/GZ archive."""
        extracted = []
        mode = 'r:*'  # Auto-detect compression

        with tarfile.open(path, mode) as tf:
            for member in tf.getmembers():
                if not member.isfile() or self._should_skip(member.name):
                    continue

                try:
                    tf.extract(member, output_dir)
                    extracted.append(os.path.join(output_dir, member.name))
                except Exception as e:
                    logger.warning(f"Failed to extract {member.name}: {e}")

        return extracted

    def _extract_7z(self, path: str, output_dir: str) -> List[str]:
        """Extract 7z archive."""
        try:
            import py7zr
            extracted = []
            with py7zr.SevenZipFile(path, mode='r') as archive:
                archive.extractall(path=output_dir)
                # Get list of extracted files
                for name in archive.getnames():
                    full_path = os.path.join(output_dir, name)
                    if os.path.isfile(full_path) and not self._should_skip(name):
                        extracted.append(full_path)
            return extracted
        except ImportError:
            logger.warning("py7zr package not installed, 7z extraction unavailable")
            return []


class EmailExtractor:
    """Extract email metadata and attachments from EML/MSG files."""

    def extract(
        self,
        email_path: str,
        output_dir: Optional[str] = None,
        parent_lineage: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract email content and attachments."""

        output_dir = output_dir or tempfile.mkdtemp(prefix="email_")
        os.makedirs(output_dir, exist_ok=True)

        ext = Path(email_path).suffix.lower()

        if ext == '.eml':
            return self._extract_eml(email_path, output_dir, parent_lineage)
        elif ext == '.msg':
            return self._extract_msg(email_path, output_dir, parent_lineage)
        else:
            return {
                'error': f'Unsupported email format: {ext}',
                'attachments': [],
                'email_path': email_path
            }

    def _extract_eml(
        self,
        path: str,
        output_dir: str,
        parent_lineage: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract from EML file."""

        with open(path, 'rb') as f:
            msg = email.message_from_binary_file(f, policy=policy.default)

        attachments = []
        inline_images = []

        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue

            filename = part.get_filename()
            content_disposition = str(part.get('Content-Disposition', ''))

            if filename:
                # Sanitize filename
                safe_filename = self._sanitize_filename(filename)
                attachment_path = os.path.join(output_dir, safe_filename)

                # Handle duplicate filenames
                attachment_path = self._get_unique_path(attachment_path)

                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        with open(attachment_path, 'wb') as f:
                            f.write(payload)
                        attachments.append(attachment_path)
                        logger.debug(f"Extracted attachment: {safe_filename}")
                except Exception as e:
                    logger.warning(f"Failed to extract attachment {filename}: {e}")

            elif 'inline' in content_disposition and part.get_content_type().startswith('image/'):
                # Handle inline images
                content_id = part.get('Content-ID', '')
                ext = part.get_content_type().split('/')[-1]
                inline_name = f"inline_{len(inline_images)}.{ext}"
                inline_path = os.path.join(output_dir, inline_name)

                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        with open(inline_path, 'wb') as f:
                            f.write(payload)
                        inline_images.append(inline_path)
                except Exception as e:
                    logger.warning(f"Failed to extract inline image: {e}")

        return {
            'subject': msg.get('subject', ''),
            'from': msg.get('from', ''),
            'to': msg.get('to', ''),
            'cc': msg.get('cc', ''),
            'date': msg.get('date', ''),
            'message_id': msg.get('message-id', ''),
            'body': self._get_email_body(msg),
            'attachments': attachments,
            'inline_images': inline_images,
            'attachment_count': len(attachments),
            'email_path': path,
            'output_dir': output_dir,
            'parent_lineage': parent_lineage
        }

    def _extract_msg(
        self,
        path: str,
        output_dir: str,
        parent_lineage: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract from Outlook MSG file."""
        try:
            import extract_msg

            msg = extract_msg.Message(path)
            attachments = []

            for attachment in msg.attachments:
                if attachment.longFilename:
                    safe_filename = self._sanitize_filename(attachment.longFilename)
                    attachment_path = os.path.join(output_dir, safe_filename)
                    attachment_path = self._get_unique_path(attachment_path)

                    try:
                        attachment.save(customPath=output_dir, customFilename=safe_filename)
                        attachments.append(attachment_path)
                    except Exception as e:
                        logger.warning(f"Failed to save attachment: {e}")

            return {
                'subject': msg.subject or '',
                'from': msg.sender or '',
                'to': msg.to or '',
                'cc': msg.cc or '',
                'date': str(msg.date) if msg.date else '',
                'body': msg.body or '',
                'attachments': attachments,
                'attachment_count': len(attachments),
                'email_path': path,
                'output_dir': output_dir,
                'parent_lineage': parent_lineage
            }

        except ImportError:
            logger.warning("extract-msg package not installed, MSG extraction unavailable")
            return {
                'error': 'extract-msg package not installed',
                'attachments': [],
                'email_path': path,
                'parent_lineage': parent_lineage
            }

    def _get_email_body(self, msg) -> str:
        """Extract email body text, preferring plain text over HTML."""
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode('utf-8', errors='ignore')
                            break
                    except Exception:
                        continue
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='ignore')
            except Exception:
                pass

        return body

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe filesystem use."""
        # Remove or replace dangerous characters
        dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\x00']
        safe_name = filename
        for char in dangerous_chars:
            safe_name = safe_name.replace(char, '_')
        return safe_name.strip()

    def _get_unique_path(self, path: str) -> str:
        """Get unique path by appending number if file exists."""
        if not os.path.exists(path):
            return path

        base, ext = os.path.splitext(path)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        return f"{base}_{counter}{ext}"


class PDFPortfolioExtractor:
    """Extract embedded files from PDF portfolios."""

    def extract(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None,
        parent_lineage: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract embedded documents from PDF portfolio."""

        output_dir = output_dir or tempfile.mkdtemp(prefix="pdf_portfolio_")
        os.makedirs(output_dir, exist_ok=True)

        embedded_files = []
        errors = []

        try:
            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)

            # Check for embedded files
            if doc.embfile_count() == 0:
                logger.info(f"No embedded files in PDF: {pdf_path}")
                doc.close()
                return {
                    'embedded_files': [],
                    'output_dir': output_dir,
                    'file_count': 0,
                    'pdf_path': pdf_path,
                    'parent_lineage': parent_lineage
                }

            # Extract each embedded file
            for i in range(doc.embfile_count()):
                try:
                    info = doc.embfile_info(i)
                    name = info.get('name', f'embedded_{i}')
                    content = doc.embfile_get(i)

                    # Sanitize filename
                    safe_name = self._sanitize_filename(name)
                    output_path = os.path.join(output_dir, safe_name)
                    output_path = self._get_unique_path(output_path)

                    with open(output_path, 'wb') as f:
                        f.write(content)

                    embedded_files.append(output_path)
                    logger.debug(f"Extracted embedded file: {safe_name}")

                except Exception as e:
                    logger.warning(f"Failed to extract embedded file {i}: {e}")
                    errors.append(str(e))

            doc.close()

        except ImportError:
            logger.warning("PyMuPDF not installed, PDF portfolio extraction unavailable")
            errors.append("PyMuPDF not installed")

        except Exception as e:
            logger.error(f"PDF portfolio extraction error: {e}")
            errors.append(str(e))

        return {
            'embedded_files': embedded_files,
            'output_dir': output_dir,
            'file_count': len(embedded_files),
            'pdf_path': pdf_path,
            'errors': errors,
            'parent_lineage': parent_lineage
        }

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe filesystem use."""
        dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\x00']
        safe_name = filename
        for char in dangerous_chars:
            safe_name = safe_name.replace(char, '_')
        return safe_name.strip()

    def _get_unique_path(self, path: str) -> str:
        """Get unique path by appending number if file exists."""
        if not os.path.exists(path):
            return path

        base, ext = os.path.splitext(path)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        return f"{base}_{counter}{ext}"
