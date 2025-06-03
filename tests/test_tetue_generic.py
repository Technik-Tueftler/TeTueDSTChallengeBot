"""
This file contains unit tests for verifying the functionality of 
generic utilities and functions within package tetue_generic.
"""
import os
import sys
import pytest
from unittest.mock import patch
from asyncmock import AsyncMock
from pydantic import ValidationError
import src
from src.tetue_generic import GENERIC_REQUEST_TIMEOUT_THR

sys.path.append('..')

@pytest.mark.asyncio
async def test_generic_http_request_success(mocker):
    """
    Tests the successful execution of a generic HTTP request.

    This test verifies that the `generic_http_request` function behaves correctly
    when an HTTP request succeeds. Using mocking, it simulates the behavior of an 
    HTTP GET request to ensure that the function:
    - Returns a valid response.
    - Correctly processes the response's status code and text.

    Args:
        mocker: A fixture used to mock modules and functions, 
        applied here to patch `src.requests.get`.

    Test Steps:
    1. Create a mock HTTP response with a status code of 200 and the text "Success."
    2. Patch the `src.requests.get` function to return the mock response.
    3. Call the `generic_http_request` function with a sample URL and headers.
    4. Validate the returned response to ensure that:
        - It is not `None`.
        - It contains a status code of 200.
        - It includes the text "Success."
    """
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "Success"
    mocker.patch("src.requests.get", return_value=mock_response)

    url = "https://example.com"
    header = {"Authorization": "Bearer token"}
    response = await src.generic_http_request(url, header)

    assert response is not None
    assert response.status_code == 200
    assert response.text == "Success"


@pytest.mark.asyncio
async def test_generic_requests_http_error(mocker, capsys):
    """
    Tests the behavior of `generic_http_request` when an HTTP error occurs.

    This test ensures that the `generic_http_request` function handles HTTP errors gracefully by:
    - Returning `None` when an HTTP error is encountered.
    - Logging the appropriate error message to standard output.

    Args:
        mocker: A fixture used to mock modules and functions, 
        here used to simulate an HTTP error by patching `requests.get`.
        capsys: A pytest fixture for capturing and inspecting standard output and error streams.

    Test Steps:
    1. Mock the `requests.get` function to raise an `HTTPError` when called.
    2. Provide a sample URL and headers to the `generic_http_request` function.
    3. Verify the following:
        - The function returns `None`.
        - The error message "HTTP error occurred: \n" is logged to the standard output.
    """

    mocker.patch("requests.get", side_effect=src.requests.exceptions.HTTPError)
    url = "https://example.com"
    header = {"Authorization": "Bearer token"}

    # with pytest.raises(src.requests.exceptions.HTTPError):
    response = await src.generic_http_request(url, header)
    captured = capsys.readouterr()
    assert response is None
    assert captured.out == "HTTP error occurred: \n"


@pytest.mark.asyncio
async def test_generic_requests_connect_timeout(mocker, capsys):
    """
    Tests the behavior of `generic_http_request` when a connection timeout occurs.

    This test ensures that the `generic_http_request` function handles connection timeouts 
    gracefully by:
    - Returning `None` when a `ConnectTimeout` exception is raised.
    - Logging the appropriate timeout error message to standard output.

    Args:
        mocker: A fixture used to mock modules and functions, 
        here used to simulate a connection timeout by patching `requests.get`.
        capsys: A pytest fixture for capturing and inspecting standard output and error streams.

    Test Steps:
    1. Mock the `requests.get` function to raise a `ConnectTimeout` exception when called.
    2. Provide a sample URL and headers to the `generic_http_request` function.
    3. Verify the following:
        - The function returns `None`.
        - The error message "Connection timeout error occurred: \n" 
        is logged to the standard output.
    """

    mocker.patch("requests.get", side_effect=src.requests.exceptions.ConnectTimeout)
    url = "https://example.com"
    header = {"Authorization": "Bearer token"}

    response = await src.generic_http_request(url, header)
    captured = capsys.readouterr()
    assert response is None
    assert captured.out == "Connection timeout error occurred: \n"


@pytest.mark.asyncio
async def test_generic_requests_connection_error(mocker, capsys):
    """
    Tests the behavior of `generic_http_request` when a connection error occurs.

    This test ensures that the `generic_http_request` function handles 
    connection errors appropriately by:
    - Returning `None` when a `ConnectionError` exception is raised.
    - Logging the correct connection error message to standard output.

    Args:
        mocker: A fixture used to mock modules and functions, 
        here used to simulate a connection error by patching `requests.get`.
        capsys: A pytest fixture for capturing and inspecting standard output and error streams.

    Test Steps:
    1. Mock the `requests.get` function to raise a `ConnectionError` exception when called.
    2. Provide a sample URL and headers to the `generic_http_request` function.
    3. Verify the following:
        - The function returns `None`.
        - The error message "Connection error occurred: \n" is logged to the standard output.
    """

    mocker.patch("requests.get", side_effect=src.requests.exceptions.ConnectionError)
    url = "https://example.com"
    header = {"Authorization": "Bearer token"}

    response = await src.generic_http_request(url, header)
    captured = capsys.readouterr()
    assert response is None
    assert captured.out == "Connection error occurred: \n"

def test_gen_req_configuration_default():
    """
    Verifies the default value for request timeout of `GenReqConfiguration`.

    Steps:
    1. Instantiate `GenReqConfiguration`.
    2. Assert that `request_timeout` equals 10.
    """
    config = src.GenReqConfiguration()
    assert config.request_timeout == 10

def test_gen_req_configuration_valid():
    """
    Verifies the correct value for request timeout of `GenReqConfiguration`.
    
    Steps:
    1. Instantiate `GenReqConfiguration` with a custom request timeout with 33s.
    2. Assert that `request_timeout` equals the custom value 33s.
    """
    config = src.GenReqConfiguration(request_timeout=33)
    assert config.request_timeout == 33

def test_gen_req_configuration_invalid():
    """
    Verifies the validation of request timeout of `GenReqConfiguration`.

    Steps:
    1. Instantiate `GenReqConfiguration` with an invalid request timeout below the threshold.
    2. Assert that a `ValidationError` is raised with the correct error message.
    """
    with pytest.raises(ValidationError) as exc_info:
        src.GenReqConfiguration(request_timeout=GENERIC_REQUEST_TIMEOUT_THR-1)
    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]['msg'] == \
    f"Value error, request_timeout must be greater than or equal to {GENERIC_REQUEST_TIMEOUT_THR}"


def test_watcher_configuration_default():
    """
    Verifies the default value for file path of `WatcherConfiguration`.

    Steps:
    1. Instantiate `Configuration`.
    2. Assert that `log_file_path` equals files/app.log.
    """
    with patch.dict(os.environ, {"TT_WATCHER__LOG_FILE_PATH": "files/app.log"}):
        config = src.Configuration()
        assert config.watcher.log_file_path == "files/app.log"
