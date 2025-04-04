"""
Module to parse the items from Fandom wiki with given url and process items
"""
import pandas as pd
from .configuration import Configuration
from .tetue_generic.generic_requests import generic_http_request

#url_ = "https://dontstarve.fandom.com/wiki/Items_Don't_Starve_Together"



async def parse_items(config: Configuration, url: str, save_path_name: str) -> bool:
    """
    Function to parse the items from the given url and save them to a csv file.

    Args:
        config (Configuration): App configuration
        url (str): Url to parse the items from
        save_path_name (str): Path and name to save the csv file

    Returns:
        bool: If csv file was created successfully
    """

    response = generic_http_request(
        url,
        header={},
        req_timeout=config.gen_req.request_timeout,
        logger=config.watcher.logger,
    )
    if response is None:
        return False

    df_list = pd.read_html(response.content)
    df = df_list[-1]
    df.to_csv(save_path_name)
    return True
