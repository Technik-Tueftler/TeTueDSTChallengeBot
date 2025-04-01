"""
This module contains the discord bot implementation with definitions for the bot and its commands.
The bot is implemented using the discord.py library and provides a simple command to test the bot.
"""

from typing import List
from pydantic import BaseModel
import discord
from discord.ext import commands
from discord import Interaction
from .db import Player, process_player, create_game, update_db_obj


class DiscordBotConfiguration(BaseModel):
    """
    Configuration settings for discord bot
    """

    token: str


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
        self.config = config
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
        """
        Function to handle the user selection menu and create a player list.
        This function is called when the user selects player from the menu and
        call the interface to input player information.

        Args:
            interaction (Interaction): Interaction object
            select (discord.ui.UserSelect): UserSelect object
        """
        translated_player_list = [
            Player(dc_id=user.id, name=user.name, hours=0) for user in select.values
        ]
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
        user_view = UserSelectView(config)
        await interaction.response.send_message(
            'Select the players for the game "Fast and hungry, task hunt":',
            view=user_view,
            ephemeral=True,
        )
        await user_view.wait()
        if not user_view.valid_input:
            return
        player = await process_player(config, user_view.player_list)
        game = await create_game(config, "Fast and hungry, task hunt", player)
        output_message = (
            f'The players for game (ID: {game.id}) "Fast and hungry, task hunt" are:\n'
        )
        for player in user_view.player_list:
            output_message = (
                output_message
                + f"<@{player.dc_id}> with {player.hours} playing hours.\n"
            )
        output_message += "Each player now receives a private message with the tasks."
        message = await interaction.followup.send(output_message)
        
        await message.add_reaction("1️⃣")
        await message.add_reaction("2️⃣")
        await message.add_reaction("3️⃣")
        await message.add_reaction("4️⃣")
        await message.add_reaction("5️⃣")
        await message.add_reaction("🇭")

        game.message_id = message.id
        await update_db_obj(config, game)

        # try:
        #     # Über die Nachrichten ID die Nachricht abrufen
        #     new_message = await interaction.channel.fetch_message(int(message.id))
        #     # Über die Nachricht ID die Reaktionen abrufen
        #     for reaction in new_message.reactions:
        #         emoji = reaction.emoji
        #         count = reaction.count
        #         users = [user async for user in reaction.users()]
        #         print(
        #             f"Emoji: {emoji}, Anzahl: {count}, Benutzer: {[user.name for user in users]}"
        #         )
        # except Exception as e:
        #     print(f"Error fetching message: {e}")


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
# ich bekomme bei diesem befehl:
