"""
This module contains the discord bot implementation with definitions for the bot and its commands.
The bot is implemented using the discord.py library and provides a simple command to test the bot.
"""
from pydantic import BaseModel
import discord
from discord.ext import commands
from discord import SelectOption, Interaction

class DiscordBotConfiguration(BaseModel):
    token: str

intents = discord.Intents.default()
intents.members = True  # Für Mitgliederliste benötigt
bot = commands.Bot(command_prefix="!", intents=intents)

class UserSelect(discord.ui.Select):
    def __init__(self, users):
        options = [
            SelectOption(label=user.name, value=str(user.id)) 
            for user in users[:6]  # Ersten 6 Mitglieder
        ]
        super().__init__(
            placeholder="Wähle bis zu 6 Benutzer aus",
            min_values=1,
            max_values=6,
            options=options
        )

    async def callback(self, interaction: Interaction):
        selected = [f"<@{user_id}>" for user_id in self.values]
        await interaction.response.send_message(
            f"Ausgewählte Benutzer: {', '.join(selected)}",
            ephemeral=True
        )

class UserSelectView(discord.ui.View):
    def __init__(self, users):
        super().__init__()
        self.add_item(UserSelect(users))

@bot.event
async def on_ready():
    print(f"{bot.user} ist online")
    await bot.tree.sync()

@bot.tree.command(name="test", description="User-Auswahlmenü testen")
async def test(interaction: discord.Interaction):
    """Zeigt ein User-Auswahlmenü an"""
    if interaction.guild:
        view = UserSelectView(interaction.guild.members)
        await interaction.response.send_message(
            "Wähle Benutzer aus:", 
            view=view,
            # ephemeral=True Option, dass nur der Benutzer die Nachricht sieht
        )
    else:
        await interaction.response.send_message(
            "Dieser Befehl funktioniert nur auf Servern",
            ephemeral=True
        )
