"""All database related functions are here."""
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine("sqlite+aiosqlite:///../files/DstGame.db", echo=False)


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
    craftable: Mapped[str] = mapped_column() # ToDo: crfaftable ist das falsche Wort für das Attribut. Benutzt werden kann sammelbar oder craftbar, herstellbar, 

    def __repr__(self) -> str:
        return f"Name: {self.name!r}, rate:{self.rating!r})"
