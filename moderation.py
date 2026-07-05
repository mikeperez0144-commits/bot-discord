@discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.danger, custom_id="cerrar_ticket_btn", emoji="🔒")
    async def cerrar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild
        
        await interaction.response.send_message("🔒 Generando transcripción...", ephemeral=True)

        # 1. Crear contenido
        transcript_content = f"Transcripción del ticket: {channel.name}\n"
        transcript_content += f"Fecha: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n"
        transcript_content += "="*30 + "\n\n"

        async for message in channel.history(limit=1000, oldest_first=True):
            transcript_content += f"{message.created_at.strftime('%H:%M:%S')} {message.author.name}: {message.content}\n"
        
        # 2. Crear archivo binario correctamente
        file_data = io.BytesIO(transcript_content.encode('utf-8'))
        file = discord.File(file_data, filename=f"ticket-{channel.name}.txt")

        # 3. Enviar a logs
        log_channel = discord.utils.get(guild.text_channels, name="logs") or discord.utils.get(guild.text_channels, name="moderacion")
        
        if log_channel:
            try:
                await log_channel.send(f"📜 Transcripción del ticket **{channel.name}** cerrado por {interaction.user.name}", file=file)
            except Exception as e:
                print(f"Error enviando log: {e}")
        
        # 4. Borrar canal
        await asyncio.sleep(2)
        await channel.delete()
