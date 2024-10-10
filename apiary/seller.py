"""This module defines the Sellers used within the CoopHive protocol."""

import logging
import os

from dotenv import load_dotenv

from apiary.base_agent import Agent
from apiary.utils import add_float_to_csv

load_dotenv(override=True)


class NaiveSeller(Agent):
    """A Seller in the CoopHive protocol."""

    def __init__(self) -> None:
        """Initialize the Seller instance."""
        super().__init__()
        logging.info("NaiveSeller initialized")

    def infer(self, states, input_message):
        """Policy of Naive Seller."""
        output_message = self._preprocess_infer(input_message)
        if output_message == "noop":
            return output_message

        match input_message["data"].get("_tag"):
            case "offer":
                pass  # Confirm buyer offer with identity counteroffer
            case "buyAttest":
                output_message = self._buy_attestation_to_sell_attestation(
                    input_message, output_message
                )
        return output_message


class KalmanSeller(Agent):
    """A Seller in the CoopHive protocol."""

    def __init__(self) -> None:
        """Initialize the Seller instance."""
        super().__init__()
        logging.info("KalmanSeller initialized")

    def infer(self, states, input_message):
        """Policy of Kalman Seller."""
        output_message = self._preprocess_infer(input_message)
        if output_message == "noop":
            return output_message

        match input_message["data"].get("_tag"):
            case "offer":
                # NOTE: Negotiation strategy over scalar ERC20 amount only.
                valuation_estimation = os.getenv("VALUATION_ESTIMATION")
                valuation_variance = os.getenv("VALUATION_VARIANCE")

                # NOTE: General form:
                # (valuation_estimation, valuation_variance) = f(input_message, states)
                if valuation_estimation is None:
                    valuation_estimation = 300.0
                else:
                    valuation_estimation = float(valuation_estimation)
                add_float_to_csv(valuation_estimation)

                if valuation_variance is None:
                    valuation_variance = 10.0
                else:
                    valuation_variance = float(valuation_variance)

                valuation_measurement = input_message["data"]["token"]["amt"]
                add_float_to_csv(valuation_measurement)

                if valuation_measurement >= valuation_estimation:
                    # Beneficial incoming offer, no further negotiation needed.
                    pass  # Confirm buyer offer with identity counteroffer
                else:
                    valuation_measurement_variance = float(
                        os.getenv("VALUATION_MEASUREMENT_VARIANCE")
                    )

                    kalman_gain = valuation_variance / (
                        valuation_variance + valuation_measurement_variance
                    )

                    # Covariance Update
                    valuation_variance *= 1 - kalman_gain
                    os.environ["VALUATION_VARIANCE"] = str(valuation_variance)

                    # State Update
                    valuation_estimation *= 1 - kalman_gain
                    valuation_estimation += kalman_gain * valuation_measurement
                    valuation_estimation = round(
                        valuation_estimation
                    )  # EVM-compatible integer.
                    os.environ["VALUATION_ESTIMATION"] = str(valuation_estimation)
                    output_message["data"]["token"]["amt"] = valuation_estimation
            case "buyAttest":
                output_message = self._buy_attestation_to_sell_attestation(
                    input_message, output_message
                )
        return output_message
