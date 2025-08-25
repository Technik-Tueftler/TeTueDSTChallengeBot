"""
Module for handling the 'Fast and hungry, task hunt' game.
"""

import asyncio
from typing import List
from datetime import datetime
import discord
from discord import Interaction, errors
from discord.errors import DiscordException, NotFound, HTTPException, Forbidden
from .game import MissingGameConfig, GameStats
from .game import (
    game_configs,
    failed_game,
    get_player_rank,
    create_quests,
    generate_league_table,
)
from .configuration import Configuration
from .db import (
    Player,
    Exercise,
    Game,
    Task,
    ReactionStatus,
    Game1PlayerResult,
    Rank,
    GameStatus,
)
from .db import (
    get_random_tasks,
    process_player,
    update_db_obj,
    create_game,
    get_main_task,
    get_game_from_id,
    get_tasks_based_on_rating_1,
    balanced_task_mix_random,
    get_all_db_obj_from_id,
    get_all_game_x_player_from_message_id,
    get_reaction,
    get_game_player_association,
    update_db_objs,
    merging_calc_base_game_1,
)

game_positions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]


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


class ConfirmationView(discord.ui.View):
    """
    ConfirmationView class to create a confirmation view for the user.
    This view is used to confirm the game setup.
    """

    def __init__(self, config: Configuration, game: Game):
        super().__init__(timeout=60)
        self.game = game
        self.config = config

    @discord.ui.button(label="Im sure!", style=discord.ButtonStyle.danger)
    async def button_callback(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):  # pylint: disable=unused-argument
        """
        Callback function for the confirm button.
        """
        # await asyncio.sleep(2)
        await interaction.response.edit_message(
            content=f"Evaluation of the game with ID: {self.game.id} is finished. "
            + "Game status is also set to finished.",
            view=None,
        )
        self.stop()


class GameSelect(discord.ui.Select):
    """
    GameSelect class to create a input menu to select the target game. Here
    the input is built dynamically with the possible games that can be changed.
    """

    def __init__(self, config: Configuration, games: list[Game]):
        self.config = config
        options = [
            discord.SelectOption(
                label=f"{game.id}: {game.timestamp.strftime('%Y-%m-%d')}",
                value=str(game.id),
                emoji=game.status.icon,
                description=f"{game.name}",
            )
            for game in games
        ]
        super().__init__(
            placeholder="Select a game...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            game = await get_game_from_id(self.config, self.values[0])
            confirmation_view = ConfirmationView(self.config, game)
            await interaction.response.edit_message(
                content=f"You are sure to evaluate and finish the game with ID: {game.id}? "
                + "This is not reversible!",
                view=confirmation_view,
            )
        except AttributeError as err:
            self.config.watcher.logger.error(f"Attribute error during callback: {err}")


class GameSelectView(discord.ui.View):
    """
    GameSelectView class to create a view for the user to select the
    target game to change the status.
    """

    def __init__(self, config, games):
        super().__init__()
        self.add_item(GameSelect(config, games))


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
        self, interaction: discord.Interaction, select: discord.ui.UserSelect
    ):
        """
        Function to handle the user selection menu and create a player list.
        This function is called when the user selects player from the menu and
        call the interface to input player information.

        Args:
            interaction (discord.Interaction): Interaction object from Discord
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

    Args:
        interaction (discord.Interaction): Interaction object from Discord
        config (Configuration): App configuration
    """
    try:
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
                f"Selected players: {[player.name for player in user_view.player_list]}"
            )
            players = await process_player(config, user_view.player_list)
            game = await create_game(config, "Fast and hungry, task hunt", players)
            main_task = await get_main_task(config)
            config.watcher.logger.trace(
                f"Created game with ID: {game.id} and main task: {main_task.name}"
            )
            success = await initialize_game_1(
                config, interaction, game, players, main_task
            )
            config.watcher.logger.trace(f"Game initialization success: {success}")
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
                f"The players for game (ID: {game.id}) "
                + '"Fast and hungry, task hunt" are:\n'
            )
            for player in players:
                output_message = (
                    output_message
                    + f"<@{player.dc_id}> with {player.hours} playing hours.\n"
                )
            output_message += (
                "Each player now receives a private message with the tasks."
            )
            message = await interaction.followup.send(output_message)
            positions_game_1 = game_configs.get(
                "Fast and hungry, task hunt", []
            ).game_emojis
            if not positions_game_1:
                raise MissingGameConfig(
                    "No emojis found for game 'Fast and hungry, task hunt'."
                )
            for element in positions_game_1:
                await message.add_reaction(element)
            game.message_id = message.id
            game.channel_id = message.channel.id
            await update_db_obj(config, game)
    except MissingGameConfig as err:
        config.watcher.logger.error(
            f"Missing game configuration: {err}, game not started."
        )
    except (DiscordException, HTTPException, NotFound, Forbidden) as err:
        config.watcher.logger.error(
            f"Discord related error occurred while starting the game: {err}"
        )


async def initialize_game_1(
    config: Configuration,
    interaction: Interaction,
    game: Game,
    players: list[Player],
    main_task: Task,
) -> bool:
    """
    Function to initialize the game and send a message to all players with the
    tasks they have to complete.

    Args:
        config (Configuration): App configuration
        interaction (Interaction): Interaction object to get the guild
        game (Game): Game object to get the game id
        players (list[Player]): List of players to get the player ids and send messages with quests
        main_task (Task): Main task for all player in game 1
    """
    try:
        game_statistics = GameStats()
        await game_statistics.process_league_stats(config)
        players.sort(key=lambda x: x.hours, reverse=True)
        config.watcher.logger.debug(game_statistics)
        exclude_ids = set()
        exclude_lock = asyncio.Lock()  # pylint: disable=not-callable
        for player in players:
            dc_user = await interaction.guild.fetch_member(player.dc_id)
            if dc_user is None:
                config.logger.error(
                    f"User {player.name} not found in the guild with dc_id: {player.dc_id}."
                )
                await failed_game(config, game)
                break
            player_rank = await get_player_rank(config, player, game_statistics)
            rated_tasks = await get_tasks_based_on_rating_1(config, player_rank * 100)
            if not rated_tasks:
                config.watcher.logger.error(
                    f"No tasks found for player rating {player_rank}: {player.name}."
                )
                await failed_game(config, game)
                break
            async with exclude_lock:
                tasks = await balanced_task_mix_random(config, rated_tasks, exclude_ids)
                config.watcher.logger.debug(
                    f"Tasks for player {player.name}: {[task.name for task in tasks]}"
                )
                config.watcher.logger.debug(f"Exclude IDs: {exclude_ids}")
            if not tasks:
                config.watcher.logger.error(
                    f"No tasks found for player with Algo-Balanced: {player.name}."
                )
                await failed_game(config, game)
                break
            tasks.append(main_task)
            await create_quests(config, player, game, tasks)
            positions_game_1 = game_configs.get(
                "Fast and hungry, task hunt", []
            ).game_emojis
            if not positions_game_1:
                raise MissingGameConfig(
                    "No emojis found for game 'Fast and hungry, task hunt'."
                )
            await dc_user.send(
                f"Hello {dc_user.name}, you are now in the game "
                f'"{game.name}". You have to complete the following quests:\n'
                + "\n".join(
                    f"{positions_game_1[i]} {task.name}: {task.description}"
                    for i, task in enumerate(tasks)
                )
            )
        else:
            return True
        return False
    except errors.HTTPException as err:
        config.watcher.logger.error(
            f"Error sending message to user {player.name} with dc_id: {player.dc_id}. "
            f"Error: {err}"
        )
        await failed_game(config, game)
        return False
    except MissingGameConfig as err:
        config.watcher.logger.error(f"Missing game configuration: {err}")
        await failed_game(config, game)
        return False
    except (DiscordException) as err:
        config.watcher.logger.error(
            f"Discord related error occurred while initialize the game: {err}"
        )


class PlayerGameDaysInput(discord.ui.Modal):
    """
    PlayerGameDaysInput class to create a input menu with for the player game days
    """
    def __init__(self, config, player_list, game):
        super().__init__(title="Enter game days and player survival days")
        self.config = config
        self.player_list = player_list
        self.game = game
        self.input_valid = True
        self.add_item(
            discord.ui.TextInput(label="Game days", default="70", max_length=3)
        )
        for player in player_list:
            self.add_item(
                discord.ui.TextInput(
                    label=player.name,
                    placeholder="Enter the days played here",
                    default="0",
                )
            )
            self.add_item(
                discord.ui.TextInput(
                    label=player.name + ": survived",
                    placeholder="Enter here whether he survived",
                    default="no",
                )
            )

    async def on_submit(
        self, interaction: discord.Interaction
    ):  # pylint: disable=arguments-differ
        try:
            result = {child.label: child.value for child in self.children}
            player_results = []
            if not result["Game days"].isdigit():
                await interaction.response.send_message(
                    "Please enter only numbers for the game days.",
                    ephemeral=True,
                )
                self.config.watcher.logger.debug("Invalid input in modal for game days")
                return
            for player in self.player_list:
                self.config.watcher.logger.debug(
                    f"Player {player.name} survived {result[player.name]} days."
                )
                if not result[player.name].isdigit():
                    self.input_valid = False
                    break
                if not result[player.name + ": survived"] in ["yes", "no"]:
                    self.input_valid = False
                    break
                if int(result[player.name]) > int(result["Game days"]):
                    self.input_valid = False
                    break
                game_player_association = await get_game_player_association(
                    self.config, self.game.id, player.id
                )
                reactions = await get_reaction(
                    self.config,
                    self.game.message_id,
                    player.dc_id,
                    ReactionStatus.REGISTERED,
                )
                if not reactions:
                    comp_tasks = 0
                else:
                    comp_tasks = len(reactions)
                player_result = Game1PlayerResult(
                    player_days=int(result[player.name]),
                    total_tasks=5,
                    completed_tasks=comp_tasks,
                    survived=result[player.name + ": survived"],
                    gameplayerassociation=game_player_association,
                )
                player_results.append(player_result)
            if not self.input_valid:
                await interaction.response.send_message(
                    "Please enter only numbers for the playing days and 'yes' or 'no' for survived."
                    + " Furthermore, players game days cannot be greater than the game days.",
                    ephemeral=True,
                )
                self.config.watcher.logger.debug(
                    "Invalid input in modal for player days"
                )
                return
            self.game.playing_days = int(result["Game days"])
            await update_db_obj(self.config, self.game)
            await update_db_objs(self.config, player_results)
            await interaction.response.send_message(
                "All inputs have been saved.", ephemeral=True
            )
        except (DiscordException) as err:
            self.config.watcher.logger.error(
                f"Discord related error occurred while initialize the game: {err}"
            )


class ModalButtonView(discord.ui.View):
    """
    ModalButtonView class to create a view with a button to open the modal for
    entering the player game days and survival status.
    """
    def __init__(self, config: Configuration, player_list: list[Player], game: Game):
        super().__init__(timeout=None)
        self.config = config
        self.player_list = player_list
        self.game = game

    @discord.ui.button(label="Submission", style=discord.ButtonStyle.primary)
    async def open_modal(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,  # pylint: disable=unused-argument
    ):
        """
        Function to open the modal for entering the player game days and survival status.
        This function is called when the button is clicked.
        """
        game_input = PlayerGameDaysInput(self.config, self.player_list, self.game)
        await interaction.response.send_modal(game_input)
        await game_input.wait()
        self.stop()


async def finish_game_1(
    config: Configuration, game: Game, interaction: discord.Interaction
): # pylint: disable=too-many-locals, too-many-statements
    """
    Function to finish the game and update the game status.

    Args:
        config (Configuration): App configuration
        game (Game): Game object to finish the game
    """
    try:
        player_scores = {}
        game_x_player = await get_all_game_x_player_from_message_id(
            config, game.message_id
        )
        player = await get_all_db_obj_from_id(
            config,
            Player,
            [player.player_id for player in game_x_player.players],
        )

        player_dc_ids = [int(player.dc_id) for player in player]
        game_emojis = game_configs.get(game_x_player.name, []).game_emojis
        config.watcher.logger.debug(f"Game: {game.id} with players: {player_dc_ids}")
        config.watcher.logger.debug(f"Game emojis: {game_emojis}")
        for player_id in player_dc_ids:
            reactions = await get_reaction(
                config, game.message_id, player_id, ReactionStatus.REGISTERED
            )
            config.watcher.logger.debug(
                f"Reactions for DC_ID: {player_id}: {[reaction.id for reaction in reactions]}"
            )
        view = ModalButtonView(config, player, game)
        await interaction.followup.send(
            "The game is now evaluated using the key data of the game and the players.",
            view=view,
            ephemeral=True,
        )
        await view.wait()
        results = await merging_calc_base_game_1(config, [game.id])

        for result in results:
            score = 0
            player = result.gameplayerassociation.player
            game = result.gameplayerassociation.game
            association_id = result.gameplayerassociation.id
            config.watcher.logger.debug(
                f"Processing Player ID: {player.id}, Game ID: {game.id}, "
                + f"Association ID: {association_id}"
            )
            config.watcher.logger.debug(
                f"Player: {player.name}, Game: {game.id}, "
                + f"Completed Tasks: {result.completed_tasks}, Survived: {result.survived}, "
                + f"Player Days: {result.player_days}"
            )
            value_tasks = result.completed_tasks * config.game.weighted_rank_task_g1
            value_survived = (
                1 if result.survived == "yes" else 0
            ) * config.game.weighted_rank_surv_g1
            value_days = result.player_days * config.game.weighted_rank_days_g1
            score = value_tasks + value_survived + value_days
            config.watcher.logger.debug(
                f"Score: {score} - Tasks: {value_tasks}, Survived: {value_survived}, "
                + f"Days: {value_days}"
            )
            config.watcher.logger.debug(f"Total Score for {player.name}: {score}")
            player_scores[association_id] = (
                player.name,
                score,
                result.player_days,
                player.dc_id,
                result.survived,
            )
        sorted_scores = sorted(
            player_scores.items(), key=lambda x: x[1][1], reverse=True
        )
        ranks = []
        rank = 1
        points = 6
        last_score = 0
        response_message = f"Player rankings in game (ID: {game.id}):\n"
        for player in sorted_scores:
            if player[1][1] < last_score:
                rank += 1
                points -= 1
            temp = Rank(
                placement=rank,
                points=points,
                timestamp=datetime.now(),
                game_player_association_id=player[0],
                survived=player[1][2],
            )
            last_score = player[1][1]
            ranks.append(temp)
            dc_name = f"<@{player[1][3]}>"
            survived_icon = ":olive:" if player[1][4] == "yes" else ":skull:"
            response_message += (
                f"{game_positions[rank-1]} {dc_name:<20} {survived_icon} - Points: {points}, "
                + f"Survived: {player[1][2]} / {game.playing_days} days"
                + "\n"
            )
        response_message += (
            "The league table has been recalculated with the new rankings. "
            + "Thank you all for participating. We hope you enjoyed it and "
            + "will join us again next season."
        )
        await update_db_objs(config, ranks)
        game.status = GameStatus.FINISHED
        _ = await update_db_obj(config, game)
        await generate_league_table(config)
        await interaction.followup.send(response_message)

    except (
        asyncio.TimeoutError,
        asyncio.CancelledError,
        DiscordException,
        HTTPException,
        Forbidden,
        NotFound,
    ) as err:
        config.watcher.logger.error(
            f"An error occurred while finishing the game: {err}"
        )
