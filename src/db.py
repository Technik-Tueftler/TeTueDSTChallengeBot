"""All database related functions are here."""

import random
from enum import Enum
from typing import Set
from datetime import datetime
from sqlalchemy import ForeignKey, func
from sqlalchemy import Enum as AlchemyEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from .configuration import Configuration


class ReactionStatus(Enum):
    """Enum for reaction status"""

    NEW: int = 0
    DELETED_STATUS: int = 1
    DELETED_PLAYER: int = 2
    REGISTERED: int = 3
    SUPPORTER: int = 4


class GameStatus(Enum):
    """Enum for game status"""

    CREATED: int = 0
    RUNNING: int = 1
    PAUSED: int = 2
    STOPPED: int = 3
    FINISHED: int = 4

    @property
    def icon(self):
        """
        Status assignment icon
        """
        icons = {
            GameStatus.CREATED: "🆕",
            GameStatus.RUNNING: "🎮",
            GameStatus.PAUSED: "⏸️",
            GameStatus.STOPPED: "⏹️",
            GameStatus.FINISHED: "🏁",
        }
        return icons[self]


class Base(DeclarativeBase):
    """Declarative base class

    Args:
        DeclarativeBase (_type_): Basic class that is inherited
    """


class GamePlayerAssociation(Base):
    """
    _summary_

    Args:
        Base (_type_): _description_
    """

    __tablename__ = "game_player_association"
    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    game = relationship("Game", back_populates="players")
    player = relationship("Player", back_populates="games")
    quests = relationship("Quest", back_populates="gameplayerassociation")
    rank = relationship("Rank", back_populates="gameplayerassociation")


class Player(Base):
    """
    _summary_

    Args:
        Base (_type_): _description_
    """

    __tablename__ = "players"
    id: Mapped[int] = mapped_column(primary_key=True)
    dc_id: Mapped[str] = mapped_column()
    name: Mapped[str] = mapped_column(nullable=False)
    hours: Mapped[int] = mapped_column()
    games = relationship("GamePlayerAssociation", back_populates="player")
    league = relationship("League", back_populates="player", uselist=False)

    def __repr__(self) -> str:
        return f"Name: {self.name!r}, Playtime:{str(self.hours)!r})"


class League(Base):
    """League table

    Args:
        Base (_type_): Basic class that is inherited
    """

    __tablename__ = "league"
    id: Mapped[int] = mapped_column(primary_key=True)
    points: Mapped[int] = mapped_column(nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    survived: Mapped[int] = mapped_column(nullable=False)
    player: Mapped[Player] = relationship(
        "Player", back_populates="league", lazy="joined"
    )

    def __repr__(self) -> str:
        return (
            f"Player: {self.player_id!r} / "
            f"Place: {self.id!r} / "
            f"points:{self.points!r} / "
            f"survived:{self.survived!r})"
        )


class Rank(Base):
    """List of ranks for each player per game

    Args:
        Base (_type_): Basic class that is inherited
    """

    __tablename__ = "ranks"
    id: Mapped[int] = mapped_column(primary_key=True)
    placement: Mapped[int] = mapped_column(nullable=True)
    points: Mapped[int] = mapped_column(nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    survived: Mapped[int] = mapped_column(nullable=False)
    game_player_association_id: Mapped[int] = mapped_column(
        ForeignKey("game_player_association.id")
    )
    gameplayerassociation = relationship("GamePlayerAssociation", back_populates="rank")


class Game(Base):
    """Game table

    Args:
        Base (_type_): Basic class that is inherited
    """

    __tablename__ = "games"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[GameStatus] = mapped_column(
        AlchemyEnum(GameStatus), default=GameStatus.CREATED
    )
    playing_days: Mapped[int] = mapped_column(default=70)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    message_id: Mapped[str] = mapped_column(nullable=True)
    channel_id: Mapped[int] = mapped_column(nullable=True)
    players = relationship("GamePlayerAssociation", back_populates="game")

    def __repr__(self) -> str:
        return f"ID: {self.id!r}"


class Items(Base):
    """Items table

    Args:
        Base (_type_): Basic class that is inherited
    """

    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    type: Mapped[str] = mapped_column()
    stackable: Mapped[int] = mapped_column()
    floatable: Mapped[str] = mapped_column()
    acquisition: Mapped[str] = mapped_column()
    rating: Mapped[int] = mapped_column()
    craftable: Mapped[str] = mapped_column()

    def __repr__(self) -> str:
        return f"Name: {self.name!r}, rate:{self.rating!r})"


class Exercise(Base):
    """
    Exercise table

    Args:
        Base (_type_): Basic class that is inherited
    """

    __tablename__ = "exercises"
    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))


class Quest(Base):
    """Quests table

    Args:
        Base (_type_): Basic class that is inherited
    """

    __tablename__ = "quests"
    id: Mapped[int] = mapped_column(primary_key=True)
    start_time: Mapped[datetime] = mapped_column(nullable=False)
    end_time: Mapped[datetime] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=False)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    position: Mapped[int] = mapped_column(nullable=False)
    game_player_association_id: Mapped[int] = mapped_column(
        ForeignKey("game_player_association.id")
    )

    task = relationship("Task", back_populates="quests")
    gameplayerassociation = relationship(
        "GamePlayerAssociation", back_populates="quests"
    )


class Task(Base):
    """Task table

    Args:
        Base (_type_): Basic class that is inherited
    """

    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    active: Mapped[bool] = mapped_column(default=True)
    once: Mapped[bool] = mapped_column(default=False)
    rating: Mapped[int] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    language: Mapped[str] = mapped_column(nullable=True)
    game: Mapped[int] = mapped_column(nullable=False)
    type: Mapped[str] = mapped_column(nullable=False)

    quests = relationship("Quest", back_populates="task")

    def __repr__(self) -> str:
        return f"Name: {self.name!r}, rate:{self.rating!r})"


class Reaction(Base):
    """Reaction table

    Args:
        Base (_type_): Basic class that is inherited
    """

    __tablename__ = "reactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    dc_id: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[ReactionStatus] = mapped_column(
        AlchemyEnum(ReactionStatus), default=ReactionStatus.NEW
    )
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))


async def get_player(config, player_id: int) -> Player | None:
    """
    Function to get a player from the database by dc_id

    Args:
        config (_type_): App configuration
        player (Player): Player object to search for

    Returns:
        Player: Player object from the database or None if not found
    """
    async with config.db.session() as session:
        async with session.begin():
            player = (
                await session.execute(select(Player).filter(Player.id == player_id))
            ).scalar_one_or_none()
    return player


async def get_game_from_id(config: Configuration, game_id: str) -> Game | None:
    """
    Function to get a game from the database by id

    Args:
        config (Configuration): App configuration
        game_id (str): Game id from DB

    Returns:
        Game: Game object from the database or None if not found
    """
    async with config.db.session() as session:
        async with session.begin():
            player = (
                await session.execute(select(Game).filter(Game.id == game_id))
            ).scalar_one_or_none()
    return player


async def process_player(
    config: Configuration, player_list: list[Player]
) -> list[Player]:
    """
    Function to process a player list and add them to the database if they are not already there.
    Also update the hours of a player if there are new values.

    Args:
        config (_type_): _description_
        player_list (list[Player]): List of players to process

    Returns:
        list[Player]: processed player list
    """
    processed_player_list = []
    async with config.db.write_lock:
        async with config.db.session() as session:
            for p in player_list:
                async with session.begin():
                    player = (
                        await session.execute(
                            select(Player).filter(Player.dc_id == p.dc_id)
                        )
                    ).scalar_one_or_none()
                    if player is None:
                        session.add(p)
                        # Nicht benötigt da Transaktionsblock .begin() auto. mit commit beendet wird
                        # await session.commit()
                        processed_player_list.append(p)
                        config.watcher.logger.info(
                            f"Player {p.name} added to the database."
                        )
                    else:
                        if p.hours != 0:
                            player.hours = p.hours
                            # await session.commit()
                        processed_player_list.append(player)
    return processed_player_list


async def create_game(config, game_name: str, player: list[Player]) -> Game:
    """
    Function to create a game in the database and link all players to the game.

    Args:
        config (_type_): _description_
        game_name (str): Game name
        player (list[Player]): All players in the game

    Returns:
        Game: Object of the created game for further processing
    """
    try:
        async with config.db.write_lock:
            async with config.db.session() as session:
                async with session.begin():
                    game = Game(
                        name=game_name,
                        timestamp=datetime.now(),
                    )
                    session.add(game)
                    associations = [
                        GamePlayerAssociation(game=game, player=p) for p in player
                    ]
                    session.add_all(associations)
                await session.refresh(game)
                return game
    except IntegrityError as err:
        config.watcher.logger.error(f"Integrity error {str(err)}")
    except SQLAlchemyError as err:
        config.watcher.logger.error(f"Database error: {str(err)}", exc_info=True)


async def get_games_w_status(
    config: Configuration, status: list[GameStatus]
) -> list[Game]:
    """
    This function get all changeable games back. Games that have the status
    CREATED, RUNNING or PAUSED can be changed.

    Args:
        config (Configuration): App configuration

    Returns:
        list[Game]: The list if changeable games
    """
    async with config.db.session() as session:
        async with session.begin():
            games = (
                (await session.execute(select(Game).where(Game.status.in_(status))))
                .scalars()
                .all()
            )
    return games


async def get_games_f_reaction(config: Configuration) -> list[Game] | None:
    """
    _summary_

    Args:
        config (Configuration): app configuration

    Returns:
        list[Game] | None: valid games to track reactions or None if no games found
    """
    try:
        async with config.db.session() as session:
            async with session.begin():
                games = (
                    (
                        await session.execute(
                            select(Game).where(
                                Game.status.not_in(
                                    [GameStatus.FINISHED, GameStatus.STOPPED]
                                ),
                                Game.channel_id.is_not(None),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
        return games
    except Exception as err:
        config.watcher.logger.error(
            f"Error while getting games for reaction: {str(err)}", exc_info=True
        )
        return []


async def get_random_tasks(
    config: Configuration, limit: int, rating_min: int = 0, rating_max: int = 101
) -> list[Task]:
    """
    This function gets a list of random tasks from the database.
    The number of tasks is limited by the limit parameter.

    Args:
        config (Configuration): App configuration
        limit (int): number of tasks to get

    Returns:
        list[Task]: Tasks from the database
    """
    async with config.db.session() as session:
        return (
            (
                await session.execute(
                    select(Task)
                    .where(Task.rating >= rating_min)
                    .where(Task.rating < rating_max)
                    .order_by(func.random())  # pylint: disable=not-callable
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )


async def get_main_task(config: Configuration) -> Task:
    """
    Funktion to get a random main task from the database for game 1

    Args:
        config (Configuration): App configuration

    Returns:
        Task: main task
    """
    async with config.db.session() as session:
        return (
            await session.execute(
                select(Task)
                .where(Task.type == "main")
                .order_by(func.random())  # pylint: disable=not-callable
                .limit(1)
            )
        ).scalar_one_or_none()


async def get_tasks_based_on_rating_1(config: Configuration, rating: int) -> list[Task]:
    """
    This function gets a list of tasks from the database based on the rating for game 1.
    The rating is used to filter the tasks.

    Args:
        config (Configuration): App configuration
        rating (int): rating to filter the tasks from 0 to 100

    Returns:
        list[Task]: Tasks from the database
    """
    async with config.db.session() as session:
        for _ in range(6):
            tasks = (
                (
                    await session.execute(
                        select(Task)
                        .filter(Task.rating <= rating)
                        .filter(Task.type == "task")
                        .order_by(Task.rating.desc())
                    )
                )
                .scalars()
                .all()
            )

            if len(tasks) >= 5:
                return tasks
            rating += 5
    return []


async def get_tasks_sort_hard(tasks: list[Task], number_of_tasks=5) -> list[Task]:
    """
    Get the top tasks based on their rating sorted by hardness (highest rating first).

    Args:
        tasks (list[Task]): List of Task objects to sort.
        number_of_tasks (int, optional): Number of tasks to return. Defaults to 5.

    Returns:
        list[Task]: Sorted list of Task objects, limited to the specified number of tasks.
    """
    tasks.sort(key=lambda x: x.rating, reverse=True)
    return tasks[:number_of_tasks]


async def get_tasks_sort_soft(tasks: list[Task], number_of_tasks=5) -> list[Task]:
    """
    Get the top tasks based on their rating sorted by hardness (lowest rating first).

    Args:
        tasks (list[Task]): List of Task objects to sort.
        number_of_tasks (int, optional): Number of tasks to return. Defaults to 5.

    Returns:
        list[Task]: Sorted list of Task objects, limited to the specified number of tasks.
    """
    tasks.sort(key=lambda x: x.rating)
    return tasks[:number_of_tasks]


async def balanced_task_mix(tasks: list[Task], number_of_tasks=5) -> list[Task]:
    """
    This function creates a balanced task mix from the list of tasks.
    The tasks are sorted by rating and the list is divided into equal parts.
    There is one task from each of the different difficulty levels.

    Returns:
        list[Task]: Balanced task mix
    """
    tasks.sort(key=lambda x: x.rating)
    step = len(tasks) // number_of_tasks
    return [tasks[i * step] for i in range(number_of_tasks)]


async def balanced_task_mix_random(
    config: Configuration, tasks: list[Task], exclude_ids: Set[int]
) -> list[Task]:
    """
    This function creates a balanced random task mix from the list of tasks.
    The tasks are sorted by rating and the list is divided into equal parts.
    There is one task from each of the different difficulty levels.

    Returns:
        list[Task]: Balanced task mix
    """
    try:
        sorted_tasks = [[] for _ in range(5)]
        for task in tasks:
            group = min(task.rating // 20, 4)
            sorted_tasks[group].append(task)

        list_counter = 1
        selected_task = []

        for grouped_tasks in reversed(sorted_tasks):
            if not grouped_tasks:
                list_counter += 1
                continue
            filtered_tasks = [t for t in grouped_tasks if t.id not in exclude_ids]
            n = min(list_counter, len(filtered_tasks))
            selected_task.extend(
                random.sample(filtered_tasks, n)  # pylint: disable=no-member
            )
            exclude_ids.update(t.id for t in selected_task if t.once)
            list_counter -= n
            if list_counter <= 0:
                list_counter = 1

        return selected_task
    except (TypeError, AttributeError, ValueError, IndexError, KeyError) as err:
        config.watcher.logger.error(f"{str(err)}", exc_info=True)
        return []


async def update_db_obj(config: Configuration, obj: Game | Player | Exercise) -> None:
    """
    Function to update a game or player object in the database

    Args:
        config (_type_): configuration
        obj (Game | Player): Object to update in the database
    """
    async with config.db.write_lock:
        async with config.db.session() as session:
            async with session.begin():
                session.add(obj)


async def sync_db(engine: AsyncEngine):
    """
    Function to run the sync command and create all DB dependencies and tables

    Args:
        engine (AsyncEngine): The engine to run the sync command
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
