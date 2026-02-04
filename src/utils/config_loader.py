"""
Configuration loader utility for handling YAML and environment configurations.
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigLoader:
    """Loads and manages configuration from YAML files and environment variables."""
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize the configuration loader.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self._config_cache: Dict[str, Any] = {}
    
    def load_config(self, config_name: str) -> Dict[str, Any]:
        """
        Load configuration from YAML file with environment variable substitution.
        
        Args:
            config_name: Name of the configuration file (without .yaml extension)
            
        Returns:
            Dictionary containing the loaded configuration
        """
        if config_name in self._config_cache:
            return self._config_cache[config_name]
        
        config_path = self.config_dir / f"{config_name}.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as file:
            config_content = file.read()
        
        # Substitute environment variables
        config_content = self._substitute_env_vars(config_content)
        
        try:
            config = yaml.safe_load(config_content)
            self._config_cache[config_name] = config
            return config
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {config_path}: {e}")
    
    def _substitute_env_vars(self, content: str) -> str:
        """
        Substitute environment variables in configuration content.
        
        Args:
            content: Configuration content with ${VAR_NAME} placeholders
            
        Returns:
            Content with environment variables substituted
        """
        import re
        
        def replace_env_var(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) else ""
            return os.getenv(var_name, default_value)
        
        # Replace ${VAR_NAME} and ${VAR_NAME:default} patterns
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        return re.sub(pattern, replace_env_var, content)
    
    def get_jira_config(self) -> Dict[str, Any]:
        """Load Jira configuration."""
        return self.load_config("jira_config")
    
    def get_confluence_config(self) -> Dict[str, Any]:
        """Load Confluence configuration."""
        return self.load_config("confluence_config")
    
    def validate_config(self, config: Dict[str, Any], required_fields: list) -> bool:
        """
        Validate that required fields exist in configuration.
        
        Args:
            config: Configuration dictionary to validate
            required_fields: List of required field names (dot notation supported)
            
        Returns:
            True if all required fields are present
        """
        for field in required_fields:
            keys = field.split('.')
            current = config
            
            for key in keys:
                if not isinstance(current, dict) or key not in current:
                    raise ValueError(f"Required configuration field missing: {field}")
                current = current[key]
        
        return True
