"""All functions related to track reactions for each game"""

import asyncio
import datetime
from discord.raw_models import RawReactionActionEvent
from .db import get_games_f_reaction, get_all_gameXplayer_from_message_id
from .configuration import Configuration

# reaction_lock = asyncio.Lock()
# allowed_game_messages = []


async def schedule_reaction_tracker(config: Configuration, payload: RawReactionActionEvent):
    """
    Function to schedule the reaction tracker.
    This function calls all necessary functions to admin reactions for each game.
    """
    try:
        print(type(payload))
        config.watcher.logger.trace(f"Reaction check: {datetime.datetime.now()}")
        config.watcher.logger.debug(
            f"Reaction: {payload.emoji}, User: {payload.user_id}, Message ID: {payload.message_id}"
        )
        games = await get_games_f_reaction(config)
        allowed_message_ids = [
            int(game.message_id) for game in games if game.message_id
        ]
        config.watcher.logger.trace(
            f"Allowed messages for reactions: {allowed_message_ids}"
        )
        if payload.message_id in allowed_message_ids:
            game_x_player = await get_all_gameXplayer_from_message_id(
                config, payload.message_id
            )
            for game in game_x_player:
                print(type(game))
                print(f"Game: {game.id}, Players: {[player.player_id for player in game.players]}")

        # for game in games:
        #     channel = bot.get_channel(game.channel_id)
        #     if channel is None:
        #         continue
        #     message = await channel.fetch_message(game.message_id)
        #     for reaction in message.reactions:
        #         print(f"Reaction: {reaction.emoji} - {reaction.count}, Users: {reaction.}")
    except TypeError as err:
        config.watcher.logger.error(f"TypeError during reaction tracker: {err}")
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
