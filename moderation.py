import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import asyncio

# ⚠️ Asegúrate de tener aquí el ID correcto de tu categoría
ID_CATEGORIA_TICKETS = 123456789012345678 

async def send_log(guild: discord.Guild, embed: discord.Embed):
    channel = discord.utils.get(guild.text_channels, name="logs") or discord.utils.get(guild.text_channels, name="moderacion")
    if channel:
        try:
            await channel.send(embed=embed)
        except Exception:
            pass

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.danger, custom_id="cerrar_ticket_btn", emoji="🔒")
    async def cerrar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Esta parte corregida reconoce cualquiera de tus canales
        if any(prefix in interaction.channel.name for prefix in ["ticket-", "duda-", "reporte-", "sugerencia-"]):
            await interaction.response.send_message("🔒 Cerrando este ticket...", ephemeral=True)
            await asyncio.sleep(2)
            await interaction.channel.delete()
        elif interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("⚠️ Forzando cierre de canal...", ephemeral=True)
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("❌ Error: Este canal no está registrado como ticket activo.", ephemeral=True)

class TicketCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Dudas", description="Resuelve tus dudas", emoji="❓"),
            discord.SelectOption(label="Reportar", description="Reporta a usuarios del Discord", emoji="🔰"),
            discord.SelectOption(label="Sugerencias / Otros", description="Sugerencias y otros", emoji="🏳️")
        ]
        super().__init__(placeholder="Selecciona la categoría de tu problema...", min_values=1, max_values=1, options=options, custom_id="ticket_select_menu")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        opcion_seleccionada = self.values[0]
        prefijo = "duda" if "Dudas" in opcion_seleccionada else "reporte" if "Reportar" in opcion_seleccionada else "sugerencia"
        channel_name = f"{prefijo}-{member.name.lower()}"
        
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            await interaction.response.send_message(f"❌ Ya tienes un ticket abierto en {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        for role in guild.roles:
            if role.permissions.manage_messages:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        category = guild.get_channel(ID_CATEGORIA_TICKETS)
        ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites, category=category)
        
        embed = discord.Embed(title=f"📩 Ticket: {opcion_seleccionada}", description=f"Bienvenido {member.mention}. Explica tu problema aquí.", color=discord.Color.green())
        await ticket_channel.send(embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Ticket creado: {ticket_channel.mention}", ephemeral=True)

class TicketSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())

class TicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.blurple, custom_id="abrir_ticket_btn", emoji="📩")
    async def abrir_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Selecciona el motivo:", view=TicketSelectView(), ephemeral=True)

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="setup-tickets", description="Configura los tickets. [Admin]")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_tickets(self, interaction: discord.Interaction):
        embed = discord.Embed(title="📩 Sistema de Tickets", description="Pulsa el botón para abrir un ticket.", color=discord.Color.blue())
        await interaction.channel.send(embed=embed, view=TicketButton())
        await interaction.response.send_message("✅ Configurado.", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
    bot.add_view(TicketButton())
    bot.add_view(TicketSelectView())
    bot.add_view(CloseTicketView())
