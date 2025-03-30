"""All database related functions are here."""

import re
from datetime import datetime
from pydantic import BaseModel, field_validator
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.future import select

DB_URL_PATTERN = r"^sqlite\+aiosqlite:///{1,3}(\.\./)*[^/]+/[^/]+\.db$"


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
    status: Mapped[str] = mapped_column()
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
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


class DbConfiguration(BaseModel):
    """
    Configuration settings for db
    """

    db_url: str = None
    engine: AsyncEngine = None
    session: async_sessionmaker = None

    def initialize_db(self):
        """
        Function to initialize the database connection
        """
        self.engine = create_async_engine(self.db_url)
        self.session = async_sessionmaker(bind=self.engine, expire_on_commit=False)

    class Config:
        """
        Pydantic configuration class to define that all types are allowed
        """

        arbitrary_types_allowed = True

    @field_validator("db_url")
    @classmethod
    def check_db_url(cls, value: str) -> str:
        """
        Function to check the db_url input format

        Args:
            value (str): The db_url as string

        Raises:
            ValueError: If the db_url does not match the pattern

        Returns:
            str: The db_url
        """
        pattern = DB_URL_PATTERN
        if not re.match(pattern, value):
            raise ValueError("Invalid connection string. Please check the format.")
        return value


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
    async with config.db.session() as session:
        async with session.begin():
            game = Game(
                name=game_name,
                status="running",
                timestamp=datetime.now()
            )
            session.add(game)
            associations = [
                GamePlayerAssociation(game=game, player=p) for p in player
            ]
            session.add_all(associations)
        await session.refresh(game)
        return game


async def sync_db(engine: AsyncEngine):
    """
    Function to run the sync command and create all DB dependencies and tables

    Args:
        engine (AsyncEngine): The engine to run the sync command
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
