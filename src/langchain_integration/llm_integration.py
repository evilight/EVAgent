"""
LLM Integration for EVAgent RAG system.

This module provides integration with various LLM providers
(OpenAI, Azure OpenAI, etc.) for the RAG pipeline.
"""

from typing import Any, Dict, Optional
import os
import logging
from pathlib import Path

import yaml

from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


def load_openai_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load OpenAI configuration from YAML file.
    
    Args:
        config_path: Path to config file, defaults to config/openai_config.yaml
        
    Returns:
        Configuration dictionary
    """
    if config_path is None:
        # Find project root and default config path
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        config_path = project_root / "config" / "openai_config.yaml"
    else:
        config_path = Path(config_path)
    
    default_config = {
        'api_key': os.getenv('OPENAI_API_KEY', ''),
        'base_url': 'https://api.openai.com/v1',
        'model': 'gpt-3.5-turbo',
        'temperature': 0.7,
        'max_tokens': 2000,
        'timeout': 60,
        'max_retries': 3
    }
    
    if not config_path.exists():
        logger.warning(f"OpenAI config file not found: {config_path}, using defaults")
        return default_config
    
    try:
        with open(config_path, 'r') as f:
            file_config = yaml.safe_load(f)
        
        if file_config and 'openai' in file_config:
            config = file_config['openai']
            
            # Handle environment variable substitution
            for key in ['api_key', 'base_url', 'organization']:
                value = config.get(key, '')
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    env_var = value[2:-1]
                    config[key] = os.getenv(env_var, '')
            
            # Merge with defaults
            default_config.update(config)
            logger.info(f"Loaded OpenAI config from {config_path}")
        
        return default_config
        
    except Exception as e:
        logger.warning(f"Failed to load OpenAI config: {e}, using defaults")
        return default_config


class LLMManager:
    """
    Manager for LLM interactions in the RAG system.
    
    This class handles initialization and configuration of LLM clients,
    supporting multiple providers (OpenAI, Azure, etc.).
    
    Example:
        >>> from src.langchain_integration import LLMManager
        >>> 
        >>> llm_manager = LLMManager()  # Loads from config/openai_config.yaml
        >>> 
        >>> llm = llm_manager.get_llm()
        >>> response = await llm.ainvoke([HumanMessage(content="Hello")])
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the LLM manager.
        
        Args:
            config: Optional configuration dictionary. If not provided,
                   loads from config/openai_config.yaml
        """
        if config is None:
            self.config = load_openai_config()
        else:
            self.config = config
        
        self.provider = self.config.get('provider', 'openai')
        self._llm: Optional[BaseChatModel] = None
        
        logger.info(f"LLMManager initialized with provider: {self.provider}")
    
    def get_llm(self) -> BaseChatModel:
        """
        Get or create the LLM instance.
        
        Returns:
            Configured LLM instance
        """
        if self._llm is None:
            self._llm = self._create_llm()
        
        return self._llm
    
    def _create_llm(self) -> BaseChatModel:
        """
        Create LLM instance based on configuration.
        
        Returns:
            Configured LLM instance
        """
        if self.provider == 'openai':
            return self._create_openai_llm()
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def _create_openai_llm(self) -> ChatOpenAI:
        """
        Create OpenAI LLM instance.
        
        Returns:
            ChatOpenAI instance
        """
        api_key = self.config.get('api_key') or os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or provide api_key in config/openai_config.yaml."
            )
        
        model = self.config.get('model', 'gpt-3.5-turbo')
        temperature = self.config.get('temperature', 0.7)
        max_tokens = self.config.get('max_tokens', 2000)
        base_url = self.config.get('base_url')
        timeout = self.config.get('timeout', 60)
        max_retries = self.config.get('max_retries', 3)
        
        llm_kwargs = {
            'model': model,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'api_key': api_key,
            'timeout': timeout,
            'max_retries': max_retries
        }
        
        # Only add base_url if it's set (for Azure or custom endpoints)
        if base_url:
            llm_kwargs['base_url'] = base_url
        
        llm = ChatOpenAI(**llm_kwargs)
        
        logger.info(f"Created OpenAI LLM with model: {model}, base_url: {base_url or 'default'}")
        return llm
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate text using the LLM.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Returns:
            Generated text
        """
        from langchain_core.messages import HumanMessage, SystemMessage
        
        messages = []
        
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        messages.append(HumanMessage(content=prompt))
        
        llm = self.get_llm()
        response = await llm.ainvoke(messages)
        
        return response.content
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the configured model.
        
        Returns:
            Dictionary with model information
        """
        return {
            'provider': self.provider,
            'model': self.config.get('model', 'gpt-3.5-turbo'),
            'temperature': self.config.get('temperature', 0.7),
            'max_tokens': self.config.get('max_tokens', 2000),
            'base_url': self.config.get('base_url', 'https://api.openai.com/v1')
        }
