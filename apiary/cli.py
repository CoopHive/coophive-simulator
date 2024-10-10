"""This module defines the CLI (Command Line Interface) for the CoopHive application."""

import logging
import os
from datetime import datetime

import click

from apiary import constants, external_services, inference, utils

current_time = datetime.now().replace(second=0, microsecond=0)
CLI_TIME = current_time.strftime("%Y-%m-%d_%H-%M")


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--verbose", is_flag=True)
@click.option("--no-color", is_flag=True)
@click.option("--logs-filename", default="Apiary-{time}.log")
@click.option(
    "--output-path",
    default="./apiary_output/",
)
def cli(
    verbose: bool,
    no_color: bool,
    logs_filename: str,
    output_path: str,
):
    """Management CLI for Apiary."""
    constants.VERBOSE = verbose
    constants.NO_COLOR = no_color

    logs_filename = utils.template(logs_filename, dict(time=CLI_TIME))

    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    logs_path = os.path.join(output_dir, logs_filename)

    utils.setup_logger(logs_path=logs_path, verbose=verbose, no_color=no_color)


@cli.command()
@click.option(
    "--config-path",
    required=True,
)
@click.option(
    "--job-path",
    required=True,
)
@click.option("--token-data", required=True)
def start_buy(config_path: str, job_path: str, token_data: str):
    """Start Buyer."""
    logging.info("Starting Buyer.")
    os.environ["ROLE"] = "buyer"

    utils.load_configuration(config_path)

    initial_offer = utils.parse_initial_offer(job_path, token_data)
    logging.info(f"Initial Offer: {initial_offer}")

    inference.start_inference_endpoint()

    external_services.start_messaging_client(initial_offer)


@cli.command()
@click.option(
    "--config-path",
    required=True,
)
def start_sell(config_path: str):
    """Start Seller."""
    logging.info("Starting Seller.")
    os.environ["ROLE"] = "seller"

    utils.load_configuration(config_path)

    inference.start_inference_endpoint()

    external_services.start_messaging_client()


@cli.command()
def cancel_buy(offer_id):
    """Turn Off Buyer Services."""
    # TODO: turn off services in backward order as they have been turned on.
    # TODO: gracefully kill killable process (including messaging cancellation messages to messaging client)
    # and warn user about in-progress processes that cannot be stopped.
    # ps aux | grep -E 'uvicorn|redis'
    pass


@cli.command()
def cancel_sell():
    """Turn Off Seller Services."""
    # TODO: turn off services in backward order as they have been turned on.
    # TODO: gracefully kill killable process and warn user about in-progress processes that cannot be stopped.
    # TODO: include force flag to kill all the in-progress jobs, else wait for them to turn everything off.
    # ps aux | grep -E 'uvicorn|redis'
    pass


@cli.command()
def buy_status():
    """Parse log output and show metrics relevant for the Buyer."""
    # TODO
    pass


@cli.command()
def sell_status():
    """Parse log output and show metrics relevant for the Seller."""
    # TODO
    pass
