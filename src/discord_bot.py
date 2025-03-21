"""
This module contains the discord bot implementation with definitions for the bot and its commands.
The bot is implemented using the discord.py library and provides a simple command to test the bot.
"""

from pydantic import BaseModel
import discord
from discord.ext import commands
from discord import Interaction
from typing import List


class Player:
    """
    Player class to store the player name and the playing hours.
    """

    def __init__(self, name: str, dc_number: str, hours: str):
        self.name = name
        self.dc_id = dc_number
        self.hours = hours

    def __str__(self):
        return (
            f"Player {self.name} with id: {self.dc_id} has played {self.hours} hours."
        )


class DiscordBotConfiguration(BaseModel):
    """
    Configuration settings for discord bot
    """

    token: str


intents = discord.Intents.default()
intents.members = True  # Option necessary to get members in guild
bot = commands.Bot(command_prefix="!", intents=intents)


class PlayerLevelInput(
    discord.ui.Modal, title="Enter the playing hours for each player"
):
    """
    PlayerLevelInput class to create a input menu with for the player levels.
    """

    def __init__(self, player_list: List[Player]):
        super().__init__()
        self.player_list = player_list
        for player in player_list:
            self.add_item(
                discord.ui.TextInput(
                    label=player.name,
                    placeholder=f"Enter the playing hours for player {player.name}",
                    required=True,
                    max_length=5,
                )
            )

    async def on_submit(self, interaction: discord.Interaction):
        mapping = {child.label: child.value for child in self.children}
        for player in self.player_list:
            player.hours = mapping[player.name]
        # await interaction.response.send_message(f"Player 1: {self.hours_1.value}")
        await interaction.response.send_message(
            "The game was created plan the next steps and start the \
                game when you are ready via the emote.",
            ephemeral=True,
        )
        self.stop()


class UserSelectView(discord.ui.View):
    """
    UserSelectView class to create a view for the user selection menu with handler.
    """

    def __init__(self):
        super().__init__()
        self.player_list = []

    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Select up to 6 user for the game",
        min_values=1,
        max_values=6,
    )
    async def user_select(
        self, interaction: Interaction, select: discord.ui.UserSelect
    ):
        # print(select.values)
        # selected = [user.mention for user in select.values
        try:
            self.player_list = [Player(user.name, user.id, 0) for user in select.values]
            player_input = PlayerLevelInput(self.player_list)
            await interaction.response.send_modal(player_input)
            await player_input.wait()
        except Exception as e:
            print(e)
        print(f"{"#"*10} in UserSelect")
        for player in self.player_list:
            print(player)
        # await interaction.response.send_message(f"The players for game \"Fast and hungry, task hunt\" are: : {', '.join(selected)}")
        self.stop()


@bot.event
async def on_ready():
    """
    Event function to print a message when the bot is online.
    """
    print(f"{bot.user} ist online")
    try:
        synced = await bot.tree.sync()
        print(f"Slash Commands synchronisiert: {len(synced)}")
    except Exception as e:
        print(e)


@bot.tree.command(
    name="fast_and_hungry_task_hunt",
    description="Complete all tasks and survive. The game ends as "
    "soon as one player has completed all tasks",
)
async def game1(interaction: discord.Interaction):
    """
    Command function to start a game with a user selection menu. This game is
    about completing all tasks and surviving. The game ends as soon as one
    player has completed all tasks.
    """
    if interaction.guild:
        try:
            user_view = UserSelectView()
            await interaction.response.send_message(
                'Select the players for the game "Fast and hungry, task hunt":',
                view=user_view,
                ephemeral=True,
            )
            await user_view.wait()
            # print(user_view.children[0].values)
            # selected = [user.mention for user in user_view.children[0].values]
            print(
                f"{"#"*10} Create new Game and enter to DB with user_view.player_list"
            )
            output_message = 'The players for game "Fast and hungry, task hunt" are:\n'
            for player in user_view.player_list:
                output_message = (
                    output_message
                    + f"<@{player.dc_id}> with {player.hours} playing hours\n"
                )
            await interaction.followup.send(output_message)
        except Exception as e:
            print(e)

        # try:
        #
        # except Exception as e:
        # print(e)
        # print((f"The players for game \"Fast and hungry, task hunt\" are: : {', '.join(selected)}"))


async def main():
    import os
    from dotenv import load_dotenv

    load_dotenv("files/.env", override=True)
    TOKEN = os.getenv("TT_DC__token")
    await bot.start(TOKEN)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
