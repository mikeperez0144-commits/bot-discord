import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import asyncio
import io # Necesario para crear archivos de texto virtuales

# ... (Mantén tu ID_CATEGORIA_TICKETS y las clases anteriores igual)

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.danger, custom_id="cerrar_ticket_btn", emoji="🔒")
    async def cerrar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild
        
        await interaction.response.send_message("🔒 Generando transcripción y cerrando ticket...", ephemeral=True)

        # 1. Crear transcripción
        transcript = io.StringIO()
        transcript.write(f"Transcripción del ticket: {channel.name}\n")
        transcript.write(f"Fecha: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n")
        transcript.write("="*30 + "\n\n")

        # Leer los últimos 1000 mensajes
        async for message in channel.history(limit=1000, oldest_first=True):
            transcript.write(f"{message.created_at.strftime('%H:%M:%S')} {message.author.name}: {message.content}\n")
        
        transcript.seek(0)
        file = discord.File(transcript, filename=f"transcripcion-{channel.name}.txt")

        # 2. Enviar al canal de logs
        log_channel = discord.utils.get(guild.text_channels, name="logs") or discord.utils.get(guild.text_channels, name="moderacion")
        if log_channel:
            embed = discord.Embed(title="📜 Transcripción de Ticket", description=f"Ticket **{channel.name}** cerrado por {interaction.user.name}", color=discord.Color.purple())
            await log_channel.send(embed=embed, file=file)

        # 3. Borrar el canal
        await asyncio.sleep(2)
        await channel.delete()
