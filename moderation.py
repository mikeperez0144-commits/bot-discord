import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

# Función de logs que requiere antiinvite.py
async def send_log(guild: discord.Guild, embed: discord.Embed):
    # Busca un canal que se llame 'logs' o 'moderacion'
    channel = discord.utils.get(guild.text_channels, name="logs") or discord.utils.get(guild.text_channels, name="moderacion")
    if channel:
        try:
            await channel.send(embed=embed)
        except Exception:
            pass

# Vista interactiva con el botón para abrir tickets
class TicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Para que el botón no expire nunca

    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.blurple, custom_id="abrir_ticket_btn", emoji="📩")
    async def abrir_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        
        # Nombre del canal del ticket
        channel_name = f"ticket-{member.name.lower()}"
        
        # Comprobar si ya existe un ticket abierto por este usuario
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            await interaction.response.send_message(f"❌ Ya tienes un ticket abierto en {existing_channel.mention}", ephemeral=True)
            return

        # Configurar permisos: Solo el staff y el creador ven el canal
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Intentar dar permisos automáticos al Staff con Gestionar Mensajes
        for role in guild.roles:
            if role.permissions.manage_messages:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Crear el canal del ticket
        ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)
        
        # Embed de bienvenida dentro del ticket
        embed = discord.Embed(
            title="📩 Sistema de Tickets",
            description=f"Bienvenido al Centro de Soporte, {member.mention}.\n¿Necesitas ayuda? Explica tu problema aquí y el equipo de soporte te atenderá pronto.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="Usa /cerrar para finalizar este ticket.")
        
        await ticket_channel.send(embed=embed)
        await interaction.response.send_message(f"✅ ¡Ticket creado con éxito! Ve a {ticket_channel.mention}", ephemeral=True)

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # Comando para enviar el mensaje con el botón de Tickets
    @app_commands.command(name="setup-tickets", description="Envía el panel con el botón interactivo para abrir tickets. [Admin]")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_tickets(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📩 Sistema de Tickets",
            description="¿Necesitas ayuda? Abre un ticket y nuestro equipo te atenderá.\n\n**📋 ¿Cómo funciona?**\n1. Abre un ticket presionando el botón de abajo.\n2. Explica tu problema detalladamente.\n3. Espera la respuesta del staff.\n\n🔒 Los tickets son privados.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="CactGuard • Soporte Técnico")
        
        # Enviamos el embed junto con la vista del botón
        await interaction.channel.send(embed=embed, view=TicketButton())
        await interaction.response.send_message("✅ Panel de tickets enviado correctamente.", ephemeral=True)

    # Comando para cerrar el ticket
    @app_commands.command(name="cerrar", description="Cierra el ticket actual.")
    async def cerrar_ticket(self, interaction: discord.Interaction):
        if "ticket-" in interaction.channel.name:
            await interaction.response.send_message("🔒 Este ticket se cerrará y eliminará en 5 segundos...")
            import asyncio
            await asyncio.sleep(5)
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("❌ Este comando solo puede usarse dentro de un canal de ticket.", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
    # Volvemos a registrar la vista del botón para que funcione si el bot se reinicia
    bot.add_view(TicketButton())
