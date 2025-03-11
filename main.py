"""
Main function for starting application
"""
import asyncio
import src


async def main():
    """
    Scheduling function for regular call.
    """
    config = src.Configuration()
    src.watcher.init_logging(config.watcher.log_level)
    config.db.initialize_db()
    await src.sync_db(config.db.engine)
    src.watcher.logger.info(f"Start application in version: {src.__version__}")


if __name__ == "__main__":
    asyncio.run(main())
