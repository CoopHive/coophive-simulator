from unittest.mock import MagicMock, patch

import pytest

from coophive.buyer import Buyer
from coophive.match import Match
from coophive.policy import Policy
from coophive.seller import Seller

private_key_buyer = "0x4c0883a69102937d6231471b5dbb6204fe512961708279a4a6075d78d6d3721b"
private_key_seller = (
    "0x4c0883a69102937d6231471b5dbb6204fe512961708279a4a6075d78d6d3721c"
)
public_key_buyer = "0x627306090abaB3A6e1400e9345bC60c78a8BEf57"
public_key_seller = "0x627306090abaB3A6e1400e9345bC60c78a8BEf56"

messaging_client_url = "coophive.network.redis"


@pytest.fixture
def setup_agents_with_policies():
    """Fixture to set up the test environment with agents and policies."""
    with (
        patch("socket.socket") as mock_socket,
        patch("docker.from_env") as mock_docker_from_env,
    ):
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance

        # Mock Docker buyer
        mock_docker_buyer = MagicMock()
        mock_docker_from_env.return_value = mock_docker_buyer

        policy_a = "naive_accepter"
        policy_b = "naive_rejecter"
        policy_c = "identity_negotiator"

        buyer = Buyer(
            private_key=private_key_buyer,
            public_key=public_key_buyer,
            messaging_client_url=messaging_client_url,
            policy_name=policy_a,
        )

        seller = Seller(
            private_key=private_key_seller,
            public_key=public_key_seller,
            messaging_client_url=messaging_client_url,
            policy_name=policy_b,
        )

        return buyer, seller, policy_c


def test_make_match_decision_with_policies(setup_agents_with_policies):
    """Test the make_match_decision method with different policies."""
    buyer, seller, policy_c = setup_agents_with_policies

    mock_match = Match()
    mock_match.set_attributes(
        {
            "buyer_address": "buyer_address",
            "seller_address": "seller_address",
            "buyer_deposit": 100,
            "price_per_instruction": 10,
            "expected_number_of_instructions": 1000,
        }
    )

    buyer.policy = Policy(policy_name=policy_c)
    buyer.negotiate_match = MagicMock()

    # TODO: make this scheme-compliant
    # TODO: more in general, test the scheme compliance of policies.
    def mock_infer(message):
        return "accept"

    buyer.policy.infer = MagicMock(side_effect=mock_infer)
    buyer.policy.infer(mock_match)


if __name__ == "__main__":
    pytest.main()
