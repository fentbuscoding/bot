"""
Help System Compatibility Shim
This file maintains backwards compatibility while loading the modular help system.
"""

# Import the modular help system
from .help import Help

def setup(bot):
    """Setup function for the help cog"""
    bot.add_cog(Help(bot))
