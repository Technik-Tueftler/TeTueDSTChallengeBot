"""
Main function for starting application
"""
from datetime import datetime
import asyncio
import src


async def onlyonce(config):
    """
    Only a test function to create a game and player in the database.
    This function is not used in the main application and is only for testing and
    would be removed in the final version.
    """
    player1 = src.Player(name="technik_tueftler", dc_id="722546721430700314", hours=0)
    async with config.db.session() as session:
        async with session.begin():
            result = await session.execute(src.select(src.Player.name, src.Player.hours, src.Player.dc_id))
            player = result.fetchall()
            for p in player:
                print(p.name, str(p.hours), p.dc_id)
            # player = (
            #         await session.execute(
            #             src.select(src.Player).filter(src.Player.dc_id == player1.dc_id)
            #         )
            #     ).scalar_one_or_none()
            print(player1)
            print(player)
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
    discord_bot = src.DiscordBot(config)
    tasks = [discord_bot.start()]
    tasks.append(background_task())
    # tasks.append(onlyonce(config))
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
