"""
This file contains all logic for creating a game and managing the game state.
"""

import asyncio
from datetime import datetime
from collections import defaultdict
from discord import Interaction, errors
from sqlalchemy import func, delete
from sqlalchemy.future import select
from sqlalchemy.exc import (
    SQLAlchemyError,
    IntegrityError,
    OperationalError,
    DBAPIError,
    StatementError,
)
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
    get_tasks_based_on_rating_1,
    balanced_task_mix_random,
)

positions_game_1 = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "🇭"]
# league_positions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]


class GameStats:
    """
    Class to store the game statistics and values to process the workflow.
    """

    def __init__(self):
        self.count_league_participants = 0
        self.max_hours = 0

    def __repr__(self):
        return f"Gamestats: {str(self.max_hours)}"

    async def process_league_stats(self, config: Configuration):
        """
        Function to process the league statistics and calculate the number of participants
        and the maximum hours played by a player.

        Args:
            config (Configuration): App configuration
        """
        try:
            async with config.db.session() as session:
                async with session.begin():
                    count_league_participants = (
                        await session.execute(
                            select(
                                func.count()  # pylint: disable=not-callable
                            ).select_from(League)
                        )
                    ).scalar_one_or_none()
                    max_hours = (
                        await session.execute(select(func.max(Player.hours)))
                    ).scalar_one_or_none()
                    if count_league_participants:
                        self.count_league_participants = count_league_participants
                    if max_hours:
                        self.max_hours = max_hours
        except (
            SQLAlchemyError,
            DBAPIError,
            OperationalError,
            StatementError,
        ) as db_err:
            config.watcher.logger.error(
                f"Database error processing league stats: {db_err}"
            )
        except asyncio.CancelledError:
            config.watcher.logger.error(
                "Async operation was cancelled while processing league stats"
            )
        except (TypeError, ValueError) as err:
            config.watcher.logger.error(f"Error processing league stats: {err}")

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
                await stop_game(config, game)
                break
            player_rank = await get_player_rank(config, player, game_statistics)
            rated_tasks = await get_tasks_based_on_rating_1(config, player_rank * 100)
            if not rated_tasks:
                config.watcher.logger.error(
                    f"No tasks found for player rating {player_rank}: {player.name}."
                )
                await stop_game(config, game)
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
                await stop_game(config, game)
                break
            tasks.append(main_task)
            await create_quests(config, player, game, tasks)
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
        await stop_game(config, game)
        return False


async def create_quests(
    config: Configuration, player: Player, game: Game, tasks: list[Task]
) -> None:
    """
    Function to get the quests for a player based on the playing hours.

    Args:
        config (Configuration): App configuration
        player (Player): Player object to get quests for
    """
    try:
        async with config.db.session() as session:
            async with session.begin():
                game_player_association = (
                    await session.execute(
                        select(GamePlayerAssociation).where(
                            GamePlayerAssociation.game_id == game.id,
                            GamePlayerAssociation.player_id == player.id,
                        )
                    )
                ).scalar_one_or_none()

                for i, task in enumerate(tasks, start=1):
                    quest = Quest(
                        start_time=datetime.now(),
                        status="running",
                        task_id=task.id,
                        position=i,
                        game_player_association_id=game_player_association.id,
                    )
                    session.add(quest)
    except (SQLAlchemyError, IntegrityError, OperationalError) as db_err:
        config.watcher.logger.error(
            f"Database error while creating quests for player {player.name}: {db_err}"
        )
    except asyncio.CancelledError:
        config.watcher.logger.error(
            f"Async operation was cancelled while creating quests for player {player.name}"
        )
    except (AttributeError, TypeError, ValueError) as err:
        config.watcher.logger.error(
            f"Error creating quests for player {player.name}: {err}"
        )


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
                config.watcher.logger.debug(
                    f"Player: {player.name}, Points: {value['total_points']}, "
                    f"Survived: {value['total_survived']}"
                )
    config.watcher.logger.info("League table generated")


# async def show_league_table(
#     interaction: Interaction, config: Configuration
# ) -> None:
#     """
#     Function to show the league table in the Discord channel.

#     Args:
#         interaction (Interaction): Interaction object to respond to the command
#         config (Configuration): App configuration
#     """
#     try:
#         async with config.db.session() as session:
#             async with session.begin():
#                 league_table = (
#                     await session.execute(
#                         select(League).order_by(League.points.desc())
#                     )
#                 ).scalars().all()

#         if not league_table:
#             await interaction.response.send_message(
#                 "No players found in the league table."
#             )
#             return

#         table_lines = [
#             f"{league_positions[i]} {league.player.name} - "
#             f"Points: {league.points}, Survived: {league.survived}"
#             for i, league in enumerate(league_table)
#         ]
#         response_message = "\n".join(table_lines)

#         await interaction.response.send_message(response_message)
#     except SQLAlchemyError as db_err:
#         config.watcher.logger.error(f"Database error while showing league table: {db_err}")
#         await interaction.response.send_message("Error retrieving league table.")
#     except errors.HTTPException as http_err:
#         config.watcher.logger.error(f"HTTP error while sending message: {http_err}")
#         await interaction.response.send_message("Error sending league table message.")


async def get_player_rank(
    config: Configuration, player: Player, prepr_game_stats: GameStats
) -> int:
    """
    Function calculate the rank of a player based on the playing hours and league position.
    The rank is calculated based on the formula PLAYER_RANK_G1

    Args:
        config (Configuration): App configuration
        player (Player): Player to calculate the rank
        prepr_game_stats (GameStats): Complete game statistics

    Returns:
        int: Rank fore the player based on formula
    """
    config.watcher.logger.trace(
        f"Entry into get_player_rank with player: {player.name}"
    )
    try:
        hours = int(player.hours)
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

        game_score = config.game.weighted_hours_g1 * (
            hours / prepr_game_stats.max_hours
        )
        config.watcher.logger.trace(
            f"{config.game.weighted_hours_g1} * ({hours} / "
            f"{prepr_game_stats.max_hours}) = {game_score}"
        )
        if league_position < 1:
            league_score = 0.0
        else:
            league_score = config.game.weighted_league_pos_g1 * (
                1
                - (
                    (league_position - 1)
                    / (prepr_game_stats.count_league_participants - 1)
                )
            )
        config.watcher.logger.trace(
            f"{config.game.weighted_league_pos_g1} * (1 - (({league_position} - 1) / "
            f"({prepr_game_stats.count_league_participants} - 1)) = {league_score}"
        )
        result = game_score + league_score
        config.watcher.logger.trace(f"Game score: {game_score}")
        config.watcher.logger.trace(f"League score: {league_score}")
        config.watcher.logger.trace(f"Exit get_player_rank with scor: {result}")
        return result
    except TypeError as err:
        config.watcher.logger.error(f"TypeError in get_player_rank: {err}")
        config.watcher.logger.error(
            f"hours: {hours} ({type(hours)}) "
            f"max_hours: {prepr_game_stats.max_hours} ({type(prepr_game_stats.max_hours)}) "
            f"and league_position: {league_position} ({type(league_position)}) "
            f"and participants: {prepr_game_stats.count_league_participants} "
            f"({type(prepr_game_stats.count_league_participants)})"
        )
    except ValueError as err:
        config.watcher.logger.error(f"ValueError in get_player_rank: {err}")
        config.watcher.logger.error(f"Input hours: {hours} ({type(hours)})")
