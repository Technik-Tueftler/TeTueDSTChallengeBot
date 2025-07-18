"""
File contains all the functions required to adjust the status of a game.
The workflow is started via a command.
"""

import discord
from .configuration import Configuration
from .db import get_changeable_games, GameStatus, get_game_from_id, update_db_obj


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
                discord.SelectOption(label="STOPPED", value="3"),
            ]
        elif game.status == GameStatus.RUNNING:
            options = [
                discord.SelectOption(label="PAUSE", value="2"),
                discord.SelectOption(label="STOPPED", value="3"),
                discord.SelectOption(label="FINISHED", value="4"),
            ]
        else:
            options = [
                discord.SelectOption(label="RUNNING", value="1"),
                discord.SelectOption(label="STOPPED", value="3"),
                discord.SelectOption(label="FINISHED", value="4"),
            ]
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
    games = await get_changeable_games(config)
    select_view = GameSelectView(config, games)
    await interaction.response.send_message(
        "Which game would you like to change the status of?",
        view=select_view,
        ephemeral=True,
    )
