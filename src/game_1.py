"""
Module for handling the 'Fast and hungry, task hunt' game.
"""
from datetime import datetime
import discord
from discord import Interaction, errors
from .configuration import Configuration
from .db import Player, Exercise
from .db import get_random_tasks, process_player, update_db_obj


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
            discord.SelectOption(label="Beginner (100h)", value="beginner"),
            discord.SelectOption(label="Easy (200h)", value="easy"),
            discord.SelectOption(label="Medium (500h)", value="medium"),
            discord.SelectOption(label="Hard (800h)", value="hard"),
            discord.SelectOption(label="Extreme (1200h)", value="extreme"),
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
    try:
        if interaction.guild:
            difficulty_select = GameDifficultyInput(config)
            await interaction.response.send_message(
                "Choose the level of difficulty you want to practise:",
                view=difficulty_select,
                ephemeral=True,
            )
            await difficulty_select.wait()
            rating_min = 0
            rating_max = 100
            match difficulty_select.difficulty:
                case "beginner":
                    rating_min = 0
                    rating_max = 19
                case "easy":
                    rating_min = 20
                    rating_max = 39
                case "medium":
                    rating_min = 40
                    rating_max = 59
                case "hard":
                    rating_min = 60
                    rating_max = 79
                case "extreme":
                    rating_min = 80
                    rating_max = 101
                case _:
                    return

            task = (await get_random_tasks(
                config,
                1,
                rating_min=rating_min,
                rating_max=rating_max,
            ))[0]
            player = (await process_player(
                config,
                (Player(dc_id=interaction.user.id, name=interaction.user.name, hours=0),),
            ))[0]
            await update_db_obj(
                config,
                Exercise(
                    timestamp = datetime.now(),
                    task_id = task.id,
                    player_id = player.id
                ),
            )
            await interaction.user.send(
                f"Hello {player.name}, you selected the difficulty: "
                f"{difficulty_select.difficulty}. "
                f"Your task for practice is: \n{task.name}: {task.description}"
            )
    except errors.Forbidden as err:
        config.watcher.logger.error(
            f"Error sending message to user {player.name} with dc_id: {player.dc_id}. "
            f"Error: {err}"
        )
