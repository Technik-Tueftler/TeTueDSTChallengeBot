"""All functions related to track reactions for each game"""
import asyncio
import datetime
from .db import get_games_f_reaction
from .configuration import Configuration

# reaction_lock = asyncio.Lock()
# allowed_game_messages = []

async def schedule_reaction_tracker(config: Configuration, reaction, user):
    """
    Function to schedule the reaction tracker.
    This function calls all necessary functions to admin reactions for each game.
    """
    try:
        config.watcher.logger.trace(f"Reaction check: {datetime.datetime.now()}")
        print(f"Benutzer: {user.name}, Reaktion: {reaction.emoji}, Message-ID: {reaction.message.id}")
        # async with reaction_lock:
        # games = await get_games_f_reaction(config)
        allowed_message_ids = [game.message_id for game in games if game.message_id]
        if reaction.message.id in allowed_message_ids:
            games = await get_games_f_reaction(config)


        # for game in games:
        #     channel = bot.get_channel(game.channel_id)
        #     if channel is None:
        #         continue
        #     message = await channel.fetch_message(game.message_id)
        #     for reaction in message.reactions:
        #         print(f"Reaction: {reaction.emoji} - {reaction.count}, Users: {reaction.}")
    except Exception as err:
        config.watcher.logger.error(f"Error during reaction tracker: {err}")
        # message = await channel.fetch_message(MESSAGE_ID)
        # for reaction in message.reactions:
        #     if str(reaction.emoji) not in positions_game_1:
        #         async for user in reaction.users():
        #             await message.remove_reaction(reaction.emoji, user)
        #     else:
        #         async for user in reaction.users():
        #             if user.id not in ALLOWED_USER_IDS:
        #                 await message.remove_reaction(reaction.emoji, user)
