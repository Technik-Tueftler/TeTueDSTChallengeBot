"""
Module for handling the 'Fast and hungry, task hunt' game.
"""

from typing import List
from datetime import datetime
import discord
from discord import Interaction, errors
from .game import positions_game_1, initialize_game_1
from .configuration import Configuration
from .db import Player, Exercise
from .db import get_random_tasks, process_player, update_db_obj, create_game


class GameDifficultyInput(discord.ui.View):
    """
    Input view for selecting the difficulty level of the game.
    """
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

            task = (
                await get_random_tasks(
                    config,
                    1,
                    rating_min=rating_min,
                    rating_max=rating_max,
                )
            )[0]
            player = (
                await process_player(
                    config,
                    (
                        Player(
                            dc_id=interaction.user.id,
                            name=interaction.user.name,
                            hours=0,
                        ),
                    ),
                )
            )[0]
            await update_db_obj(
                config,
                Exercise(
                    timestamp=datetime.now(), task_id=task.id, player_id=player.id
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

    async def on_submit(
        self, interaction: discord.Interaction
    ):  # pylint: disable=arguments-differ
        try:
            mapping = {child.label: child.value for child in self.children}
            for player in self.player_list:
                if not mapping[player.name].isdigit():
                    self.input_valid = False
                    break
                player.hours = mapping[player.name]
            if not self.input_valid:
                await interaction.response.send_message(
                    "Please enter only numbers for the playing hours.",
                    ephemeral=True,
                )
                return
            await interaction.response.send_message(
                "All entries for the game and the players were error-free.",
                ephemeral=True,
            )
            self.stop()
        except AttributeError as err:
            self.config.watcher.logger.error(
                f"Error during on_submit in PlayerLevelInput: {err}"
            )


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


async def game1(interaction: discord.Interaction, config: Configuration):
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
        config.watcher.logger.trace(
            f"Selected players: {[player.name for player in user_view.player_list]}")
        players = await process_player(config, user_view.player_list)
        config.watcher.logger.trace(
            f"Processed players: {[player.name for player in players]}"
        )
        game = await create_game(config, "Fast and hungry, task hunt", players)
        config.watcher.logger.trace(
            f"Created game with ID: {game.id}"
        )
        success = await initialize_game_1(config, interaction, game, players)
        config.watcher.logger.trace(
            f"Game initialization success: {success}"
        )
        if not success:
            await interaction.followup.send(
                (
                    "An error has occurred while creating the game. Please check the error "
                    "log and documentation."
                ),
                ephemeral=True,
            )
            return

        output_message = (
            f'The players for game (ID: {game.id}) "Fast and hungry, task hunt" are:\n'
        )
        for player in players:
            output_message = (
                output_message
                + f"<@{player.dc_id}> with {player.hours} playing hours.\n"
            )
        output_message += "Each player now receives a private message with the tasks."
        message = await interaction.followup.send(output_message)
        for element in positions_game_1:
            await message.add_reaction(element)
        game.message_id = message.id
        await update_db_obj(config, game)

        # await send_player_tasks(config, player, game)

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
