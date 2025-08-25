"""
File contains all the functions required to adjust the status of a game.
The workflow is started via a command.
"""

import discord
from .configuration import Configuration
from .db import get_games_w_status, get_game_from_id, update_db_obj
from .db import GameStatus, Game
from .game_1 import finish_game_1


class StatusSelect(discord.ui.Select):
    """
    StatusSelect class to create a input menu to select the target status for the game.
    Here the input is built dynamically with the possible status of a game based on
    current status.
    """

    def __init__(self, config, game):
        self.game = game
        self.config = config
        if game.status == GameStatus.CREATED:
            options = [
                discord.SelectOption(label="RUNNING", value="1"),
                discord.SelectOption(label="PAUSE", value="2"),
            ]
        elif game.status == GameStatus.RUNNING:
            options = [
                discord.SelectOption(label="PAUSE", value="2"),
            ]
        elif game.status == GameStatus.PAUSED:
            options = [
                discord.SelectOption(label="RUNNING", value="1"),
                discord.SelectOption(label="STOPPED", value="3"),
            ]
        else:
            options = []
            config.watcher.logger.error(
                f"Game with ID {game.id} is in status {game.status.name}, "
                + "no status change possible."
            )
        super().__init__(
            placeholder="Select the destination status...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            old_status_name = self.game.status.name
            self.game.status = GameStatus(int(self.values[0]))
            new_status_name = self.game.status.name
            await update_db_obj(self.config, self.game)
            await interaction.response.edit_message(
                content=(
                    f"You have changed the status of game {self.game.id} from {old_status_name} "
                    f"to {new_status_name}"
                ),
                view=None,
            )
            await interaction.followup.send(
                f"The status of game with ID: {self.game.id} has been set to: {new_status_name}",
                ephemeral=False,
            )
        except (IndexError, ValueError) as err:
            self.config.watcher.logger.error(f"Error during callback: {err}")
        except discord.errors.Forbidden as err:
            self.config.watcher.logger.error(
                f"Error during callback with DC permissons: {err}"
            )


class StatusSelectView(discord.ui.View):
    """
    StatusSelectView class to create a view for the user to select the
    target status of the selected game
    """

    def __init__(self, config, game):
        super().__init__()
        self.add_item(StatusSelect(config, game))


class GameSelect(discord.ui.Select):
    """
    GameSelect class to create a input menu to select the target game. Here
    the input is built dynamically with the possible games that can be changed.
    """

    def __init__(self, config, games):
        self.config = config
        options = [
            discord.SelectOption(
                label=f"{game.id}: {game.timestamp.strftime('%Y-%m-%d')}",
                value=str(game.id),
                emoji=game.status.icon,
                description=f"{game.name} in status: {game.status.name}",
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
            self.view.chosen_category = self.values[0]
            game = await get_game_from_id(self.config, self.values[0])
            await interaction.response.edit_message(
                content=f"You have chosen the game with id {game.id}. Now select the status:",
                view=StatusSelectView(self.config, game),
            )
        except AttributeError as err:
            self.config.watcher.logger.error(f"Attribute rrror during callback: {err}")


class GameSelectView(discord.ui.View):
    """
    GameSelectView class to create a view for the user to select the
    target game to change the status.
    """

    def __init__(self, config, games):
        super().__init__()
        self.chosen_category = None
        self.add_item(GameSelect(config, games))


async def setup_game(interaction: discord.Interaction, config: Configuration):
    """
    Function game status with a select menu to choose the game status. The game status can be
    switched based on the current status of the game.

    Args:
        interaction (discord.Interaction): Interaction object to get the guild
        config (Configuration): App configuration
    """
    games = await get_games_w_status(
        config,
        [
            GameStatus.CREATED,
            GameStatus.RUNNING,
            GameStatus.PAUSED,
        ],
    )
    select_view = GameSelectView(config, games)
    await interaction.response.send_message(
        "Which game would you like to change the status of?",
        view=select_view,
        ephemeral=True,
    )


async def evaluate_game2(interaction: discord.Interaction, config: Configuration):
    """
    Command function to evaluate and finish a game of 'Fast and hungry, task hunt'.
    This function allows the user to select a game that has been evaluated and finished.

    Args:
        interaction (discord.Interaction): Interaction object from Discord
        config (Configuration): App configuration
    """
    games = await get_games_w_status(config, [GameStatus.STOPPED])
    select_view = GameSelectView(config, games)
    await interaction.response.send_message(
        "Which game would you like to evaluate and finish?",
        view=select_view,
        ephemeral=True,
    )


class GenGameSelect(discord.ui.Select):
    """
    General GameSelect class to create a input menu to select the target game. Here
    the input is built dynamically with the possible games that can be changed.
    """
    def __init__(self, config: Configuration, games: list[Game]):
        self.config = config
        options = [
            discord.SelectOption(
                label=f"{game.id}: {game.timestamp.strftime('%Y-%m-%d')}",
                value=str(game.id),
                emoji=game.status.icon,
                description=f"{game.name} in status: {game.status.name}",
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
        self.view.selected_game_id = self.values[0]
        self.disabled = True
        self.view.stop()
        await interaction.response.edit_message(
            content=f"You have chosen the game with id {self.values[0]}.",
            view=self.view,
        )


class GenGameSelectView(discord.ui.View):
    """
    GenGameSelectView class to create a view for the user to select the
    target game to change the status.
    """
    def __init__(self, config, games):
        super().__init__()
        self.selected_game_id = None
        self.add_item(GenGameSelect(config, games))

    async def wait_for_selection(self):
        """
        Function to wait for the user to select a game. This function is called after sending the
        message with the view to wait for the user to select
        """
        await self.wait()
        return self.selected_game_id


class ConfirmationView(discord.ui.View):
    """
    ConfirmationView class to create a confirmation view for the user.
    This view is used to confirm the game setup.
    """

    def __init__(self, config: Configuration, game: Game):
        super().__init__(timeout=60)
        self.game = game
        self.config = config
        self.result = None

    @discord.ui.button(label="Im sure!", style=discord.ButtonStyle.danger)
    async def button_callback(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):  # pylint: disable=unused-argument
        """
        Callback function for the confirm button.
        """
        # await asyncio.sleep(2)
        self.result = True
        await interaction.response.edit_message(
            content=f"Evaluation of the game with ID: {self.game.id} started",
            view=None,
        )
        self.stop()

    async def on_timeout(self):
        self.result = False
        await super().on_timeout()


async def evaluate_game(interaction: discord.Interaction, config: Configuration):
    """
    Function to evaluate and finish a game. This function allows the user to select a game
    that has been stopped and then confirms the evaluation of the game.

    Args:
        interaction (discord.Interaction): Interaction object to get the guild
        config (Configuration): App configuration
    """
    config.watcher.logger.trace("evaluate_game called")
    try:
        games = await get_games_w_status(config, [GameStatus.STOPPED])
        if not games:
            await interaction.response.send_message(
                "No games available to evaluate and finish.", ephemeral=True
            )
            return
        select_view = GenGameSelectView(config, games)
        await interaction.response.send_message(
            "Which game would you like to evaluate and finish?",
            view=select_view,
            ephemeral=True,
        )
        chosen_game_id = await select_view.wait_for_selection()
        if chosen_game_id is None:
            await interaction.followup.send("No game selected.", ephemeral=True)
            return
        game = await get_game_from_id(config, chosen_game_id)
        confirmation_view = ConfirmationView(config, game)
        await interaction.followup.send(
            content=f"You are sure to evaluate and finish the game with ID: {game.id}? "
            + "This is not reversible!",
            view=confirmation_view,
            ephemeral=True,
        )
        await confirmation_view.wait()

        if not confirmation_view.result:
            return

        # Idee 1
        match game.name:
            case "Fast and hungry, task hunt":
                await finish_game_1(config, game, interaction)
            case _:
                config.watcher.logger.error(
                    f"Game with ID {game.id} has an unknown name: {game.name}."
                )
    except Exception as err:
        print(f"Error during evaluate_game: {err}")
