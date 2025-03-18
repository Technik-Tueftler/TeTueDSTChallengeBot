"""
Main function for starting application
"""

import asyncio
import src


async def background_task():
    while True:
        print("Hintergrundtask läuft...")
        await asyncio.sleep(10)

async def main():
    """
    Scheduling function for regular call.
    """
    config = src.Configuration()
    src.watcher.init_logging(config.watcher.log_level)
    config.db.initialize_db()
    src.watcher.logger.info(f"Start application in version: {src.__version__}")
    await asyncio.gather(
        src.sync_db(config.db.engine),
        src.discord_bot.bot.start(config.dc.token),
        background_task()
    )

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
