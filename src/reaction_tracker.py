"""All functions related to track reactions for each game"""
import datetime

async def schedule_reaction_tracker(config):
    """
    Function to schedule the reaction tracker.
    This function calls all necessary functions to admin reactions for each game.
    """
    config.watcher.logger.track(f"Reaction check: {datetime.datetime.now()}")
