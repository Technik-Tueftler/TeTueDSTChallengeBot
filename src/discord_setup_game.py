import discord
from discord import Interaction
from .configuration import Configuration
from .db import get_changeable_games, GameStatus


class GameSelect(discord.ui.Select):
    def __init__(self, games):
        self.selected_game = None
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
            placeholder="Select a game ...", min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            self.selected_game = int(self.values[0])
            print(f"in GameSelect:  {self.selected_game}")
            print(f"ausgabe in callback: {self.values[0]}")
            self.view.stop()
        except Exception as e:
            print(e)


class SetupGameSelectView(discord.ui.View):
    def __init__(self, config, games):
        super().__init__(timeout=120)
        self.config = config
        self.selected_game_id = None
        self.game_select = GameSelect(games)
        self.add_item(self.game_select)

    async def wait_for_selection(self):
        try:
            await self.wait()
            print(f"in callback SetupGameSelectView: {self.game_select.selected_game}")
            self.selected_game_id = self.game_select.selected_game
            print(f"in callback SetupGameSelectView2: {self.selected_game_id}")
            return self.selected_game_id
        except Exception as e:
            print(e)


async def setup_game(interaction: discord.Interaction, config: Configuration):
    """
    Function game status with a select menu to choose the game status. The game status can be
    switched based on the current status of the game.

    Args:
        interaction (discord.Interaction): Interaction object to get the guild
        config (Configuration): App configuration
    """
    try:
        if interaction.guild:
            games = await get_changeable_games(config)
            if games:
                game_select_view = SetupGameSelectView(config, games)
                await interaction.response.send_message(
                    "Which game would you like to change the status of?",
                    view=game_select_view,
                    ephemeral=True,
                )
                await game_select_view.wait()
                print(f"ausgabe: {game_select_view.selected_game_id}")
                return
            await interaction.response.send_message(
                "There are currently no games that can be changed in status",
                ephemeral=True,
            )
    except Exception as err:
        print(err)
