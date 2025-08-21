"""All functions related to track reactions for each game"""

import datetime
from discord.raw_models import RawReactionActionEvent
from discord.ext.commands.bot import Bot as DiscordBot
from .db import (
    get_games_f_reaction,
    get_all_game_x_player_from_message_id,
    insert_db_obj,
    get_all_db_obj_from_id,
    update_db_obj,
    get_reaction,
    set_reaction_status,
)
from .db import Reaction, Player, GameStatus, ReactionStatus
from .configuration import Configuration
from .game import game_configs

# reaction_lock = asyncio.Lock()
# allowed_game_messages = []


async def remove_reaction(
    bot: DiscordBot, config: Configuration, payload: RawReactionActionEvent
) -> None:
    """
    Function load all necessary informations and remove the reaction from the message.

    Args:
        bot (DiscordBot): Discord bot instance
        config (Configuration): App configuration
        payload (RawReactionActionEvent): payload information from reaction event
    """
    try:
        config.watcher.logger.debug(
            f"Removing reaction: {payload.emoji.name} from user: {payload.user_id} "
            + f"on message ID: {payload.message_id} in channel ID: {payload.channel_id}"
        )
        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        member = await bot.fetch_user(payload.user_id)
        await message.remove_reaction(payload.emoji, member)
    except TypeError as err:
        config.watcher.logger.error(f"TypeError during reaction tracker: {err}")


async def schedule_reaction_tracker_add(
    bot: DiscordBot, config: Configuration, payload: RawReactionActionEvent
):
    """
    General function to handle the addition of a reaction to a message.

    Args:
        bot (DiscordBot): Discord bot instance to interact with Discord API
        config (Configuration): App configuration
        payload (RawReactionActionEvent): Payload information from reaction event
    """
    try:
        config.watcher.logger.trace(f"Reaction add check: {datetime.datetime.now()}")
        config.watcher.logger.debug(
            f"Reaction add: {payload.emoji.name}, "
            + f"User: {payload.member} / {payload.user_id}, Message ID: {payload.message_id} "
            + f"Channel ID {payload.channel_id}"
        )
        games = await get_games_f_reaction(config)
        reaction = await insert_db_obj(
            config,
            Reaction(
                dc_id=payload.user_id,
                status=ReactionStatus.NEW,
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
            game_x_player = await get_all_game_x_player_from_message_id(
                config, payload.message_id
            )
            if game_x_player:
                game_emojis = game_configs.get(game_x_player.name, []).game_emojis
                player = await get_all_db_obj_from_id(
                    config,
                    Player,
                    [player.player_id for player in game_x_player.players],
                )
                player_dc_ids = [int(player.dc_id) for player in player]
                game_status = game_x_player.status
                game_id = game_x_player.id

                match game_status:
                    case GameStatus.CREATED | GameStatus.PAUSED if (
                        payload.emoji.name in game_emojis
                    ):
                        config.watcher.logger.debug(
                            "Delete reaction because of status. "
                            + f"Reaction-ID:{reaction.id}, Game-ID: {game_x_player.id}"
                        )
                        reaction.status = ReactionStatus.DELETED_STATUS
                        reaction.game_id = game_id
                        await update_db_obj(config, reaction)
                        await remove_reaction(bot, config, payload)
                    case GameStatus.RUNNING if (
                        payload.emoji.name in game_emojis
                        and payload.user_id in player_dc_ids
                    ):
                        config.watcher.logger.debug(
                            "Reaction registered. "
                            + f"Reaction-ID:{reaction.id}, Game-ID: {game_x_player.id}"
                        )
                        reaction.status = ReactionStatus.REGISTERED
                        reaction.game_id = game_id
                        await update_db_obj(config, reaction)
                    case GameStatus.RUNNING if (
                        payload.emoji.name in game_emojis
                        and payload.user_id not in player_dc_ids
                    ):
                        config.watcher.logger.debug(
                            "Delete reaction because of player. "
                            + f"Reaction-ID:{reaction.id}, Game-ID: {game_x_player.id}."
                        )
                        reaction.status = ReactionStatus.DELETED_PLAYER
                        reaction.game_id = game_id
                        await update_db_obj(config, reaction)
                        await remove_reaction(bot, config, payload)
                    case _ if payload.emoji.name not in game_emojis:
                        config.watcher.logger.debug(
                            "Support reaction. "
                            + f"Reaction-ID:{reaction.id}, Game-ID: {game_x_player.id}."
                        )
                        reaction.status = ReactionStatus.SUPPORTER
                        reaction.game_id = game_id
                        await update_db_obj(config, reaction)
                    case _:
                        config.watcher.logger.debug(
                            "Reaction not matching game status or emoji. "
                            + f"Reaction-ID:{reaction.id}, Game-ID: {game_x_player.id}"
                        )
                        reaction.status = ReactionStatus.REVIEW
                        reaction.game_id = game_id
                        await update_db_obj(config, reaction)

    except TypeError as err:
        config.watcher.logger.error(f"TypeError during reaction tracker: {err}")


async def schedule_reaction_tracker_remove(
    config: Configuration, payload: RawReactionActionEvent
):
    """
    General function to handle removal of a reaction from a message.

    Args:
        config (Configuration): App configuration
        payload (RawReactionActionEvent): Payload information from reaction event
    """
    config.watcher.logger.debug(
        f"Reaction removed: {payload.emoji.name}, "
        + f"from user: {payload.user_id}, Message ID: {payload.message_id} "
        + f"Channel ID {payload.channel_id}"
    )
    reactions = await get_reaction(
        config, payload.message_id, payload.user_id, payload.emoji.name
    )
    config.watcher.logger.debug(
        f"Reactions found: {[reaction.id for reaction in reactions]}"
    )
    await set_reaction_status(config, reactions, ReactionStatus.REMOVED)
