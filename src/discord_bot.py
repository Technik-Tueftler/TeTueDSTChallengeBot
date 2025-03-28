"""
This module contains the discord bot implementation with definitions for the bot and its commands.
The bot is implemented using the discord.py library and provides a simple command to test the bot.
"""
from typing import List
from pydantic import BaseModel
import discord
from discord.ext import commands
from discord import Interaction
from .db import Player, process_player, get_player


class DiscordBotConfiguration(BaseModel):
    """
    Configuration settings for discord bot
    """

    token: str


# intents = discord.Intents.default()
# intents.members = True  # Option necessary to get members in guild
# bot = commands.Bot(command_prefix="!", intents=intents)


class PlayerLevelInput(
    discord.ui.Modal, title="Enter the playing hours for each player"
):
    """
    PlayerLevelInput class to create a input menu with for the player levels.
    """

    def __init__(self, config, player_list: List[Player]):
        super().__init__()
        self.player_list = player_list
        self.input_valid = True
        for player in player_list:
            default_hours = str(player.hours) if player.hours > 0 else ""
            self.add_item(
                discord.ui.TextInput(
                    label=player.name,
                    default=default_hours,
                    placeholder=f"Enter the playing hours for player {player.name}",
                    required=True,
                    max_length=5,
                )
            )

    async def on_submit(self, interaction: discord.Interaction):
        mapping = {child.label: child.value for child in self.children}
        for player in self.player_list:
            player.hours = mapping[player.name]
            if not player.hours.isdigit():
                self.input_valid = False
                break
        if not self.input_valid:
            await interaction.response.send_message(
                "Please enter only numbers for the playing hours.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            "The game was created plan the next steps and start the "
            + "game when you are ready via the emote.",
            ephemeral=True,
        )
        self.stop()


class UserSelectView(discord.ui.View):
    """
    UserSelectView class to create a view for the user selection menu with handler.
    """

    def __init__(self, config):
        super().__init__()
        self.player_list = []
        self.valid_input = True
        self.config = config
    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Select up to 6 user for the game",
        min_values=1,
        max_values=6,
    )
    async def user_select(
        self, interaction: Interaction, select: discord.ui.UserSelect
    ):
        translated_player_list = [Player(dc_id=user.id, name=user.name, hours=0) for user in select.values]
        self.player_list = await process_player(self.config, translated_player_list)
        player_input = PlayerLevelInput(self.config, self.player_list)
        await interaction.response.send_modal(player_input)
        await player_input.wait()
        self.valid_input = player_input.input_valid
        self.stop()


async def game1(interaction: discord.Interaction, config: DiscordBotConfiguration):
    """
    Command function to start a game with a user selection menu. This game is
    about completing all tasks and surviving. The game ends as soon as one
    player has completed all tasks.
    """
    if interaction.guild:
        try:
            user_view = UserSelectView(config)
            await interaction.response.send_message(
                'Select the players for the game "Fast and hungry, task hunt":',
                view=user_view,
                ephemeral=True,
            )
            await user_view.wait()
            if not user_view.valid_input:
                return
            output_message = 'The players for game "Fast and hungry, task hunt" are:\n'
            await update_player(config, user_view.player_list)
            for player in user_view.player_list:
                output_message = (
                    output_message
                    + f"<@{player.dc_id}> with {player.hours} playing hours.\n"
                )
            await interaction.followup.send(output_message)
        except Exception as e:
            print(e)

        # try:
        #
        # except Exception as e:
        # print(e)
        # print((f"The players for game \"Fast and hungry, task hunt\" are: : {', '.join(selected)}"))


class DiscordBot:
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
        async def wrapped_game1_command(interaction: discord.Interaction):
            await game1(interaction, self.config)
        self.bot.tree.command(
            name="fast_and_hungry_task_hunt",
            description="Complete all tasks and survive. The game ends as soon as one "
            "player has completed all tasks",
        )(wrapped_game1_command)


# async def main():
#     import os
#     from dotenv import load_dotenv

#     load_dotenv("files/.env", override=True)
#     TOKEN = os.getenv("TT_DC__token")
#     await bot.start(TOKEN)


# if __name__ == "__main__":
#     import asyncio

#     asyncio.run(main())
