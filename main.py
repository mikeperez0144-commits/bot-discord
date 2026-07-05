import asyncio
import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado correctamente como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Se han sincronizado {len(synced)} comandos.")
    except Exception as e:
        print(f"❌ Error sincronizando comandos: {e}")

async def load_extensions():
    # Esto carga tu archivo antiinvite.py automáticamente
    await bot.load_extension("antiinvite")

async def main():
    async with bot:
        await load_extensions()
        # Koyeb leerá el token de forma segura desde aquí
        await bot.start(os.environ.get("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
