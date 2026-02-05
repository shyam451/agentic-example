"""
Client Module for Document Extraction Engine

Provides Python SDK and CLI for interacting with the deployed Agent Engine.
"""

from client.client import ExtractionClient
from client.cli import main as cli_main

__all__ = ['ExtractionClient', 'cli_main']
