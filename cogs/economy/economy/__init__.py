# Economy System Module
from .economy_cog import Economy

__all__ = ['Economy']

async def setup(bot):
    """Setup function for the economy cog"""
    await bot.add_cog(Economy(bot))
