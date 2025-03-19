"""
This module contains the discord bot implementation with definitions for the bot and its commands.
The bot is implemented using the discord.py library and provides a simple command to test the bot.
"""

from pydantic import BaseModel
import discord
from discord.ext import commands
from discord import SelectOption, Interaction


class DiscordBotConfiguration(BaseModel):
    """
    Configuration settings for discord bot
    """

    token: str


intents = discord.Intents.default()
intents.members = True  # Option necessary to get members in guild
bot = commands.Bot(command_prefix="!", intents=intents)


class UserSelect(discord.ui.Select):
    """
    UserSelect class to create a user selection menu to select up to 6 users for the game.
    """

    def __init__(self, users):
        options = [
            SelectOption(label=user.name, value=str(user.id)) for user in users[:6]
        ]
        super().__init__(
            placeholder="Select up to 6 user for the game",
            min_values=1,
            max_values=6,
            options=options,
        )

    async def callback(self, interaction: Interaction):
        selected = [f"<@{user_id}>" for user_id in self.values]
        await interaction.response.send_message(
            f"The players for game \"Fast and hungry, task hunt\" are: : {', '.join(selected)}",
            # ephemeral=True Option that all user can see the message
        )


class UserSelectView(discord.ui.View):
    """
    UserSelectView class to create a view for the user selection menu with handler.
    """

    def __init__(self, users):
        super().__init__(timeout=60)
        self.add_item(UserSelect(users))
        self.message = None

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(
                content="Time has expired and is deactivated.", view=self
            )


@bot.event
async def on_ready():
    """
    Event function to print a message when the bot is online.
    """
    print(f"{bot.user} ist online")
    await bot.tree.sync()


@bot.tree.command(
    name="fast_and_hungry_task_hunt",
    description="Complete all tasks and survive. The game ends as " \
    "soon as one player has completed all tasks",
)
async def game1(interaction: discord.Interaction):
    """
    Command function to start a game with a user selection menu. This game is
    about completing all tasks and surviving. The game ends as soon as one 
    player has completed all tasks.
    """
    if interaction.guild:
        view = UserSelectView(interaction.guild.members)
        await interaction.response.send_message(
            "Select the players for the game \"Fast and hungry, task hunt\":", 
            view=view,
            ephemeral=True
        )
        view.message = await interaction.original_response()
