"""
Main function for starting application
"""

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

    tasks = [src.sync_db(config.db.engine), src.discord_bot.bot.start(config.dc.token)]
    tasks.append(background_task())
    await asyncio.gather(*tasks)

    # async with config.db.session() as session:
    #     user = src.Items(
    #         name="test user",
    #         type="test",
    #         stackable=1,
    #         floatable="test",
    #         acquisition="test",
    #         rating=1,
    #         craftable="test",
    #     )
    #     session.add(user)
    #     await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
