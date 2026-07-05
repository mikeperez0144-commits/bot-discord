"""
Anti-invite filter cog — filtro anti-invitaciones.

Automatically detects and deletes Discord invite links in any message or edit.
On a match:
  1. Deletes the message immediately.
  2. Warns the user via DM (falls back to a self-deleting channel notice).
  3. Logs the incident in the moderation log channel.

Features:
  • Detects all common Discord invite URL formats:
      discord.gg/CODE
      discord.com/invite/CODE
      discordapp.com/invite/CODE
      dsc.gg/CODE
      invite.gg/CODE
  • Per-guild enable / disable toggle (off by default until /invites enable).
  • Whitelist: specific invite codes that are always permitted
    (e.g. the server's own invite link).
  • Staff exempt: members with Manage Messages are never filtered.
  • Also checks edited messages — edit-based bypasses are caught.
  • All state stored per guild — fully multi-server safe.

Commands  (group: /invites)
  /invites enable                  — turn the filter on              [administrator]
  /invites disable                 — turn the filter off             [administrator]
  /invites whitelist add <invite>  — whitelist a code or URL        [manage_messages]
  /invites whitelist remove <invite> — un-whitelist a code or URL   [manage_messages]
"""

import re
import asyncio
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from cogs.moderation import send_log


# ── Invite link regex ──────────────────────────────────────────────────────────
# Group 1 captures the invite code.
# The negative lookbehind (?<![a-zA-Z0-9.-]) prevents matching inside longer
# host strings (e.g. "notdiscord.gg") while still matching bare "discord.gg/x"
# and "https://discord.gg/x".
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
    """
    Extract an invite code from a full URL or a bare code, return it lowercase.

    https://discord.gg/myserver  →  myserver
    discord.gg/myserver          →  myserver
    myserver                     →  myserver
    """
    matches = INVITE_RE.findall(invite_input.strip())
    if matches:
        return matches[0].lower()
    return invite_input.strip().lower()


# ── Per-guild state ────────────────────────────────────────────────────────────
# {
#   guild_id: {
#     "enabled"       : bool,       # filter active? (default False)
#     "allowed_codes" : set[str],   # lowercase invite codes that are always allowed
#   }
# }
antiinvite_data: dict[int, dict] = {}


def get_antiinvite(guild_id: int) -> dict:
    if guild_id not in antiinvite_data:
        antiinvite_data[guild_id] = {
            "enabled": False,
            "allowed_codes": set(),
        }
    return antiinvite_data[guild_id]


# ── Shared enforcement logic (used by both on_message and on_message_edit) ─────

async def _check_message(message: discord.Message) -> None:
    """
    Inspect *message* for invite links and act if found.
    Safe to call from both on_message and on_message_edit.
    """
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
            "Si necesitas compartir un enlace autorizado, contacta al staff."
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

    # ── 3. Log ───────────────────────────────────────────────────────────────
    safe_content = message.content[:500].replace("||", "")

    log_embed = discord.Embed(
        title="🔗 Anti-invitaciones — mensaje eliminado",
        color=discord.Color.orange(),
        timestamp=datetime.utcnow(),
    )
    log_embed.add_field(name="Usuario", value=f"{member.mention} (`{member.id}`)", inline=True)
    log_embed.add_field(name="Canal", value=message.channel.mention, inline=True)
    log_embed.add_field(
        name="Códigos bloqueados",
        value=" · ".join(f"`{c}`" for c in blocked_codes[:10]),
        inline=False,
    )
    log_embed.add_field(name="Contenido eliminado", value=f"||{safe_content}||", inline=False)
    log_embed.set_footer(text=f"ID de usuario: {member.id}")
    await send_log(guild, log_embed)


# ── Nested app-command groups ──────────────────────────────────────────────────
# discord.py 2.x Cog class-attribute groups cannot be nested, so we define the
# two levels as standalone app_commands.Group subclasses and register the root
# group manually from Cog.__init__.  Module-level state means no Cog reference
# is needed inside the command callbacks.

class WhitelistSubgroup(app_commands.Group):
    """
    /invites whitelist add <invite>
    /invites whitelist remove <invite>
    """

    def __init__(self) -> None:
        super().__init__(
            name="whitelist",
            description="Gestiona la lista blanca de invitaciones permitidas.",
        )

    # /invites whitelist add ───────────────────────────────────────────────────

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

    # /invites whitelist remove ────────────────────────────────────────────────

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
    """
    /invites enable
    /invites disable
    /invites whitelist add <invite>
    /invites whitelist remove <invite>
    """

    def __init__(self) -> None:
        super().__init__(
            name="invites",
            description="Configura la protección anti-invitaciones.",
            default_permissions=discord.Permissions(manage_messages=True),
        )
        # Attach the whitelist subgroup
        self.add_command(WhitelistSubgroup())

    # /invites enable ──────────────────────────────────────────────────────────

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

    # /invites disable ─────────────────────────────────────────────────────────

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
        # Register the nested group tree with the bot's command tree
        self._invites_group = InvitesGroup()
        bot.tree.add_command(self._invites_group)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command("invites")

    # ── Listeners ─────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        await _check_message(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        """Catch invite links added via message edits."""
        if before.content == after.content:
            return
        await _check_message(after)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AntiInvite(bot))
