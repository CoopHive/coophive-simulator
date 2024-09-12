"""This module defines the Agent class.

It manage agents, their policies, their states and their actions.
"""

import logging
from dataclasses import dataclass

from coophive.data_attribute import DataAttribute
from coophive.deal import Deal
from coophive.job_offer import JobOffer
from coophive.match import Match
from coophive.policy import Policy
from coophive.resource_offer import ResourceOffer
from coophive.utils import Tx, hash_dict, log_json


class Agent:
    """A class to represent an Agent.

    Agents are entities such as Clients, Resource Providers, Solvers, and Validators.

    The Agent is designed to be stateless, meaning that its states (messages, policy states, and environmental states)
    are loaded at inference time rather than being stored in memory. The history of these states is managed externally
    via storage mechanisms like databases or flatfiles (e.g., PostgreSQL, .parquet).

    Key Concepts:
        - Messages: Communication exchanged by the Agent, handled by connecting with a messaging client (e.g., Redis).
        - Environmental States: These represent external factors that influence the Agent's decisions. Environmental states
          are updated using independent data pipelines and stored externally.
            - Mandatory States are hard coded in the Agents API.
            - Additional States are passed as a generic dictionary {"additional_state_1_name": additional_state_1_value}.
        - Policies: The Agent's behavior is defined by its policiy, which in turn is determined by a set of parameters,
            defining the internal state/policy state of the agent, which can be dynamically updated using machine learning
            models. They are again stored outside the Agent.

    The responsibility for managing the history and updates of these states, if necessary, is on the Agent itself.

    Tradeoff Consideration:
        - Disk Space vs. RAM: While stateless design offloads memory usage by storing and retrieving data externally,
          there is a tradeoff when considering the amount of space consumed. Over time, the volume of stored states
          (especially environmental states and policy histories) can grow significantly, requiring more storage.
          This has relevant implications for more lightweight devices like IoT sensors, which may have limited storage and RAM.
    """

    def __init__(
        self,
        private_key: str,
        public_key: str,
        messagin_client_address: str,
        policy_name: str,
    ):
        """Initialize the Agent."""
        self.private_key = private_key  # https://web3py.readthedocs.io/en/stable/web3.eth.account.html#reading-a-private-key-from-an-environment-variable
        self.public_key = public_key
        self.messagin_client_address = messagin_client_address
        self.policy = Policy(policy_name=policy_name)

        self.local_information = LocalInformation()
        self.events = []
        self.smart_contract = None
        self.current_deals: dict[str, Deal] = {}
        self.current_matched_offers = []
        self.deals_finished_in_current_step = []

        logging.info(f"Agent {self.public_key} initialized.")

    def get_public_key(self):
        """Get the public key of the agent."""
        return self.public_key

    def get_local_information(self):
        """Get the local information of the agent."""
        return self.local_information

    def _create_transaction(self, value):
        """Helper function to create a reusable transaction object."""
        return Tx(sender=self.get_public_key(), value=value)

    def connect_to_smart_contract(self, smart_contract):
        """Connect to a smart contract and subscribe to its events.

        Args:
            smart_contract: The smart contract instance to connect to.
        """
        self.smart_contract = smart_contract
        smart_contract.subscribe_event(self.handle_smart_contract_event)
        logging.info("Connected to smart contract")

    def handle_solver_event(self, event):
        """Handle events from the solver."""
        event_data = {"name": event.get_name(), "id": event.get_data().get_id()}
        logging.info(f"Received solver event: {event_data}")

        if event.get_name() == "match":
            match = event.get_data()
            if (
                match.get_data()[f"{self.__class__.__name__.lower()}_address"]
                == self.get_public_key()
            ):
                self.current_matched_offers.append(match)

    # TODO: transfer functionality inside policy evaluation
    def reject_match(self, match):
        """Reject a match."""
        logging.info(f"Rejected match: {match.get_id()}")

    # TODO: transfer functionality inside policy evaluation
    def negotiate_match(self, match, max_rounds=5):
        """Negotiate a match."""
        match_dict = match.get_data()
        rounds_completed = match_dict["rounds_completed"]
        while rounds_completed < max_rounds:
            new_match_offer = self.create_new_match_offer(match)
            response = self.communicate_request_to_party(new_match_offer)
            if response["accepted"]:
                self._agree_to_match(response["match_offer"])
                return
            match = response["counter_offer"]
            rounds_completed += 1
            match.set_attributes({"rounds_completed": rounds_completed})
        self.reject_match(match)

    def communicate_request_to_party(self, match_offer):
        """Communicate a match offer request to a specified party.

        Args:
            match_offer: The match offer details to be communicated.
        """
        return self.simulate_communication(match_offer)

    def simulate_communication(self, match_offer):
        """Simulate communication."""
        message = f"New match offer: {match_offer.get_data()}"

        response_message = "Your offer has been accepted."

        logging.info("Received response from server")
        log_json(
            "Received response from server",
            {"response_message": response_message},
        )

        response = {
            "accepted": "accepted" in response_message,
            "match_offer": match_offer,
            "counter_offer": self.create_new_match_offer(match_offer),
        }
        return response

    def create_new_match_offer(self, match):
        """Create a new match offer with modified terms.

        Args:
            match (Match): The match object to base the new offer on.

        Returns:
            Match: A new match object.
        """
        data = match.get_data()
        new_data = data.copy()

        # Placeholder identity Policy
        new_data["price_per_instruction"] = data["price_per_instruction"]

        new_match = Match(new_data)
        return new_match

    def update_finished_deals(self):
        """Update the list of finished deals by removing them from the current deals and jobs lists."""
        for deal_id in self.deals_finished_in_current_step:
            del self.current_deals[deal_id]
        self.deals_finished_in_current_step.clear()


@dataclass
class CID:
    """IPFS CID."""

    hash: str
    data: dict


@dataclass
class IPFS:
    """Class representing an IPFS system for storing and retrieving data."""

    def __init__(self):
        """Initialize the IPFS system with an empty data store."""
        self.data = {}

    def add(self, data):
        """Add data to the IPFS system.

        Args:
            data: The data to add, which can be of type DataAttribute or dict.
        """
        # check if data is of type DataAttribute
        if isinstance(data, DataAttribute):
            cid_hash = data.get_id()
            self.data[cid_hash] = data
        # check if data is of type dict
        if isinstance(data, dict):
            cid = CID(hash=hash_dict(data), data=data)
            self.data[cid.hash] = data

    def get(self, cid_hash):
        """Retrieve data from the IPFS system by its CID hash."""
        return self.data[cid_hash]


class LocalInformation:
    """A class to manage local information.

    Attributes:
        block_number (int): The block number for the current state.
        resource_providers (dict): Mapping from wallet address to resource provider metadata.
        clients (dict): Mapping from wallet address to client metadata.
        solvers (dict): Mapping from wallet address to solver metadata.
        mediators (dict): Mapping from wallet address to mediator metadata.
        directories (dict): Mapping from wallet address to directory metadata.
        resource_offers (dict): Mapping from offer ID to resource offer data.
        job_offers (dict): Mapping from offer ID to job offer data.
    """

    ipfs = IPFS()

    def __init__(self):
        """Initialize the LocalInformation."""
        self.block_number = 0
        self.resource_providers = {}
        self.clients = {}
        self.solvers = {}
        self.mediators = {}
        self.directories = {}
        self.resource_offers: dict[str, ResourceOffer] = {}
        self.job_offers: dict[str, JobOffer] = {}

    def add_resource_offer(self, id: str, data):
        """Add a resource offer to the local information and IPFS."""
        logging.info("Adding resource offer locally:")
        self.resource_offers[id] = data
        logging.info("Adding resource offer to IPFS:")
        self.ipfs.add(data)

    def add_job_offer(self, id: str, data):
        """Add a job offer to the local information and IPFS."""
        logging.info("Adding job offer locally:")
        self.job_offers[id] = data
        logging.info("Adding job offer to IPFS:")
        self.ipfs.add(data)

    def get_resource_offers(self):
        """Get the resource offers in the local information."""
        return self.resource_offers

    def get_job_offers(self):
        """Get the job offers in the local information."""
        return self.job_offers
