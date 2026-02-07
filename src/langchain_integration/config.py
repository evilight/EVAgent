"""
LangChain configuration for EVAgent RAG system.

This module provides configuration loading and management
for LangChain integration components.
"""

from typing import Any, Dict, Optional
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)


class LangChainConfig:
    """
    Configuration manager for LangChain integration.
    
    Handles loading and validation of configuration for:
    - LLM settings (provider, model, temperature, etc.)
    - RAG chain settings (prompts, search parameters)
    - Vector store settings
    """
    
    DEFAULT_CONFIG = {
        'llm': {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'temperature': 0.7,
            'max_tokens': 2000,
            'api_key': None  # Will use OPENAI_API_KEY env var
        },
        'rag': {
            'search_k': 5,
            'similarity_threshold': 0.7,
            'system_prompt': None,  # Use default
            'qa_prompt': None  # Use default
        },
        'retrieval': {
            'default_filters': None,
            'max_context_length': 4000
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize LangChain configuration.
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        logger.info("LangChainConfig initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file or use defaults.
        
        Returns:
            Configuration dictionary
        """
        config = self.DEFAULT_CONFIG.copy()
        
        if self.config_path and Path(self.config_path).exists():
            try:
                with open(self.config_path, 'r') as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        # Merge with defaults
                        config.update(file_config)
                logger.info(f"Loaded config from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")
        
        return config
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration."""
        return self.config.get('llm', self.DEFAULT_CONFIG['llm'])
    
    def get_rag_config(self) -> Dict[str, Any]:
        """Get RAG chain configuration."""
        return self.config.get('rag', self.DEFAULT_CONFIG['rag'])
    
    def get_retrieval_config(self) -> Dict[str, Any]:
        """Get retrieval configuration."""
        return self.config.get('retrieval', self.DEFAULT_CONFIG['retrieval'])
    
    def update_config(self, section: str, updates: Dict[str, Any]) -> None:
        """
        Update a configuration section.
        
        Args:
            section: Configuration section name
            updates: Dictionary of updates
        """
        if section in self.config:
            self.config[section].update(updates)
        else:
            self.config[section] = updates
        
        logger.info(f"Updated config section: {section}")


def create_default_config_file(path: str = "config/langchain_config.yaml") -> None:
    """
    Create a default configuration file.
    
    Args:
        path: Path where to create the config file
    """
    config_content = """# LangChain Configuration for EVAgent RAG System

# LLM Settings
llm:
  provider: openai
  model: gpt-3.5-turbo
  temperature: 0.7
  max_tokens: 2000
  # api_key: set via OPENAI_API_KEY environment variable

# RAG Chain Settings
rag:
  search_k: 5
  similarity_threshold: 0.7
  # system_prompt: custom system prompt (optional)
  # qa_prompt: custom QA prompt (optional)

# Retrieval Settings
retrieval:
  max_context_length: 4000
  # default_filters:
  #   source: jira
"""
    
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w') as f:
        f.write(config_content)
    
    logger.info(f"Created default config file: {path}")
