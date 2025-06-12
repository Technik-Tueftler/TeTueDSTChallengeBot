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
    src.watcher.init_logging(config)
    config.db.initialize_db()
    await src.sync_db(config.db.engine)
    src.watcher.logger.info(f"Start application in version: {src.__version__}")
    await src.generate_league_table(config)
    discord_bot = src.DiscordBot(config)
    tasks = [discord_bot.start()]
    # tasks.append(background_task())
    # tasks.append(onlyonce(config))
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
