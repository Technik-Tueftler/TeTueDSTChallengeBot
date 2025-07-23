"""All functions related to track reactions for each game"""

import datetime
from discord.raw_models import RawReactionActionEvent
from .db import (
    get_games_f_reaction,
    get_all_gameXplayer_from_message_id,
    insert_db_obj,
    get_all_db_obj_from_id,
)
from .db import Reaction, Player, GameStatus
from .configuration import Configuration
from .game import all_game_emoji

# reaction_lock = asyncio.Lock()
# allowed_game_messages = []


async def schedule_reaction_tracker(
    config: Configuration, payload: RawReactionActionEvent
):
    """
    Function to schedule the reaction tracker.
    This function calls all necessary functions to admin reactions for each game.
    """
    try:
        config.watcher.logger.trace(f"Reaction check: {datetime.datetime.now()}")
        config.watcher.logger.debug(
            f"Reaction: {payload.emoji.name}, "
            + f"User: {payload.member} / {payload.user_id}, Message ID: {payload.message_id}"
        )
        games = await get_games_f_reaction(config)
        reaction = await insert_db_obj(
            config,
            Reaction(
                dc_id=payload.user_id,
                status="NEW",
                timestamp=datetime.datetime.now(),
                message_id=payload.message_id,
                channel_id=payload.channel_id,
                emoji=payload.emoji.name,
            ),
        )
        config.watcher.logger.debug(f"Reaction inserted: {reaction}")

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
            if game_x_player:
                game_emojis = all_game_emoji.get(game_x_player.name, [])
                player = await get_all_db_obj_from_id(
                    config,
                    Player,
                    [player.player_id for player in game_x_player.players],
                )
                player_dc_ids = [int(player.dc_id) for player in player]
                game_status = game_x_player.status

                match game_status:
                    case GameStatus.CREATED | GameStatus.PAUSED if payload.emoji.name in game_emojis:
                        config.watcher.logger.debug(f"Delete reaction because of status. Reaction-ID:{reaction.id}, Game-ID: {game_x_player.id}")
                    case GameStatus.RUNNING if payload.emoji.name in game_emojis and payload.user_id in player_dc_ids:
                        print("Emoji and user ID match for game reaction")
                        # -> registered
                    case GameStatus.RUNNING if payload.emoji.name in game_emojis and payload.user_id not in player_dc_ids:
                        config.watcher.logger.debug(f"Delete reaction because of player. Reaction-ID:{reaction.id}.")
                    case GameStatus.RUNNING if payload.emoji.name not in game_emojis:
                        config.watcher.logger.debug(f"Support reaction. Reaction-ID:{reaction.id}.")
                    case _:
                        print(f"No matching emoji or user ID for game reaction: {payload.emoji.name}, {payload.user_id}")

                # if payload.emoji.name in game_emojis:
                #     if payload.user_id in player_dc_ids:
                #
                # print(f"Game: {game_x_player.id}, Players: {[player.player_id for player in game_x_player.players]}")

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
