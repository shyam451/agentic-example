"""
Config Validator

Validates YAML configuration files against JSON Schema at load time.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import yaml

try:
    import jsonschema
    from jsonschema import Draft7Validator, ValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    def __init__(self, message: str, errors: List[str] = None):
        super().__init__(message)
        self.errors = errors or []


class ConfigValidator:
    """
    Validates YAML configuration files against JSON Schema.

    Usage:
        validator = ConfigValidator()
        validator.validate_config('config/custom_agents.yaml')
        # Raises ConfigValidationError if invalid

        # Or get errors as list:
        errors = validator.get_validation_errors('config/custom_agents.yaml')
    """

    # Default schema path relative to project root
    DEFAULT_SCHEMA_PATH = 'schemas/config/custom_agent_config.schema.json'

    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize validator with schema.

        Args:
            schema_path: Path to JSON Schema file. If None, uses default.
        """
        self._schema: Optional[Dict[str, Any]] = None
        self._schema_path = schema_path

        if not HAS_JSONSCHEMA:
            logger.warning("jsonschema package not installed. Validation will be skipped.")

    def _load_schema(self) -> Dict[str, Any]:
        """Load JSON Schema from file."""
        if self._schema is not None:
            return self._schema

        # Determine schema path
        if self._schema_path:
            schema_path = Path(self._schema_path)
        else:
            # Try to find schema relative to this file
            module_dir = Path(__file__).parent.parent.parent
            schema_path = module_dir / self.DEFAULT_SCHEMA_PATH

        if not schema_path.exists():
            raise ConfigValidationError(
                f"Schema file not found: {schema_path}"
            )

        with open(schema_path, 'r') as f:
            self._schema = json.load(f)

        return self._schema

    def _load_yaml(self, yaml_path: str) -> Dict[str, Any]:
        """Load YAML configuration file."""
        path = Path(yaml_path)

        if not path.exists():
            raise ConfigValidationError(f"Config file not found: {yaml_path}")

        with open(path, 'r') as f:
            try:
                return yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                raise ConfigValidationError(f"Invalid YAML syntax: {e}")

    def validate_config(self, yaml_path: str) -> Dict[str, Any]:
        """
        Validate YAML config against schema.

        Args:
            yaml_path: Path to YAML configuration file

        Returns:
            Parsed configuration dict if valid

        Raises:
            ConfigValidationError: If validation fails
        """
        config = self._load_yaml(yaml_path)

        if not HAS_JSONSCHEMA:
            logger.warning("Skipping schema validation (jsonschema not installed)")
            return config

        schema = self._load_schema()

        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(config))

        if errors:
            error_messages = self._format_errors(errors)
            raise ConfigValidationError(
                f"Configuration validation failed with {len(errors)} error(s)",
                errors=error_messages
            )

        logger.info(f"Configuration validated successfully: {yaml_path}")
        return config

    def get_validation_errors(self, yaml_path: str) -> List[str]:
        """
        Get list of validation errors without raising exception.

        Args:
            yaml_path: Path to YAML configuration file

        Returns:
            List of error messages (empty if valid)
        """
        try:
            config = self._load_yaml(yaml_path)
        except ConfigValidationError as e:
            return [str(e)]

        if not HAS_JSONSCHEMA:
            return []

        try:
            schema = self._load_schema()
        except ConfigValidationError as e:
            return [str(e)]

        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(config))

        return self._format_errors(errors)

    def _format_errors(self, errors: List['ValidationError']) -> List[str]:
        """Format validation errors into readable messages."""
        messages = []

        for error in errors:
            # Build path to error location
            path = ' → '.join(str(p) for p in error.absolute_path) or 'root'

            # Create readable message
            if error.validator == 'required':
                missing = error.message.split("'")[1] if "'" in error.message else error.message
                messages.append(f"Missing required field '{missing}' at {path}")
            elif error.validator == 'pattern':
                messages.append(f"Invalid format at {path}: {error.message}")
            elif error.validator == 'enum':
                messages.append(f"Invalid value at {path}: {error.message}")
            elif error.validator == 'minLength':
                messages.append(f"Value too short at {path}: {error.message}")
            else:
                messages.append(f"Validation error at {path}: {error.message}")

        return messages

    def is_valid(self, yaml_path: str) -> bool:
        """
        Check if configuration is valid.

        Args:
            yaml_path: Path to YAML configuration file

        Returns:
            True if valid, False otherwise
        """
        errors = self.get_validation_errors(yaml_path)
        return len(errors) == 0
