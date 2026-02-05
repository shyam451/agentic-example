"""
Schema Registry

Manages extraction schemas with support for inheritance and validation.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from copy import deepcopy

logger = logging.getLogger(__name__)


class SchemaRegistry:
    """
    Registry for extraction schemas.

    Supports:
    - Auto-loading built-in schemas (invoice, agreement, kyc)
    - Schema inheritance with 'extends' field
    - Schema validation
    - Custom schema registration

    Usage:
        registry = SchemaRegistry()

        # Get built-in schema
        invoice_schema = registry.get_schema('invoice')

        # Register custom schema
        registry.register_schema('receipt', receipt_schema)

        # Register schema that extends another
        registry.register_schema('enhanced_invoice', custom_schema, extends='invoice')
    """

    # Built-in schema names
    BUILTIN_SCHEMAS = ['invoice', 'agreement', 'kyc']

    def __init__(self, schemas_dir: Optional[str] = None):
        """
        Initialize schema registry.

        Args:
            schemas_dir: Path to schemas directory. If None, auto-detects.
        """
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._schemas_dir = self._resolve_schemas_dir(schemas_dir)

        # Auto-load built-in schemas
        self._load_builtin_schemas()

    def _resolve_schemas_dir(self, schemas_dir: Optional[str]) -> Path:
        """Resolve schemas directory path."""
        if schemas_dir:
            return Path(schemas_dir)

        # Try to find relative to this file
        module_dir = Path(__file__).parent.parent.parent
        return module_dir / 'schemas'

    def _load_builtin_schemas(self):
        """Load built-in schemas from disk."""
        for name in self.BUILTIN_SCHEMAS:
            schema_path = self._schemas_dir / f'{name}.json'

            if schema_path.exists():
                try:
                    with open(schema_path, 'r') as f:
                        schema = json.load(f)
                    self._schemas[name] = schema
                    logger.debug(f"Loaded built-in schema: {name}")
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Failed to load schema {name}: {e}")
            else:
                logger.debug(f"Built-in schema not found: {schema_path}")

    def register_schema(
        self,
        name: str,
        schema: Dict[str, Any],
        extends: Optional[str] = None
    ) -> None:
        """
        Register a schema.

        Args:
            name: Schema identifier
            schema: JSON schema dictionary
            extends: Optional parent schema to inherit from
        """
        if extends:
            if extends not in self._schemas:
                raise ValueError(f"Parent schema '{extends}' not found")

            # Merge with parent schema
            parent = deepcopy(self._schemas[extends])
            schema = self._merge_schemas(parent, schema)

        self._schemas[name] = schema
        logger.info(f"Registered schema: {name}" + (f" (extends {extends})" if extends else ""))

    def _merge_schemas(
        self,
        parent: Dict[str, Any],
        child: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge child schema into parent schema.

        Child properties override parent properties.
        Required fields are combined.
        """
        result = deepcopy(parent)

        # Merge properties
        if 'properties' in child:
            if 'properties' not in result:
                result['properties'] = {}
            result['properties'].update(child['properties'])

        # Combine required fields
        if 'required' in child:
            parent_required = set(result.get('required', []))
            child_required = set(child['required'])
            result['required'] = list(parent_required | child_required)

        # Merge definitions
        if 'definitions' in child:
            if 'definitions' not in result:
                result['definitions'] = {}
            result['definitions'].update(child['definitions'])

        # Override other fields
        for key in ['title', 'description', '$id']:
            if key in child:
                result[key] = child[key]

        return result

    def get_schema(self, name: str) -> Dict[str, Any]:
        """
        Get schema by name.

        Args:
            name: Schema identifier

        Returns:
            Schema dictionary

        Raises:
            KeyError: If schema not found
        """
        if name not in self._schemas:
            # Try to load from custom schemas directory
            custom_path = self._schemas_dir / 'custom' / f'{name}.json'
            if custom_path.exists():
                with open(custom_path, 'r') as f:
                    self._schemas[name] = json.load(f)
            else:
                raise KeyError(f"Schema not found: {name}")

        return deepcopy(self._schemas[name])

    def has_schema(self, name: str) -> bool:
        """Check if schema exists."""
        if name in self._schemas:
            return True

        # Check custom schemas directory
        custom_path = self._schemas_dir / 'custom' / f'{name}.json'
        return custom_path.exists()

    def list_schemas(self) -> List[str]:
        """List all registered schema names."""
        schemas = set(self._schemas.keys())

        # Include custom schemas from disk
        custom_dir = self._schemas_dir / 'custom'
        if custom_dir.exists():
            for path in custom_dir.glob('*.json'):
                schemas.add(path.stem)

        return sorted(schemas)

    def validate_against_schema(
        self,
        data: Dict[str, Any],
        schema_name: str
    ) -> Dict[str, Any]:
        """
        Validate data against a schema.

        Args:
            data: Data to validate
            schema_name: Schema to validate against

        Returns:
            Validation result with is_valid, errors, and warnings
        """
        try:
            import jsonschema
        except ImportError:
            logger.warning("jsonschema not installed, skipping validation")
            return {'is_valid': True, 'errors': [], 'warnings': []}

        schema = self.get_schema(schema_name)

        validator = jsonschema.Draft7Validator(schema)
        errors = list(validator.iter_errors(data))

        return {
            'is_valid': len(errors) == 0,
            'errors': [e.message for e in errors if e.validator in ['required', 'type']],
            'warnings': [e.message for e in errors if e.validator not in ['required', 'type']]
        }

    def load_schema_from_path(self, path: str) -> Dict[str, Any]:
        """
        Load schema from file path.

        Args:
            path: Path to schema JSON file

        Returns:
            Schema dictionary
        """
        schema_path = Path(path)

        if not schema_path.is_absolute():
            # Resolve relative to schemas directory
            schema_path = self._schemas_dir / path

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {path}")

        with open(schema_path, 'r') as f:
            return json.load(f)
