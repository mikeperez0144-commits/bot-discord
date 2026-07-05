import asyncio
import discord
from discord.ext import commands
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Mini servidor web para mantener a Render activo de forma gratuita
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Online")

def run_web_server():
    server = HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 10000))), SimpleHTTPRequestHandler)
    server.serve_forever()

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

# Carga de extensiones corregida desde la raíz del proyecto
async def load_extensions():
    await bot.load_extension("antiinvite")
    await bot.load_extension("moderation")

async def main():
    # Arrancamos el servidor web simulado
    threading.Thread(target=run_web_server, daemon=True).start()
    
    async with bot:
        await load_extensions()
        await bot.start(os.environ.get("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
