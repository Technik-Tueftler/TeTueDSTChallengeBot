"""All database related functions are here."""

from enum import Enum, auto
from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy import Enum as AlchemyEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError


class GameStatus(Enum):
    """Enum for game status"""

    CREATED = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPED = auto()
    FINISHED = auto()


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

    def __repr__(self) -> str:
        return f"Name: {self.name!r}, Playtime:{str(self.hours)!r})"


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
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    message_id: Mapped[str] = mapped_column(nullable=True)
    players = relationship("GamePlayerAssociation", back_populates="game")


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
    description: Mapped[str] = mapped_column(nullable=False)
    difficulty: Mapped[int] = mapped_column(nullable=False)

    quests = relationship("Quest", back_populates="task")


async def get_player(config, player: Player) -> Player:
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
                await session.execute(
                    select(Player).filter(Player.dc_id == player.dc_id)
                )
            ).scalar_one_or_none()
    return player


async def process_player(config, player_list: list[Player]) -> list[Player]:
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
                    # await session.commit() <- Nicht benötigt da Transaktionsblock .begin() automatisch mit commit beendet wird
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
        async with config.db.session() as session:
            async with session.begin():
                game = Game(
                    name=game_name,
                    # status=GameStatus.CREATED,
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


async def update_db_obj(config, obj: Game | Player) -> None:
    """
    Function to update a game or player object in the database

    Args:
        config (_type_): configuration
        obj (Game | Player): Object to update in the database
    """
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
