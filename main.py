"""
Main function for starting application
"""

import asyncio
from sqlalchemy import text, func
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
import src


async def onlyonce(config):
    """
    Only a test function to create a game and player in the database.
    This function is not used in the main application and is only for testing and
    would be removed in the final version.
    """
    try:
        async with config.db.session() as session:
            async with session.begin():
                # await src.generate_league_table(config)
                result = await session.execute(
                    select(src.Player)
                    .options(selectinload(src.Player.league))  # Eager Loading
                    .where(src.Player.dc_id == "722546721430700314")
                )
                player = result.scalar_one()
                print(player)
                print(player.league.points)
                # print(f"Player: {player.name}, League-Punkte: {player.league}")
        async with config.db.session() as session:
            result = (
                await session.execute(select(func.count()).select_from(src.League))
            ).scalar_one()
            #print(f"Anzahl Einträge: {result}")
            count_max_hours_tbl = (
                await session.execute(select(func.max(src.Player.hours)))
            ).scalar_one_or_none()

        prepr_game_stats = src.GameStats()
        await prepr_game_stats.process_league_stats(config)

        playerslist = [player]
        player_rank = await src.get_player_rank(
                     config, playerslist[0], prepr_game_stats
                 )
        #print(f"Player: {playerslist[0].name}, Rank: {player_rank}")


        # print(prepr_game_stats.count_league_participants)
        # print(prepr_game_stats.max_hours)

        async with config.db.session() as session:
            async with session.begin():
                exclude_ids = set()
                exclude_lock = asyncio.Lock()
                result = (await session.scalars(select(src.Player))).all()
            for player in result:
                player_rank = await src.get_player_rank(
                    config, player, prepr_game_stats
                )
                print(20*"#")
                print(f"Player: {player.name}, Rank: {player_rank}")
                all_tasks = await src.get_tasks_based_on_rating_1(config, player_rank*100)
                if all_tasks:
                    tasks = await src.balanced_task_mix_random(all_tasks, exclude_ids, exclude_lock)
                    for task in tasks:
                        print(f"Task: {task.name}, Difficulty: {task.rating}")
                    

            # tasks = (
            #     (
            #         await session.execute(
            #             select(src.Task).filter(src.Task.rating <= (player_rank * 100)).order_by(src.Task.rating.desc())
            #         )
            #     )
            #     .scalars()
            #     .all()
            # )
            

    except Exception as e:
        print("Error in main function:", e)
    # async with config.db.session() as session:
    #     async with session.begin():
    #         task1 = (await session.execute(src.select(src.Task).filter(src.Task.id == 1))).scalar_one_or_none()
    #         task2 = (await session.execute(src.select(src.Task).filter(src.Task.id == 2))).scalar_one_or_none()
    #         task3 = (await session.execute(src.select(src.Task).filter(src.Task.id == 3))).scalar_one_or_none()
    #         task4 = (await session.execute(src.select(src.Task).filter(src.Task.id == 4))).scalar_one_or_none()
    #         player_1 = (await session.execute(src.select(src.Player).filter(src.Player.dc_id == "722546721430700314"))).scalar_one_or_none()
    #         player_2 = (await session.execute(src.select(src.Player).filter(src.Player.dc_id == "1142778497702572106"))).scalar_one_or_none()
    #         game1 = src.Game(
    #             name="DST",
    #             status="RUNNING",
    #             timestamp=src.datetime.now(),
    #             message_id=1234567890,
    #         )
    #         session.add(game1)
    #         await session.flush()
    #         print(game1.id)
    #         player_game1 = src.GamePlayerAssociation(game=game1, player=player_1)
    #         player_game2 = src.GamePlayerAssociation(game=game1, player=player_2)
    #         session.add_all([player_game1, player_game2])
    # async with config.db.session() as session:
    #     async with session.begin():
    #         quest1 = src.Quest(
    #             start_time=src.datetime.now(),
    #             end_time=src.datetime.now(),
    #             status="running",
    #             task_id=task1.id,
    #             game_player_association_id=player_game1.id,
    #         )
    #         quest2 = src.Quest(
    #             start_time=src.datetime.now(),
    #             end_time=src.datetime.now(),
    #             status="running",
    #             task_id=task2.id,
    #             game_player_association_id=player_game1.id,
    #         )
    #         quest3 = src.Quest(
    #             start_time=src.datetime.now(),
    #             end_time=src.datetime.now(),
    #             status="running",
    #             task_id=task3.id,
    #             game_player_association_id=player_game2.id,
    #         )
    #         quest4 = src.Quest(
    #             start_time=src.datetime.now(),
    #             end_time=src.datetime.now(),
    #             status="running",
    #             task_id=task4.id,
    #             game_player_association_id=player_game2.id,
    #         )
    #         quest5 = src.Quest(
    #             start_time=src.datetime.now(),
    #             end_time=src.datetime.now(),
    #             status="running",
    #             task_id=task4.id,
    #             game_player_association_id=player_game2.id,
    #         )
    #         session.add_all([quest1, quest2, quest3, quest4, quest5])

    # async with config.db.session() as session:
    #     async with session.begin():
    #         game = await session.get(
    #             src.Game,
    #             14,
    #             options=[
    #                 selectinload(src.Game.players).selectinload(
    #                     src.GamePlayerAssociation.player
    #                 )
    #             ],
    #         )
    #     players = [association.player for association in game.players]
    #     print(players)

    #     task = src.Task(
    #         name="Boss Kill 4",
    #         description="Kill the first boss in under 10 days",
    #         difficulty=100,
    #     )
    #     session.add(task)
    # await session.refresh(task)
    # print(task.id)
    # async with config.db.session() as session:
    #     async with session.begin():
    #     game1 = src.Game(name="Among Us", status="running", timestamp=src.datetime.now())
    #     player1 = src.Player(name="Luni", dc_id="722546721430700314", hours=0)
    #     player_game = src.GamePlayerAssociation(game=game1, player=player1)
    #     session.add_all([game1, player1, player_game])
    # await session.refresh(player_game)
    # print(player_game.id)
    # quest1 = src.Quest(start_time=src.datetime.now(), end_time=src.datetime.now(), status="running", task_id=task.id)
    # session.add(quest1)

    # result = await session.execute(
    #     src.select(src.Player.name, src.Player.hours, src.Player.dc_id)
    # )
    # player = result.fetchall()
    # for p in player:
    #     print(p.name, str(p.hours), p.dc_id)
    # player = (
    #         await session.execute(
    #             src.select(src.Player).filter(src.Player.dc_id == player1.dc_id)
    #         )
    #     ).scalar_one_or_none()
    # print(player1)
    # print(player)
    # player1 = src.Player(
    #     name="Luni",
    #     dc_id="2234567890",
    #     hours=2,
    # )
    # player2 = src.Player(
    #     name="JoJo",
    #     dc_id="1234567890",
    #     hours=123,
    # )
    # game = src.Game(
    #     name="Among Us",
    #     status="running",
    #     timestamp=datetime.now(),
    # )

    # association1 = src.GamePlayerAssociation(game=game, player=player1)
    # association2 = src.GamePlayerAssociation(game=game, player=player2)

    # session.add_all([player1, player2, game, association1, association2])
    # await session.commit()


async def background_task():
    """
    Background test task that runs in parallel to the main task.
    """
    while True:
        print("Test task runs...")
        await asyncio.sleep(10)


async def main():
    """
    Scheduling function for regular call.
    """
    config = src.Configuration()
    src.watcher.init_logging(config)
    config.db.initialize_db()
    await src.sync_db(config.db.engine)
    src.watcher.logger.info(f"Start application in version: {src.__version__}")
    await src.generate_league_table(config) # TODO: activate for release
    discord_bot = src.DiscordBot(config)
    tasks = [discord_bot.start()]
    # tasks.append(background_task())
    # tasks.append(onlyonce(config))
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
