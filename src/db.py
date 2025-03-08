"""All database related functions are here."""

from pydantic import BaseModel, Field
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine


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
    # ToDo: crfaftable ist das falsche Wort für das Attribut. Benutzt werden kann sammelbar oder craftbar, herstellbar,
    craftable: Mapped[str] = mapped_column()

    def __repr__(self) -> str:
        return f"Name: {self.name!r}, rate:{self.rating!r})"


class DbConfiguration(BaseModel):
    """
    Configuration settings for db
    """

    db_url: str = ""
    engine: AsyncEngine = None
    session: async_sessionmaker = None

    def initialize_db(self):
        self.engine = create_async_engine(self.db_url, echo=False)
        self.session = async_sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine, expire_on_commit=False
        )


async def sync_db(engine: AsyncEngine):
    """Function to run the sync command and create all DB dependencies and tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
