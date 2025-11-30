import os
import yaml
import docker
import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file with environment variable substitution.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dictionary containing configuration
    """

    with open(config_path, 'r') as f:
        config_str = f.read()
    
    # Replace environment variables
    for key, value in os.environ.items():
        config_str = config_str.replace(f"${{{key}}}", value)
    
    config = yaml.safe_load(config_str)
    return config


def setup_logging(config: Dict[str, Any]) -> None:
    """
    Setup logging based on configuration.
    
    Args:
        config: Configuration dictionary
    """
    log_config = config.get('logging', {})
    level = getattr(logging, log_config.get('level', 'INFO'))
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = log_config.get('file', 'wordpress_manager.log')
    
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )


def get_llm_from_config(config: Dict[str, Any]):
    """
    Initialize LLM based on configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        LangChain LLM instance
    """
    llm_config = config['llm']
    provider = llm_config['provider'].lower()
    
    if provider == 'anthropic':
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=llm_config['model'],
            temperature=llm_config['temperature'],
            max_tokens=llm_config['max_tokens'],
            api_key=llm_config.get('api_key') or os.getenv('ANTHROPIC_API_KEY')
        )
    elif provider == 'openai':
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=llm_config['model'],
            temperature=llm_config['temperature'],
            max_tokens=llm_config['max_tokens'],
            api_key=llm_config.get('api_key') or os.getenv('OPENAI_API_KEY')
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
