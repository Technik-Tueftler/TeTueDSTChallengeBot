import discord
from discord import Interaction
from .configuration import Configuration
from .db import get_changeable_games, GameStatus, get_game_from_id, update_db_obj


class StatusSelect(discord.ui.Select):
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
        except Exception as err:
            print(err)


class StatusSelectView(discord.ui.View):
    def __init__(self, config, game):
        super().__init__()
        self.add_item(StatusSelect(config, game))


class GameSelect(discord.ui.Select):
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
        self.view.chosen_category = self.values[0]
        game = await get_game_from_id(self.config, self.values[0])
        await interaction.response.edit_message(
            content=f"You have chosen the game with id {game.id}. Now select the status:",
            view=StatusSelectView(self.config, game),
        )


class GameSelectView(discord.ui.View):
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
    try:
        games = await get_changeable_games(config)
        select_view = GameSelectView(config, games)
        await interaction.response.send_message(
            "Which game would you like to change the status of?",
            view=select_view,
            ephemeral=True,
        )
        # await select_view.wait()
        # print(select_view.chosen_category)
    except Exception as err:
        print(err)
