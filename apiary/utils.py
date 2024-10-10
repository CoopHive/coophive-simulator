"""This module defines various utility classes and functions for the CoopHive simulator."""

import csv
import json
import logging
import os
import uuid
from typing import TypedDict, Union

import colorlog
import matplotlib.pyplot as plt
import pandas as pd
import readwrite as rw
from dotenv import load_dotenv

load_dotenv(override=True)


def template(input: str, variables: dict) -> None:
    """Replace placeholders in the input string with values from the variables dictionary."""
    return input.format_map(variables)


def setup_logger(logs_path, verbose, no_color):
    """Set up a logger with both console and file handlers.

    Args:
        logs_path (str): The path for the log file.
        verbose (bool): If True, set logging level to DEBUG; otherwise, set to INFO.
        no_color (bool): If True, disable color in console output; otherwise, enable color.

    Returns:
        logging.Logger: Configured logger instance.
    """
    console_handler = colorlog.StreamHandler()

    log_format = (
        "%(levelname)s:%(message)s"
        if no_color
        else "%(log_color)s%(levelname)s:%(message)s%(reset)s"
    )

    log_colors = {
        "DEBUG": "green",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    }
    console_handler.setFormatter(
        logging.Formatter(log_format)
        if no_color
        else colorlog.ColoredFormatter(log_format, log_colors)
    )

    logger = colorlog.getLogger()
    logger.addHandler(console_handler)

    if verbose:
        # Set the desired file path here
        file_handler = logging.FileHandler(logs_path)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)

    # Set the logging level
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    return logger


def set_env_variables(config: dict):
    """Set environment variables based on a configuration dictionary.

    This function flattens the nested dictionary and assigns the corresponding values
    to environment variables. Existing environment variables take precedence over
    values in the config.
    """

    def get_keys(d, parent_key=""):
        """Recursively flatten dictionary keys."""
        keys = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                keys.extend(get_keys(v, new_key))
            else:
                keys.append(new_key)
        return keys

    def get_value_by_key(d, key):
        """Get the value from a nested dictionary using a flattened key."""
        keys = key.split(".")
        value = d
        for k in keys:
            value = value.get(k)
        return value

    # Flatten the config keys
    keys = get_keys(config)

    for key in keys:
        # Use the dotted keys directly for environment variables
        env_key = key.upper()

        # If the env variable is not already set, use the value from config
        if not os.getenv(env_key):
            value = get_value_by_key(config, key)
            os.environ[env_key] = str(value)
            logging.info(f"Set {env_key} = {value}")


def load_configuration(config_path: str):
    """Load configuration from a file and set environment variables.

    This function reads the configuration from a given file path and sets the
    appropriate environment variables, including setting AGENT_NAME based on the file name if not already defined.
    """
    config = rw.read(config_path)

    if not os.getenv("AGENT_NAME"):
        agent_name = config_path.rpartition(".")[0]
        agent_name = agent_name.rpartition("/")[-1]
        os.environ["AGENT_NAME"] = agent_name
        logging.info(f"Set AGENT_NAME: {agent_name}")

    set_env_variables(config)


class ERC20Token(TypedDict):
    """ERC20."""

    tokenStandard: str
    address: str
    amt: int


class ERC721Token(TypedDict):
    """ERC721."""

    tokenStandard: str
    address: str
    id: int


Token = Union[ERC20Token, ERC721Token]


def create_token(token_data: list) -> Token:
    """Create token object form input token data."""
    token_standard = token_data[0]
    address = token_data[1]

    if token_standard == "ERC20":
        amt = token_data[2]
        os.environ["VALUATION_ESTIMATION"] = str(amt)
        return {"tokenStandard": "ERC20", "address": address, "amt": amt}
    elif token_standard == "ERC721":
        return {"tokenStandard": "ERC721", "address": address, "id": token_data[2]}
    else:
        raise ValueError(f"Unsupported token standard: {token_standard}")


def parse_initial_offer(job_path, token_data):
    """Parses the initial offer based on the provided job path and price."""
    pubkey = os.getenv("PUBLIC_KEY")
    query = rw.read_as(job_path, "txt")

    data = {
        "_tag": "offer",
        "query": query,
    }

    token_data = json.loads(token_data)
    token = create_token(token_data)

    data["token"] = token

    return {
        "pubkey": pubkey,
        "offerId": str(uuid.uuid4()),
        "initial": True,
        "data": data,
    }


def add_float_to_csv(value):
    """Append a float value to a CSV file."""
    file_path = "apiary_output/negotiation.csv"
    file_exists = os.path.isfile(file_path)

    # Open the file in append mode if it exists, otherwise create a new file
    with open(file_path, mode="a", newline="") as file:
        writer = csv.writer(file)
        if not file_exists:
            # Write the header if the file is being created
            writer.writerow(["Amount"])
        # Append the current float value to the file
        writer.writerow([value])


def plot_negotiation():
    """Plot negotiation offers from a CSV file."""
    file_path = "apiary_output/negotiation.csv"

    df = pd.read_csv(file_path)

    odd_entries = df.iloc[::2]
    even_entries = df.iloc[1::2]

    plt.figure(figsize=(13, 5))
    plt.scatter(df.index, df, color="b", s=64, label="_nolegend_")

    plt.plot(
        odd_entries.index,
        odd_entries,
        linestyle="--",
        color="g",
        linewidth=1.5,
        label="Seller Offers",
    )
    plt.plot(
        even_entries.index,
        even_entries,
        linestyle="--",
        color="m",
        linewidth=1.5,
        label="Buyer Offers",
    )

    plt.title("Negotiation Rounds vs Offers", fontsize=16, fontweight="bold")
    plt.xlabel("Negotiation Round", fontsize=12)
    plt.ylabel("Offer", fontsize=12)
    plt.grid(True, linestyle="--", linewidth=0.5)

    plt.xticks(df.index)

    plt.legend()

    plt.tight_layout()

    plt.savefig("apiary_output/negotiation.png")
    plt.close()
