import discord
import pandas as pd
from .configuration import Configuration
from .db import Task

positive_args = ("y", "yes", "1", "true", "j", "ja")

async def check_rows(interaction: discord.Interaction):
    ...

async def load_tasks(interaction: discord.Interaction, config: Configuration):
    try:
        df = pd.read_excel(config.game.input_task_path)
        new_tasks = []
        failed_rows = []
        for index, row in df.iterrows:
            if "NaN" in (row["name"], row["game"], row["type"]):
                failed_rows.append(index)
                continue
            temp_task = Task(
                name=row["name"],
                active=row["active"] in positive_args,
                once=row["once"] in positive_args,
                rating=row["rating"] if row["rating"] != "NaN" else 0,
                description=row["description"],
                language=row["language"],
                game=row["game"],
                type=row["type"]
            )
            new_tasks.append(temp_task)
            async with config.db.session() as session:
                async with session.begin():
                    session.add_all(new_tasks)
        # print(df.head(10))
        await interaction.response.send_message(
            "read excel and ...",
            ephemeral=True)
    except Exception as e:
        print(e)
