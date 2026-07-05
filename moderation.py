import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import asyncio

# ⚠️ PEGA AQUÍ EL ID DE LA CATEGORÍA DE DISCORD DONDE SE CREARÁN LOS CANALES
ID_CATEGORIA_TICKETS = 123456789012345678  # <- Cambia este número por tu ID real

async def send_log(guild: discord.Guild, embed: discord.Embed):
    channel = discord.utils.get(guild.text_channels, name="logs") or discord.utils.get(guild.text_channels, name="moderacion")
    if channel:
        try:
            await channel.send(embed=embed)
        except Exception:
            pass

# Vista con el botón ROJO de cerrar dentro del ticket
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.danger, custom_id="cerrar_ticket_btn", emoji="🔒")
    async def cerrar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if "ticket-" in interaction.channel.name:
            await interaction.response.send_message("🔒 Este ticket ha sido cerrado y se eliminará en 5 segundos...")
            await asyncio.sleep(5)
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("❌ Este canal no parece ser un ticket válido.", ephemeral=True)

# El menú desplegable con las opciones que me mostraste
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
        
        # Nombre del canal según la elección
        prefijo = "duda" if "Dudas" in opcion_seleccionada else "reporte" if "Reportar" in opcion_seleccionada else "sugerencia"
        channel_name = f"{prefijo}-{member.name.lower()}"
        
        # Comprobar si ya existe uno abierto
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            await interaction.response.send_message(f"❌ Ya tienes un ticket abierto para esta categoría en {existing_channel.mention}", ephemeral=True)
            return

        # Permisos del canal
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        for role in guild.roles:
            if role.permissions.manage_messages:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        category = guild.get_channel(ID_CATEGORIA_TICKETS)

        # Crear el canal
        ticket_channel = await guild.create_text_channel(
            name=channel_name, 
            overwrites=overwrites, 
            category=category
        )
        
        # Embed informativo dentro del ticket
        embed = discord.Embed(
            title=f"📩 Ticket Abierto: {opcion_seleccionada}",
            description=f"Bienvenido al Centro de Soporte, {member.mention}.\nHas seleccionado el apartado de **{opcion_seleccionada}**.\n\nExplica tu caso detalladamente aquí y un moderador te atenderá.\n\nPara cerrar el soporte, presiona el botón rojo.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="CactGuard • Gestión de Soporte")
        
        await ticket_channel.send(embed=embed, view=CloseTicketView())
        
        # Modificamos la respuesta inicial para avisar al usuario de que ya se creó
        await interaction.response.send_message(f"✅ ¡Ticket creado correctamente! Ve a {ticket_channel.mention}", ephemeral=True)

# Vista que sostiene el menú desplegable
class TicketSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())

# Vista principal que tiene el botón azul de "Abrir Ticket"
class TicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.blurple, custom_id="abrir_ticket_btn", emoji="📩")
    async def abrir_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Al pulsar el botón azul, le respondemos de forma privada con el menú desplegable de tus 3 opciones
        await interaction.response.send_message("Elige una opción del menú desplegable para abrir tu ticket:", view=TicketSelectView(), ephemeral=True)


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="setup-tickets", description="Envía el panel interactivo para abrir tickets. [Admin]")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_tickets(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📩 Sistema de Tickets",
            description="¿Necesitas asistencia o reportar algo?\nAbre un ticket presionando el botón de abajo, selecciona tu motivo y nuestro equipo te atenderá de inmediato.\n\n**🔒 Los tickets son privados y seguros.**",
            color=discord.Color.blue()
        )
        embed.set_footer(text="CactGuard • Soporte Técnico")
        
        await interaction.channel.send(embed=embed, view=TicketButton())
        await interaction.response.send_message("✅ Panel de tickets enviado correctamente.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
    # Registramos todas las vistas en la memoria persistente del bot
    bot.add_view(TicketButton())
    bot.add_view(TicketSelectView())
    bot.add_view(CloseTicketView())
