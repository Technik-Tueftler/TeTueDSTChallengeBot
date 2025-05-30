"""
Module for handling the 'Fast and hungry, task hunt' game.
"""

import discord
from discord import Interaction
from .configuration import Configuration
from .db import get_random_tasks


class GameDifficultyInput(discord.ui.View):
    def __init__(self, config: Configuration):
        super().__init__(timeout=60)
        self.difficulty = None
        self.config = config

    @discord.ui.select(
        placeholder="Choose the level",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="Beginner", value="beginner"),
            discord.SelectOption(label="Easy", value="easy"),
            discord.SelectOption(label="Medium", value="medium"),
            discord.SelectOption(label="Hard", value="hard"),
            discord.SelectOption(label="Extreme", value="extreme"),
        ],
    )
    async def select_callback(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        """
        Callback function for the select menu to handle the selected difficulty.
        """
        self.difficulty = select.values[0]
        await interaction.response.send_message(
            f"You have selected the difficulty: {self.difficulty}",
            ephemeral=True,
        )
        self.stop()


async def practice_game1(interaction: Interaction, config: Configuration):
    """
    Command function to start a practice game based on 'Fast and hungry,
    task hunt' with a user menu to select the task difficulty.
    """
    if interaction.guild:
        difficulty_select = GameDifficultyInput(config)
        await interaction.response.send_message(
            "Choose the level of difficulty you want to practise:",
            view=difficulty_select,
            ephemeral=True,
        )
        await difficulty_select.wait()
        rating = 0
        match difficulty_select.difficulty:
            case "beginner":
                rating = 20
            case "easy":
                rating = 40
            case "medium":
                rating = 60
            case "hard":
                rating = 80
            case _:
                rating = 100

        task = await get_random_tasks(
            config,
            1,
            rating_min=rating - 20,
            rating_max=rating - 1,
        )
        dc_user = interaction.user
        await dc_user.send(
            f"Hello {dc_user.display_name}, you selected the difficulty: "
            f"{difficulty_select.difficulty}. "
            f"Your task for practice is: \n{task[0].name}: {task[0].description}"
        )
