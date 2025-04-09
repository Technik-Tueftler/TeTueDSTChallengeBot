"""
This file contains all logic for creating a game and managing the game state.
"""

from discord import Interaction
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.future import select
from .configuration import Configuration
from .db import Player, Quest, Task, Game, GamePlayerAssociation

positions_game_1 = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣", "🇭"]


async def initialize_game_1(
    config: Configuration, interaction: Interaction, game: Game, players: Player
):
    for player in players:
        dc_user = await interaction.guild.fetch_member(player.dc_id)
        if dc_user is None:
            config.logger.error(
                f"User {player.name} not found in the guild with dc_id: {player.dc_id}."
            )
            continue
        tasks = await create_quests(config, player, game)
        if not tasks:
            print("No tasks found for the player.")
            continue
        await dc_user.send(
            f"Hello {dc_user.name}, you are now in the game "
            f'"{game.name}". You have to complete the following quests:\n'
            + "\n".join(
                f"{positions_game_1[i]} {task.name}: {task.description}"
                for i, task in enumerate(tasks)
            )
        )


async def create_quests(
    config: Configuration, player: Player, game: Game
) -> list[Task]:
    """
    Function to get the quests for a player based on the playing hours.

    Args:
        config (Configuration): App configuration
        player (Player): Player object to get quests for

    Returns:
        list[Quest]: List of quests for the player
    """
    try:
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
                print(f"GamePlayerAssociation: {game_player_association.id}")
                tasks = (
                    (
                        await session.execute(
                            select(Task).order_by(func.random()).limit(5)
                        )
                    )
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
    except Exception as e:
        print(e)
        return []
