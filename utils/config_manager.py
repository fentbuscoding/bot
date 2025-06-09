# config_manager.py - Centralized configuration management
import os
import json
import logging
from typing import Dict, Any, Optional

class ConfigManager:
    """Centralized configuration manager with environment variable support"""
    
    def __init__(self, config_file: str = "data/config.json"):
        self.config_file = config_file
        self._config = {}
        self.logger = logging.getLogger('ConfigManager')
        self.load_config()
    
    def load_config(self):
        """Load configuration from file with environment variable overrides"""
        try:
            # Load base config from file
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self._config = json.load(f)
                self.logger.info(f"Loaded config from {self.config_file}")
            else:
                self.logger.warning(f"Config file {self.config_file} not found, using defaults")
                self._config = {}
            
            # Override with environment variables
            env_mappings = {
                'TOKEN': 'DISCORD_TOKEN',
                'DEV_TOKEN': 'DISCORD_DEV_TOKEN', 
                'MONGO_URI': 'MONGODB_URI',
                'CLIENT_ID': 'DISCORD_CLIENT_ID',
                'DEV': 'DEVELOPMENT_MODE'
            }
            
            for config_key, env_key in env_mappings.items():
                env_value = os.getenv(env_key)
                if env_value:
                    # Convert boolean strings
                    if env_value.lower() in ('true', 'false'):
                        env_value = env_value.lower() == 'true'
                    # Convert numeric strings
                    elif env_value.isdigit():
                        env_value = int(env_value)
                    
                    self._config[config_key] = env_value
                    self.logger.info(f"Overrode {config_key} from environment")
            
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with optional default"""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self._config[key] = value
    
    def save_config(self):
        """Save current config to file"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
            self.logger.info(f"Saved config to {self.config_file}")
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
    
    @property
    def is_dev(self) -> bool:
        """Check if running in development mode"""
        return self.get('DEV', False)
    
    @property
    def token(self) -> str:
        """Get appropriate token based on mode"""
        if self.is_dev:
            return self.get('DEV_TOKEN', '')
        return self.get('TOKEN', '')
    
    def validate_required(self) -> bool:
        """Validate that all required config values are present"""
        required_keys = ['TOKEN', 'MONGO_URI', 'CLIENT_ID']
        if self.is_dev:
            required_keys.append('DEV_TOKEN')
        
        missing_keys = []
        for key in required_keys:
            if not self.get(key):
                missing_keys.append(key)
        
        if missing_keys:
            self.logger.error(f"Missing required config keys: {missing_keys}")
            return False
        
        return True

# Global instance
config_manager = ConfigManager()
