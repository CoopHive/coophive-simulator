"""Registry of Agents."""

import os

from apiary import buyer, seller


def get_agent():
    """Get agent from registry."""
    agent_name = os.getenv("AGENT_NAME")

    agents = {
        # Buyers
        "buyer_naive": buyer.NaiveBuyer,
        "buyer_kalman": buyer.KalmanBuyer,
        # Sellers
        "seller_naive": seller.NaiveSeller,
        "seller_kalman": seller.KalmanSeller,
    }

    agent_class = agents.get(agent_name)

    if agent_class is None:
        raise ValueError(f"Unknown agent: {agent_name}")

    return agent_class()
