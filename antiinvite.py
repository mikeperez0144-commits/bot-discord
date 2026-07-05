import discord
from discord.ext import commands
import re

class AntiInvite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Busca enlaces de invitación de Discord
        if re.search(r'discord\.gg/\S+', message.content) or re.search(r'discord\.com/invite/\S+', message.content):
            await message.delete()
            await message.channel.send(f"🚫 {message.author.mention}, no puedes enviar enlaces de invitación aquí.", delete_after=5)

async def setup(bot):
    await bot.add_cog(AntiInvite(bot))
