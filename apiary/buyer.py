"""This module defines the Buyers used within the CoopHive protocol."""

import logging
import os

from dotenv import load_dotenv

from apiary.base_agent import Agent
from apiary.utils import plot_negotiation

load_dotenv(override=True)


class NaiveBuyer(Agent):
    """A Buyer in the CoopHive protocol."""

    def __init__(self) -> None:
        """Initialize the Buyer instance."""
        super().__init__()
        logging.info("NaiveBuyer initialized")

    def infer(self, states, input_message):
        """Policy of Naive Buyer."""
        output_message = self._preprocess_infer(input_message)
        if output_message == "noop":
            return output_message

        match input_message["data"].get("_tag"):
            case "offer":
                # Confirm seller counteroffer
                output_message = self._offer_to_buy_attestation(
                    input_message, output_message
                )
            case "sellAttest":
                self._get_result_from_result_cid(input_message["data"]["result"])
                return "noop"

        return output_message


class KalmanBuyer(Agent):
    """A Buyer in the CoopHive protocol."""

    def __init__(self) -> None:
        """Initialize the Buyer instance."""
        super().__init__()
        logging.info("KalmanBuyer initialized")

    def infer(self, states, input_message):
        """Policy of Naive Buyer."""
        output_message = self._preprocess_infer(input_message)
        if output_message == "noop":
            return output_message

        match input_message["data"].get("_tag"):
            case "offer":
                # TODO: mostly duplicate of KalmanSeller, refacto to avoid.

                # NOTE: Negotiation strategy over scalar ERC20 amount only.
                valuation_estimation = float(os.getenv("VALUATION_ESTIMATION"))
                valuation_variance = float(os.getenv("VALUATION_VARIANCE"))

                valuation_measurement = input_message["data"]["token"]["amt"]

                abs_tol = float(os.getenv("ABSOLUTE_TOLERANCE"))
                if valuation_measurement <= valuation_estimation + abs_tol:
                    plot_negotiation()

                    output_message = self._offer_to_buy_attestation(
                        input_message, output_message
                    )
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
            case "sellAttest":
                self._get_result_from_result_cid(input_message["data"]["result"])
                return "noop"

        return output_message


# NOTE:
# def load_states():
# check that states (including p (internal states/model states/policy configurations))
# are up to date and warning if not (not doing anything directly, another process is responsibile for doing something about it).
#     import jax
#     model_pickle = read_pickle('jax_model.pickle')
#     model = jax.from_pickle(model_pickle) # This is why we do this in python, even if the training is happening in a completely separate process.
#     return {'X': , ''}
#    match input_message_tag to capute negotiation-strategy-invariant actions and move them to buy/sellagent functions if necessary, else:
#    reply_buy_attest.
#    reply_sell_attest.
#    NOTE: in the case messaging is server-push-based, deal negotiations and job runs are necessarily sequential.
