"""
This module contains the discord bot implementation with definitions for the bot and its commands.
The bot is implemented using the discord.py library and provides a simple command to test the bot.
"""

import discord
from discord.ext import commands
from .discord_setup_game import setup_game
from .file_utils import import_tasks, export_tasks
from .game_1 import practice_game1, game1
# from .game import show_league_table


class DiscordBot:
    """
    DiscordBot class to create a discord bot with the given configuration. This is
    necessary because of a own implementation with user configuration and
    pydantic validation.
    """

    def __init__(self, config):
        self.config = config
        intents = discord.Intents.default()
        intents.members = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)

        @self.bot.event
        async def on_ready():
            await self.on_ready()

        self.register_commands()

    async def start(self):
        """
        Function to start the bot with the given token from the configuration.
        This function is called in the main function to start the bot.
        """
        await self.bot.start(self.config.dc.token)

    async def on_ready(self):
        """
        Event function to print a message when the bot is online.
        """
        print(f"{self.bot.user} ist online")
        synced = await self.bot.tree.sync()
        print(f"Slash Commands synchronisiert: {len(synced)}")
        await self.bot.change_presence(
            status=discord.Status.online, activity=discord.Game("Don't Starve Together")
        )

    def register_commands(self):
        """
        Function to register the commands for the bot. This function is called in the
        constructor to register the commands.
        """

        async def wrapped_game1_command(interaction: discord.Interaction):
            await game1(interaction, self.config)

        # async def wrapped_game1_evaluate(interaction: discord.Interaction):
        #     await game1_evaluate(interaction, self.config)

        async def wrapped_practice_game1_command(interaction: discord.Interaction):
            await practice_game1(interaction, self.config)

        async def wrapped_setup_game(interaction: discord.Interaction):
            await setup_game(interaction, self.config)

        # async def wrapped_show_league_table(interaction: discord.Interaction):
        #     await show_league_table(interaction, self.config)

        async def wrapped_import_tasks(interaction: discord.Interaction):
            await import_tasks(interaction, self.config)

        async def wrapped_export_tasks(interaction: discord.Interaction):
            await export_tasks(interaction, self.config)

        self.bot.tree.command(
            name="fast_and_hungry_task_hunt",
            description=(
                "Complete all tasks and survive. The game ends as "
                "soon as one player has completed all tasks"
            ),
        )(wrapped_game1_command)

        # self.bot.tree.command(
        #     name="evaluate_fast_and_hungry_task_hunt",
        #     description=(
        #         "Evaluate the game 'Fast and hungry, task hunt'. "
        #         "Check all reaktions and calculate the winner."
        #     ),
        # )(wrapped_game1_evaluate)

        self.bot.tree.command(
            name="prac_fast_and_hungry_task_hunt",
            description=(
                "Practice the game 'Fast and hungry, "
                "task hunt' with a user selection menu."
            ),
        )(wrapped_practice_game1_command)

        self.bot.tree.command(
            name="setup_game",
            description="Switch game state to specific status like running, paused, finished, etc.",
        )(wrapped_setup_game)

        # self.bot.tree.command(
        #     name="show_league_table",
        #     description="Show the current league table with all players and their scores.",
        # )(wrapped_show_league_table)

        self.bot.tree.command(
            name="import_tasks",
            description="Import and update current tasks from an Excel spreadsheet to database.",
        )(wrapped_import_tasks)

        self.bot.tree.command(
            name="export_tasks",
            description="Export current tasks from database to an Excel spreadsheet.",
        )(wrapped_export_tasks)
