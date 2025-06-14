"""Implement generic request function with own logging and return functionality"""

from __future__ import annotations
import requests
from pydantic import BaseModel, PositiveInt, field_validator, Field
from . import watcher
from . import GENERIC_REQUEST_TIMEOUT_THR


class GenReqConfiguration(BaseModel):
    """
    Configuration settings for generic_requests
    """

    request_timeout: PositiveInt = Field(
        10, description="Timeout for requests in seconds"
    )

    @field_validator("request_timeout")
    @classmethod
    def check_request_timeout(cls, value: int) -> int:
        """
        Check if the request_timeout is greater than a threshold

        Args:
            value (int): The value to check

        Raises:
            ValueError:  If the value is less than or equal to threshold

        Returns:
            int: The value if it is greater than threshold
        """
        if value < GENERIC_REQUEST_TIMEOUT_THR:
            raise ValueError(
                f"request_timeout must be greater than or equal to {GENERIC_REQUEST_TIMEOUT_THR}"
            )
        return value


async def generic_http_request(
    url: str,
    header: dict,
    req_timeout: int = GENERIC_REQUEST_TIMEOUT_THR,
    logger: watcher.loguru.Logger = None,
) -> requests.Response:
    """Function for http requests with all possible exceptions which are then stored by a logger.

    Args:
        url (str): The URL to send the request
        header (dict): The headers to include in the request
        logger (loguru.logger): Logger for storing the error

    Returns:
        requests.Response: Return value from http request or in failure case a None
    """
    try:
        return requests.get(
            url, headers=header, timeout=req_timeout
        )
    except requests.exceptions.HTTPError as err:
        if logger is not None:
            watcher.logger.error(f"HTTP error occurred: {err}")
        else:
            print(f"HTTP error occurred: {err}")
        return None
    except requests.exceptions.ConnectTimeout as err:
        if logger is not None:
            watcher.logger.error(f"Connection timeout error occurred: {err}")
        else:
            print(f"Connection timeout error occurred: {err}")
        return None
    except requests.exceptions.ConnectionError as err:
        if logger is not None:
            watcher.logger.error(f"Connection error occurred: {err}")
        else:
            print(f"Connection error occurred: {err}")
        return None
