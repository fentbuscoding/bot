# Economy System Module
from .economy_cog import Economy

def setup(bot):
    bot.add_cog(Economy(bot))
