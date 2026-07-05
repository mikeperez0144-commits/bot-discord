"""
Anti-invite filter cog — filtro anti-invitaciones.

Automatically detects and deletes Discord invite links in any message or edit.
On a match:
  1. Deletes the message immediately.
  2. Warns the user via DM (falls back to a self-deleting channel notice).
"""

import re
import asyncio
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

# Se eliminó la importación rota de cogs.moderation

# ── Invite link regex ──────────────────────────────────────────────────────────
INVITE_RE = re.compile(
    r"(?<![a-zA-Z0-9.-])"
    r"(?:https?://)?(?:www\.)?"
    r"(?:discord(?:app)?\.com/invite|discord\.gg|dsc\.gg|invite\.gg)"
    r"/([a-zA-Z0-9][a-zA-Z0-9-]{0,24})",
    re.IGNORECASE,
)


def _extract_codes(content: str) -> list[str]:
    """Return all invite codes found in *content*, normalised to lowercase."""
    return [m.group(1).lower() for m in INVITE_RE.finditer(content)]


def _parse_code(invite_input: str) -> str:
    """Extract an invite code from a full URL or a bare code, return it lowercase."""
    matches = INVITE_RE.findall(invite_input.strip())
    if matches:
        return matches[0].lower()
    return invite_input.strip().lower()


# ── Per-guild state ────────────────────────────────────────────────────────────
antiinvite_data: dict[int, dict] = {}


def get_antiinvite(guild_id: int) -> dict:
    if guild_id not in antiinvite_data:
        antiinvite_data[guild_id] = {
            "enabled": False,
            "allowed_codes": set(),
        }
    return antiinvite_data[guild_id]


# ── Shared enforcement logic ───────────────────────────────────────────────────

async def _check_message(message: discord.Message) -> None:
    if message.author.bot:
        return
    if not message.guild:
        return
    if not message.content:
        return

    member = message.author
    guild = message.guild
    cfg = get_antiinvite(guild.id)

    if not cfg["enabled"]:
        return

    # Staff (manage_messages) are exempt
    if isinstance(member, discord.Member) and member.guild_permissions.manage_messages:
        return

    codes = _extract_codes(message.content)
    if not codes:
        return

    # Only act if at least one found code is NOT whitelisted
    blocked_codes = [c for c in codes if c not in cfg["allowed_codes"]]
    if not blocked_codes:
        return

    # ── 1. Delete ────────────────────────────────────────────────────────────
    try:
        await message.delete()
    except (discord.Forbidden, discord.HTTPException):
        pass

    # ── 2. Warn the user ─────────────────────────────────────────────────────
    warn_embed = discord.Embed(
        title="🔗 Enlace de invitación eliminado",
        description=(
            f"Tu mensaje en **{guild.name}** fue eliminado porque contenía "
            "un enlace de invitación a otro servidor de Discord.\n\n"
            "Si necesitas compartir un enlace authorized, contacta al staff."
        ),
        color=discord.Color.yellow(),
        timestamp=datetime.utcnow(),
    )
    warn_embed.set_footer(text="Por favor, revisa las normas del servidor.")

    dm_sent = False
    try:
        await member.send(embed=warn_embed)
        dm_sent = True
    except (discord.Forbidden, discord.HTTPException):
        pass

    if not dm_sent:
        try:
            notice = await message.channel.send(
                f"🔗 {member.mention}, tu mensaje fue eliminado por contener "
                "un enlace de invitación no autorizado."
            )
            await asyncio.sleep(8)
            await notice.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

    # Se eliminó la función de logs rota (send_log) para evitar errores del bot


# ── Nested app-command groups ──────────────────────────────────────────────────

class WhitelistSubgroup(app_commands.Group):
    def __init__(self) -> None:
        super().__init__(
            name="whitelist",
            description="Gestiona la lista blanca de invitaciones permitidas.",
        )

    @app_commands.command(name="add", description="Añade un enlace o código a la lista blanca.")
    @app_commands.describe(invite="URL completa (discord.gg/código) o solo el código.")
    async def whitelist_add(self, interaction: discord.Interaction, invite: str) -> None:
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ Necesitas el permiso **Gestionar mensajes** para modificar la lista blanca.",
                ephemeral=True,
            )
            return

        code = _parse_code(invite)
        if not code:
            await interaction.response.send_message(
                "❌ No se pudo extraer un código de invitación válido.", ephemeral=True
            )
            return

        cfg = get_antiinvite(interaction.guild_id)
        if code in cfg["allowed_codes"]:
            await interaction.response.send_message(
                f"⚠️ `{code}` ya está en la lista blanca.", ephemeral=True
            )
            return

        cfg["allowed_codes"].add(code)
        await interaction.response.send_message(
            f"✅ `{code}` añadido a la lista blanca.\n"
            f"Entradas en la lista blanca: **{len(cfg['allowed_codes'])}**",
            ephemeral=True,
        )

    @app_commands.command(name="remove", description="Elimina un enlace o código de la lista blanca.")
    @app_commands.describe(invite="URL completa (discord.gg/código) o solo el código.")
    async def whitelist_remove(self, interaction: discord.Interaction, invite: str) -> None:
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ Necesitas el permiso **Gestionar mensajes** para modificar la lista blanca.",
                ephemeral=True,
            )
            return

        code = _parse_code(invite)
        cfg = get_antiinvite(interaction.guild_id)

        if code not in cfg["allowed_codes"]:
            await interaction.response.send_message(
                f"❌ `{code}` no está en la lista blanca.", ephemeral=True
            )
            return

        cfg["allowed_codes"].discard(code)
        await interaction.response.send_message(
            f"✅ `{code}` eliminado de la lista blanca.\n"
            f"Entradas en la lista blanca: **{len(cfg['allowed_codes'])}**",
            ephemeral=True,
        )


class InvitesGroup(app_commands.Group):
    def __init__(self) -> None:
        super().__init__(
            name="invites",
            description="Configura la protección anti-invitaciones.",
            default_permissions=discord.Permissions(manage_messages=True),
        )
        self.add_command(WhitelistSubgroup())

    @app_commands.command(name="enable", description="Activa el filtro anti-invitaciones. [Admin]")
    async def invites_enable(self, interaction: discord.Interaction) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Necesitas permiso de **Administrador** para activar el filtro.",
                ephemeral=True,
            )
            return

        cfg = get_antiinvite(interaction.guild_id)
        if cfg["enabled"]:
            await interaction.response.send_message(
                "ℹ️ El filtro anti-invitaciones ya está **activado**.", ephemeral=True
            )
            return

        cfg["enabled"] = True
        wl_count = len(cfg["allowed_codes"])
        note = (
            f"\n\nHay **{wl_count}** código(s) en la lista blanca."
            if wl_count
            else "\n\nLa lista blanca está vacía — todos los enlaces serán eliminados."
        )
        await interaction.response.send_message(
            f"✅ Filtro anti-invitaciones **activado**.{note}", ephemeral=True
        )

    @app_commands.command(name="disable", description="Desactiva el filtro anti-invitaciones. [Admin]")
    async def invites_disable(self, interaction: discord.Interaction) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Necesitas permiso de **Administrador** para desactivar el filtro.",
                ephemeral=True,
            )
            return

        cfg = get_antiinvite(interaction.guild_id)
        if not cfg["enabled"]:
            await interaction.response.send_message(
                "ℹ️ El filtro anti-invitaciones ya está **desactivado**.", ephemeral=True
            )
            return

        cfg["enabled"] = False
        await interaction.response.send_message(
            "✅ Filtro anti-invitaciones **desactivado**.", ephemeral=True
        )


# ── Cog ───────────────────────────────────────────────────────────────────────

class AntiInvite(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._invites_group = InvitesGroup()
        bot.tree.add_command(self._invites_group)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command("invites")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        await _check_message(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if before.content == after.content:
            return
        await _check_message(after)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AntiInvite(bot))


