"""
Main function for starting application
"""
from datetime import datetime
import asyncio
import src


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
    src.watcher.init_logging(config.watcher.log_level)
    config.db.initialize_db()
    src.watcher.logger.info(f"Start application in version: {src.__version__}")

    async with config.db.session() as session:
        player1 = src.Player(
            name="Luni",
            hours=2,
        )
        player2 = src.Player(
            name="JoJo",
            hours=123,
        )
        game = src.Game(
            name="Among Us",
            status="running",
            timestamp=datetime.now(),
        )

        association1 = src.GamePlayerAssociation(game=game, player=player1)
        association2 = src.GamePlayerAssociation(game=game, player=player2)

        session.add_all([player1, player2, game, association1, association2])
        await session.commit()
        # user = src.Items(
        #     name="test user 2",
        #     type="test",
        #     stackable=1,
        #     floatable="test",
        #     acquisition="test",
        #     rating=1,
        #     craftable="test",
        # )
        # session.add(user)
        # await session.commit()

    tasks = [src.sync_db(config.db.engine), src.discord_bot.bot.start(config.dc.token)]
    tasks.append(background_task())
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
