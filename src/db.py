"""All database related functions are here."""

import re
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine

DB_URL_PATTERN = r"^sqlite\+aiosqlite:///{1,3}(\.\./)*[^/]+/[^/]+\.db$"

class Base(DeclarativeBase):
    """Declarative base class

    Args:
        DeclarativeBase (_type_): Basic class that is inherited
    """


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


async def sync_db(engine: AsyncEngine):
    """
    Function to run the sync command and create all DB dependencies and tables

    Args:
        engine (AsyncEngine): The engine to run the sync command
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
