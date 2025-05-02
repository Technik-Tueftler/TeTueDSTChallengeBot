"""
This file contains all logic for creating a game and managing the game state.
"""

from datetime import datetime
from collections import defaultdict
from discord import Interaction
from sqlalchemy import func, delete
from sqlalchemy.future import select
from .configuration import Configuration
from .db import (
    Player,
    Quest,
    Task,
    Game,
    GamePlayerAssociation,
    GameStatus,
    update_db_obj,
    League,
    Rank,
    get_player,
)

positions_game_1 = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "🇭"]


class GameStats:
    """
    Class to store the game statistics and values to process the workflow.
    """

    def __init__(self):
        print("GameStats initialized")
        self.count_league_participants = 0
        self.max_hours = 0

    async def process_league_stats(self, config: Configuration):
        try:
            async with config.db.session() as session:
                async with session.begin():
                    count_league_participants = (
                        await session.execute(select(func.count()).select_from(League))
                    ).scalar_one_or_none()
                    max_hours = (
                        await session.execute(select(func.max(Player.hours)))
                    ).scalar_one_or_none()
                    if count_league_participants:
                        self.count_league_participants = count_league_participants
                    if max_hours:
                        self.max_hours = max_hours
        except Exception as err:
            print(f"Error processing league stats: {err}")

    async def rank_calculation_possible(self) -> bool:
        """
        Function to check if the rank calculation is possible.

        Returns:
            bool: True if the rank calculation is possible, False otherwise
        """
        return self.count_league_participants > 0 and self.max_hours > 0


async def stop_game(config: Configuration, game: Game) -> None:
    """
    Helper function to stop a game in case that a wrong input has been givin in selection menu.

    Args:
        config (Configuration): App configuration
        game (Game): Game object for change status
    """
    game.status = GameStatus.STOPPED
    await update_db_obj(config, game)
    config.watcher.logger.info(f"Game with ID: {game.id} was stopped.")


async def initialize_game_1(
    config: Configuration, interaction: Interaction, game: Game, players: list[Player]
) -> bool:
    """
    Function to initialize the game and send a message to all players with the
    tasks they have to complete.

    Args:
        config (Configuration): App configuration
        interaction (Interaction): Interaction object to get the guild
        game (Game): Game object to get the game id
        players (list[Player]): List of players to get the player ids and send messages with quests
    """
    try:
        prepr_game_stats = await GameStats().process_league_stats(config)
        players.sort(key=lambda x: x.hours, reverse=True)
        for player in players:
            dc_user = await interaction.guild.fetch_member(player.dc_id)
            if dc_user is None:
                config.logger.error(
                    f"User {player.name} not found in the guild with dc_id: {player.dc_id}."
                )
                await stop_game(config, game)
                break
            tasks = await create_quests(config, player, game, prepr_game_stats)
            if not tasks:
                config.watcher.logger.error(
                    f"No tasks found for player: {player.name}."
                )
                await stop_game(config, game)
                break
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
    except Exception as err:
        print(err)


async def create_quests(
    config: Configuration, player: Player, game: Game, prepr_game_stats: GameStats
) -> list[Task]:
    """
    Function to get the quests for a player based on the playing hours.

    Args:
        config (Configuration): App configuration
        player (Player): Player object to get quests for

    Returns:
        list[Task]: List of Task for the player
    """
    async with config.db.session() as session:
        async with session.begin():
            # ToDo: Hier muss noch rein welche TASKs erlaubt sind bei welcher spielzeit bzw. Spieler-Level
            # result = (await session.execute(select(Task).where(???).order_by(func.rand()).limit(5))).scalars().all()
            # tasks = session.execute(select(Quest).order_by(func.random())).first()
            game_player_association = (
                await session.execute(
                    select(GamePlayerAssociation).where(
                        GamePlayerAssociation.game_id == game.id,
                        GamePlayerAssociation.player_id == player.id,
                    )
                )
            ).scalar_one_or_none()
            # query=session.query(Table); idx=random.randint(0, query.count()); return query[idx]
            # lst=list(range(count+1));random.shuffle(lst);return lst[:5] wäre mein Ansatz.
            # Also am ende return [query[x] for x in lst[:5]]

            # erstelle tasks abhängig vom level (def get_player_level)
            # def get_player_level_to_task_rating(player) -> task_rating
            # (1) hole ich möglichen task die vom level passen? ja -> Ich hole alle Tasks >= task_rating
            # if task only once:
            # (2) task prüfen ob schon in benutzung: abfrage db bei quest game_player_association.id und task.id
            # outer join quest + task.id und auf once prüfen (1 + 2 in eine query)
            # (3) quest aus task erstellen und eintragen

            player_rank = await get_player_rank(config, player, prepr_game_stats)

            tasks = (
                (await session.execute(select(Task).order_by(func.random()).limit(5)))
                .scalars()
                .all()
            )
            for i, task in enumerate(tasks, start=1):
                quest = Quest(
                    start_time=datetime.now(),
                    status="running",
                    task_id=task.id,
                    position=i,
                    game_player_association_id=game_player_association.id,
                )
                print(f"Quest: {quest.position} / Task: {task.name}")
                session.add(quest)
    return tasks


async def generate_league_table(config: Configuration) -> None:
    """
    Function to generate the league table for the players based ranks.

    Args:
        config (Configuration): App configuration
    """
    async with config.db.session() as session:
        async with session.begin():
            ranks = (
                await session.execute(
                    select(Rank, GamePlayerAssociation.player_id).join(
                        GamePlayerAssociation,
                        Rank.game_player_association_id == GamePlayerAssociation.id,
                    )
                )
                # .all()
            )

    player_data = defaultdict(
        lambda: {"ranks": [], "total_points": 0, "total_survived": 0}
    )
    for rank, player_id in ranks:
        player_data[player_id]["ranks"].append(rank)
        player_data[player_id]["total_points"] += rank.points
        player_data[player_id]["total_survived"] += rank.survived

    sorted_players = sorted(
        player_data.items(),
        key=lambda x: (x[1]["total_points"], x[1]["total_survived"]),
        reverse=True,
    )

    async with config.db.session() as session:
        async with session.begin():
            await session.execute(delete(League))
            for player_id, value in sorted_players:
                player = await get_player(config, player_id)
                session.add(
                    League(
                        player=player,
                        points=value["total_points"],
                        survived=value["total_survived"],
                    )
                )
                config.watcher.logger.info("League table generated")
                config.watcher.logger.debug(
                    f"Player: {player.name}, Points: {value['total_points']}, "
                    f"Survived: {value['total_survived']}"
                )


async def get_player_rank(
    config: Configuration, player: Player, prepr_game_stats: GameStats
) -> int:
    hours = player.hours
    league_position = 0
    async with config.db.session() as session:
        async with session.begin():
            league_position_tbl = (
                await session.execute(
                    select(League).filter(League.player_id == player.id)
                )
            ).scalar_one_or_none()
    if league_position_tbl:
        league_position = league_position_tbl.id
    if not await prepr_game_stats.rank_calculation_possible():
        return 0.0

    return config.game.weighted_hours_g1 * (
        hours / prepr_game_stats.max_hours
    ) + config.game.weighted_league_pos_g1 * (
        1 - ((league_position - 1) / (prepr_game_stats.count_league_participants - 1))
    )
