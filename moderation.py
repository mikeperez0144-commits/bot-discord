import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import asyncio

# Diccionario para guardar los warns (se borrará si el bot se reinicia)
warns = {}

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # --- COMANDO WARN ---
    @app_commands.command(name="warn", description="Avisa a un usuario. [Admin]")
    @app_commands.checks.has_permissions(kick_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, razon: str = "No especificada"):
        user_id = str(member.id)
        if user_id not in warns:
            warns[user_id] = 0
        
        warns[user_id] += 1
        embed = discord.Embed(title="⚠️ Warn", description=f"{member.mention} ha recibido un aviso.", color=discord.Color.red())
        embed.add_field(name="Razón", value=razon)
        embed.add_field(name="Total Warns", value=str(warns[user_id]))
        await interaction.response.send_message(embed=embed)

    # --- COMANDO KICK ---
    @app_commands.command(name="kick", description="Expulsa a un usuario. [Admin]")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, razon: str = "No especificada"):
        await member.kick(reason=razon)
        await interaction.response.send_message(f"✅ {member.name} ha sido expulsado. Razón: {razon}")

    # --- COMANDO BAN ---
    @app_commands.command(name="ban", description="Banea a un usuario. [Admin]")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, razon: str = "No especificada"):
        await member.ban(reason=razon)
        await interaction.response.send_message(f"🔨 {member.name} ha sido baneado. Razón: {razon}")

    # --- COMANDO VER WARNS ---
    @app_commands.command(name="warns", description="Mira cuántos avisos tiene un usuario.")
    async def ver_warns(self, interaction: discord.Interaction, member: discord.Member):
        count = warns.get(str(member.id), 0)
        await interaction.response.send_message(f"👤 {member.name} tiene {count} advertencia(s).")

# ... (Mantén aquí debajo todo el código de Tickets que ya tenías: CloseTicketView, TicketButton, setup_tickets, etc.)
