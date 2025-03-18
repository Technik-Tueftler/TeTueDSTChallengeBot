from pydantic import BaseModel
import discord
from discord.ext import commands

class DiscordBotConfiguration(BaseModel):
    """
    Configuration settings for db
    """

    token: str


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} ist online")
    await bot.tree.sync()

@bot.tree.command()
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("Funktioniert!")
