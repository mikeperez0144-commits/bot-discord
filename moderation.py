import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import io

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.danger, custom_id="cerrar_ticket_btn", emoji="🔒")
    async def cerrar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        await interaction.response.send_message("🔒 Cerrando...", ephemeral=True)
        
        # Intentamos enviar el log, si falla, al menos borra el canal
        try:
            log_channel = discord.utils.get(interaction.guild.text_channels, name="logs")
            if log_channel:
                transcript = "Transcripcion del ticket: " + channel.name + "\n\n"
                async for message in channel.history(limit=500, oldest_first=True):
                    transcript += f"{message.author.name}: {message.content}\n"
                
                file = discord.File(io.BytesIO(transcript.encode('utf-8')), filename="transcript.txt")
                await log_channel.send(f"📜 Transcripcion de {channel.name}", file=file)
        except Exception as e:
            print(f"Error en logs: {e}")

        await asyncio.sleep(1)
        await channel.delete()

# ... (El resto de tus clases: TicketCategorySelect, TicketButton, Moderation, setup permanecen iguales)
