# filepath: /home/ks/Desktop/bot/cogs/economy/Gambling.py
# Legacy gambling file - now imports from modular structure
# This file is kept for backward compatibility

# Import the new modular gambling system
from .gambling import setup

# Re-export the setup function
__all__ = ['setup']
