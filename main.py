#!/usr/bin/env python3
import sys
import argparse
import logging
from pathlib import Path
from colorama import Fore, Style, init
from utils import load_config, setup_logging, get_llm_from_config
from Agents.orchestrator_agent import OrchestratorAgent

# Initialize colorama for colored output
init(autoreset=True)

logger = logging.getLogger(__name__)


def print_success(message: str):
    """Print success message."""
    print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")


def print_error(message: str):
    """Print error message."""
    print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")


def print_info(message: str):
    """Print info message."""
    print(f"{Fore.YELLOW}ℹ {message}{Style.RESET_ALL}")


def validate_requirements():
    """Validate that required tools are installed."""
    import shutil
    
    requirements = {
        'docker': 'Docker',
        'docker-compose': 'Docker Compose'
    }
    
    missing = []
    for cmd, name in requirements.items():
        if not shutil.which(cmd):
            missing.append(name)
    
    if missing:
        print_error(f"Missing required tools: {', '.join(missing)}")
        print_info("Please install Docker and Docker Compose before running this application.")
        return False
    
    return True


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description='WordPress Multi-Agent Manager - AI-powered WordPress installation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
                Examples:
                %(prog)s install                    # Install WordPress
                %(prog)s update                     # Update existing installation
                %(prog)s validate                   # Validate current installation
                %(prog)s install --config my.yaml  # Use custom configuration file
                """
    )
    
    parser.add_argument(
        'command',
        choices=['install', 'update', 'validate'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    try:        
        # Validate requirements
        print_info("Validating system requirements...")
        if not validate_requirements():
            return 1
        print_success("System requirements validated")
        
        # Load configuration
        print_info(f"Loading configuration from {args.config}...")
        if not Path(args.config).exists():
            print_error(f"Configuration file not found: {args.config}")
            return 1
        
        config = load_config(args.config)
        
        # Override verbosity if specified
        if args.verbose:
            config['agents']['verbose'] = True
            config['logging']['level'] = 'DEBUG'
        
        print_success("Configuration loaded")
        
        # Setup logging
        setup_logging(config)
        logger.info(f"Starting WordPress Manager - Command: {args.command}")
        
        # Initialize LLM
        print_info("Initializing AI language model...")
        try:
            llm = get_llm_from_config(config)
            print_success("AI model initialized")
        except Exception as e:
            print_error(f"Failed to initialize AI model: {str(e)}")
            print_info("Please check your API key in the configuration or environment variables.")
            return 1
        
        # Create orchestrator agent
        print_info("Creating orchestrator agent...")
        orchestrator = OrchestratorAgent(llm, config)
        print_success("Orchestrator agent ready")
        
        # Execute command
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Executing: {args.command.upper()}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
        
        result = orchestrator.run(args.command)
        
        # Print results
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}RESULTS{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
        
        if result['status'] == 'success':
            print_success(f"Command '{args.command}' completed successfully!")
            print(f"\n{Fore.WHITE}{result['output']}{Style.RESET_ALL}\n")
            
            # Print access information
            wp_port = config['wordpress']['port']
            print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}WordPress is now accessible at:{Style.RESET_ALL}")
            print(f"{Fore.GREEN}http://localhost:{wp_port}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}\n")
            
            return 0
        else:
            print_error(f"Command '{args.command}' failed!")
            print(f"\n{Fore.RED}Error: {result.get('error', 'Unknown error')}{Style.RESET_ALL}\n")
            return 1
    
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Operation cancelled by user.{Style.RESET_ALL}")
        return 130
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        logger.exception("Unexpected error occurred")
        return 1


if __name__ == '__main__':
    sys.exit(main())
