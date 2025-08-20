"""
Here are all the functions needed to import and synchronize important game
information from the game master.
"""
import os
from pathlib import Path
from datetime import datetime
import discord
import pandas as pd
from sqlalchemy.future import select
from .configuration import Configuration
from .db import Task

positive_args = ("y", "yes", "1", "true", "j", "ja")


async def check_rows(config: Configuration, row: pd.core.series.Series):
    """
    function checks whether all contents of the columns are filled with
    the correct type. If the required information is empty, the row cannot be read in.

    Args:
        config (Configuration): App configuration
        row (pd.core.series.Series): Row with information
    """
    try:
        return (
            isinstance(row["name"], str)
            and isinstance(row["game"], int)
            and isinstance(row["type"], str)
            and isinstance(row["description"], str)
            and isinstance(row["active"], str)
            and isinstance(row["once"], str)
        )
    except (KeyError, TypeError) as err:
        config.watcher.logger.error(f"Validation error: {err}")


async def check_updated(config: Configuration, row: pd.core.series.Series):
    """
    This this function checks whether the entry already exists for a task.
    The name of the task is used for this check. If an entry with the same
    name already exists, it is overwritten with the new information. If it
    does not yet exist in the database, it is created.

    Args:
        config (Configuration): App configuration
        row (pd.core.series.Series): Row with information
    """
    async with config.db.session() as session:
        async with session.begin():
            task = (
                (await session.execute(select(Task).filter(Task.name == row["name"])))
                .scalars()
                .first()
            )
            if task is not None:
                task.name = "test"
                task.name = row["name"]
                task.active = (row["active"]).lower() in positive_args
                task.once = (row["once"]).lower() in positive_args
                task.rating = row["rating"]
                task.description = row["description"]
                task.language = row["language"]
                task.game = row["game"]
                task.type = row["type"]
    if task is None:
        return False
    return True


async def import_tasks(interaction: discord.Interaction, config: Configuration):
    """
    Scheduling function for importing new tasks in the datebase or updating existing.

    Args:
        interaction (discord.Interaction): Interaction object to get the guild
        config (Configuration): App configuration
    """
    try:
        config.watcher.logger.debug("Reading tasks from file")
        config.watcher.logger.debug(f"File path: {config.game.input_task_path}")
        config.watcher.logger.debug(f"Working directory: {os.getcwd()}")
        new_tasks = []
        failed_rows = []
        updated_rows = []
        df = pd.read_excel(config.game.input_task_path)
        df["rating"] = df["rating"].fillna(0)
        for index, row in df.iterrows():
            if not await check_rows(config, row):
                failed_rows.append(index)
                continue
            if await check_updated(config, row):
                updated_rows.append(index)
                continue
            temp_task = Task(
                name=row["name"],
                active=(row["active"]).lower() in positive_args,
                once=(row["once"]).lower() in positive_args,
                rating=row["rating"],
                description=row["description"],
                language=row["language"],
                game=row["game"],
                type=row["type"],
            )
            new_tasks.append(temp_task)
            async with config.db.session() as session:
                async with session.begin():
                    session.add_all(new_tasks)
        message = f"Reading completed, {len(new_tasks)} Tasks created."
        if failed_rows:
            message += (
                " There was a problem with the following entries: "
                f"{", ".join(str(x+2) for x in failed_rows)}. "
                "Check types and follow the documentation."
            )
        if updated_rows:
            message += (
                " Entries are already in the database and updated: "
                f"{", ".join(str(x+2) for x in updated_rows)}."
            )
        await interaction.response.send_message(message, ephemeral=True)
    except (KeyError, TypeError) as err:
        config.watcher.logger.error(f"Validation error: {err}")
    except Exception as err:
        config.watcher.logger.error(f"Error during import: {err}")


async def export_tasks(interaction: discord.Interaction, config: Configuration):
    """
    Scheduling function for exporting existing tasks from datebase.

    Args:
        interaction (discord.Interaction): Interaction object to get the guild
        config (Configuration): App configuration
    """
    try:
        config.watcher.logger.debug("Exporting tasks from file")
        config.watcher.logger.debug(f"File path: {config.game.export_task_path}")
        config.watcher.logger.debug(f"Working directory: {os.getcwd()}")
        async with config.db.session() as session:
            async with session.begin():
                tasks = (await session.execute(select(Task))).scalars().all()
        data = [
            {
                "name": task.name,
                "active": "yes" if task.active else "No",
                "once": "yes" if task.once else "No",
                "rating": task.rating,
                "description": task.description,
                "language": task.language,
                "game": task.game,
                "type": task.type,
            }
            for task in tasks
        ]
        df = pd.DataFrame(data)
        date = datetime.now().strftime("%Y_%m_%d")
        path_file = Path("files") / f"{date}_tasks.xlsx"
        df.to_excel(path_file, index=False)
        await interaction.response.send_message(
            f"Export is generated and saved: {path_file}.", ephemeral=True
        )
    except discord.errors.Forbidden as err:
        config.watcher.logger.error(f"Error during callback with DC permissons: {err}")
