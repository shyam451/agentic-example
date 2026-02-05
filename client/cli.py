"""
Command Line Interface for Document Extraction Engine

Provides low-code CLI for document extraction.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from client.client import ExtractionClient

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def extract_command(args):
    """Handle extract command"""
    logger.info(f"Extracting from: {args.source}")

    # Initialize client
    client = ExtractionClient(
        endpoint_name=args.endpoint,
        project_id=args.project,
        region=args.region
    )

    # Handle single file or directory
    source_path = Path(args.source)

    if source_path.is_file():
        # Single document extraction
        result = client.extract_document(
            str(source_path),
            custom_prompts=args.prompt,
            document_type=args.type
        )

        # Save or print results
        if args.output:
            client.save_results(result, args.output, args.format)
        else:
            print(json.dumps(result, indent=2))

    elif source_path.is_dir():
        # Batch extraction
        # Find all documents in directory
        patterns = args.pattern or ['*.pdf', '*.png', '*.jpg', '*.docx']
        document_paths = []

        for pattern in patterns:
            document_paths.extend(source_path.glob(pattern))

        if not document_paths:
            logger.error(f"No documents found in {source_path}")
            return 1

        logger.info(f"Found {len(document_paths)} documents")

        # Extract batch
        results = client.extract_batch(
            [str(p) for p in document_paths],
            enable_relationships=args.enable_relationships,
            cross_document_queries=args.query
        )

        # Save or print results
        if args.output:
            client.save_results(results, args.output, args.format)
        else:
            print(json.dumps(results, indent=2))

    else:
        logger.error(f"Source not found: {args.source}")
        return 1

    logger.info("✅ Extraction complete")
    return 0


def configure_command(args):
    """Handle configure command"""
    import os

    logger.info("Configuring extraction engine...")

    # Save configuration
    config = {
        'project_id': args.project,
        'region': args.region,
        'endpoint': args.endpoint
    }

    # Save to config file
    config_dir = Path.home() / '.docai'
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / 'config.json'

    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    logger.info(f"✅ Configuration saved to {config_file}")
    logger.info(f"Project: {args.project}")
    logger.info(f"Region: {args.region}")
    logger.info(f"Endpoint: {args.endpoint}")

    return 0


def deploy_command(args):
    """Handle deploy command"""
    from deployment.deploy import AgentEngineDeployer

    logger.info("Deploying to Vertex AI Agent Engine...")

    deployer = AgentEngineDeployer(
        project_id=args.project,
        region=args.region,
        config_path=args.config
    )

    deployment_info = deployer.deploy(bucket_name=args.bucket)

    logger.info("✅ Deployment complete!")
    logger.info(f"Endpoint: {deployment_info['endpoint_url']}")

    return 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        prog='docai',
        description='Document Extraction Engine - Extract structured data from documents using AI'
    )

    # Global options
    parser.add_argument('--project', help='Google Cloud project ID')
    parser.add_argument('--region', default='us-central1', help='GCP region')
    parser.add_argument('--endpoint', help='Agent Engine endpoint name')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Extract command
    extract_parser = subparsers.add_parser(
        'extract',
        help='Extract data from documents'
    )
    extract_parser.add_argument(
        'source',
        help='Document file or directory to extract from'
    )
    extract_parser.add_argument(
        '--type',
        choices=['invoice', 'agreement', 'kyc', 'auto'],
        default='auto',
        help='Document type hint'
    )
    extract_parser.add_argument(
        '--prompt',
        action='append',
        help='Custom extraction prompt (can be used multiple times)'
    )
    extract_parser.add_argument(
        '--output', '-o',
        help='Output file path'
    )
    extract_parser.add_argument(
        '--format',
        choices=['json', 'yaml', 'csv'],
        default='json',
        help='Output format'
    )
    extract_parser.add_argument(
        '--enable-relationships',
        action='store_true',
        help='Enable cross-document relationship detection'
    )
    extract_parser.add_argument(
        '--query',
        action='append',
        help='Cross-document query (can be used multiple times)'
    )
    extract_parser.add_argument(
        '--pattern',
        action='append',
        help='File pattern for directory extraction (default: *.pdf, *.png, *.jpg, *.docx)'
    )
    extract_parser.set_defaults(func=extract_command)

    # Configure command
    config_parser = subparsers.add_parser(
        'configure',
        help='Configure extraction engine'
    )
    config_parser.add_argument('--project', required=True, help='Google Cloud project ID')
    config_parser.add_argument('--region', default='us-central1', help='GCP region')
    config_parser.add_argument('--endpoint', required=True, help='Agent Engine endpoint')
    config_parser.set_defaults(func=configure_command)

    # Deploy command
    deploy_parser = subparsers.add_parser(
        'deploy',
        help='Deploy to Vertex AI Agent Engine'
    )
    deploy_parser.add_argument('--project', required=True, help='Google Cloud project ID')
    deploy_parser.add_argument('--region', default='us-central1', help='GCP region')
    deploy_parser.add_argument('--config', default='config/agent_config.yaml', help='Agent config file')
    deploy_parser.add_argument('--bucket', help='GCS bucket for schemas')
    deploy_parser.set_defaults(func=deploy_command)

    # Parse arguments
    args = parser.parse_args()

    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Execute command
    if hasattr(args, 'func'):
        try:
            return args.func(args)
        except Exception as e:
            logger.error(f"Error: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
            return 1
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
