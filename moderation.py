import discord
from discord.ext import commands
import asyncio
import io
from datetime import datetime

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.danger, custom_id="cerrar_ticket_btn", emoji="🔒")
    async def cerrar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        await interaction.response.send_message("🔒 Generando transcripción y cerrando...", ephemeral=True)
        
        try:
            log_channel = discord.utils.get(interaction.guild.text_channels, name="logs")
            if log_channel:
                transcript = f"Transcripcion del ticket: {channel.name}\nFecha: {datetime.utcnow()}\n\n"
                async for message in channel.history(limit=500, oldest_first=True):
                    transcript += f"{message.created_at.strftime('%H:%M:%S')} {message.author.name}: {message.content}\n"
                
                file = discord.File(io.BytesIO(transcript.encode('utf-8')), filename=f"ticket-{channel.name}.txt")
                await log_channel.send(f"📜 Transcripcion de **{channel.name}** cerrada por {interaction.user.name}", file=file)
        except Exception as e:
            print(f"Error al procesar logs: {e}")

        await asyncio.sleep(2)
        await channel.delete()

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Aquí irían tus comandos de warn/kick/ban si los tienes

async def setup(bot):
    await bot.add_cog(Moderation(bot))
    bot.add_view(CloseTicketView())
