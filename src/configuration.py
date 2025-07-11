"""
Load environment variables and validation of project configurations from user
"""
import re
# from typing import List, Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, field_validator, ConfigDict
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine
from .tetue_generic.generic_requests import GenReqConfiguration
from .tetue_generic.watcher import WatcherConfiguration

load_dotenv("default.env")
load_dotenv("files/.env", override=True)

DB_URL_PATTERN = r"^sqlite\+aiosqlite:///{1,3}(\.\./)*[^/]+/[^/]+\.db$"


class GeneralGame(BaseModel):
    """
    Configuration settings for general game settings
    """
    num_quests: int
    input_task_path: str
    export_task_path: str
    weighted_hours_g1: float
    weighted_league_pos_g1: float


class DbConfiguration(BaseModel):
    """
    Configuration settings for db
    """

    db_url: str = None
    engine: AsyncEngine = None
    session: async_sessionmaker = None
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def initialize_db(self):
        """
        Function to initialize the database connection
        """
        self.engine = create_async_engine(self.db_url)
        self.session = async_sessionmaker(bind=self.engine, expire_on_commit=False)


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


class DiscordBotConfiguration(BaseModel):
    """
    Configuration settings for discord bot
    """

    token: str
    # TT_DC__channel_id_g1=[1234,5678]
    # channel_id_g1: Optional[List[int]]


class Configuration(BaseSettings):
    """
    Configuration class to merge all settings for the application and validate via pydantic

    Args:
        BaseSettings (BaseSettings): Base class for settings from environment variables.
    """

    model_config = SettingsConfigDict(
        env_prefix="TT_", env_nested_delimiter="__", arbitrary_types_allowed=True
    )

    gen_req: GenReqConfiguration
    watcher: WatcherConfiguration
    db: DbConfiguration
    dc: DiscordBotConfiguration
    game: GeneralGame
