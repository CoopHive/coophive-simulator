"""This module defines the Solver class which is responsible for connecting to smart contracts, handling events, and managing job and resource offers."""

import logging

from coophive.agent import Agent
from coophive.data_attribute import DataAttribute
from coophive.deal import Deal
from coophive.event import Event
from coophive.job_offer import JobOffer
from coophive.match import Match
from coophive.resource_offer import ResourceOffer
from coophive.utils import log_json

extra_necessary_match_data = {
    "client_deposit": 5,
    "timeout": 10,
    "timeout_deposit": 3,
    "cheating_collateral_multiplier": 50,
    "price_per_instruction": 1,
    "verification_method": "random",
}


class Solver(Agent):
    """Solver class to handle smart contract connections, events, and the matching of job and resource offers."""

    def __init__(
        self,
        private_key: str,
        public_key: str,
        messagin_client_address: str,
        policy_name: str,
    ):
        """Initialize the Solver."""
        super().__init__(
            private_key=private_key,
            public_key=public_key,
            messagin_client_address=messagin_client_address,
            policy_name=policy_name,
        )

        self.machine_keys = ["CPU", "RAM"]
        self.deals_made_in_current_step: dict[str, Deal] = {}
        self.currently_matched_job_offers = set()
        self.current_matched_resource_offers = set()

    def handle_smart_contract_event(self, event: Event):
        """Handle events from the smart contract."""
        if event.get_name() == "mediation_random":
            event_name = event.get_name()
            event_data_id = (
                event.get_data().get_id()
                if isinstance(event.get_data(), DataAttribute)
                else None
            )
            log_json(
                "Smart contract event",
                {"event_name": event_name, "event_data_id": event_data_id},
            )
            job_offer_cid = event_data_id
            if job_offer_cid not in self.get_local_information().get_job_offers():
                # solver doesn't have the job offer locally, must retrieve from IPFS
                job_offer = self.get_local_information().ipfs.get(job_offer_cid)
            else:
                job_offer = self.get_local_information().get_job_offers()[job_offer_cid]

            event = job_offer

        # if deal, remove resource and job offers from list
        elif event.get_name() == "deal" and isinstance(event.get_data(), Deal):
            log_json(
                "Smart contract event",
                {
                    "event_name": event.get_name(),
                    "event_data_id": event.get_data().get_id(),
                },
            )

            deal = event.get_data()

            if not isinstance(event.get_data(), DataAttribute):
                logging.warning(
                    f"Unexpected data type received in solver event: {type(event.get_data())}"
                )

            self.deals_made_in_current_step[event.get_data().get_id()] = (
                event.get_data()
            )

    def _remove_offer(self, offers_dict, offer_id):
        """Helper function to remove an offer by ID.

        Args:
            offers_dict (dict): The dictionary of offers.
            offer_id (str): The ID of the offer to remove.
        """
        if offer_id in offers_dict:
            del offers_dict[offer_id]

    def remove_outdated_offers(self):
        """Remove outdated offers that have been dealt in the current step."""
        for deal in self.deals_made_in_current_step:
            if not isinstance(deal, Deal):
                logging.warning(
                    f"Unexpected data type received in solver event: {type(deal)}"
                )
            deal_data = deal.get_data()
            # delete resource offer
            resource_offer = deal_data["resource_offer"]
            # delete job offer
            job_offer = deal_data["job_offer"]
            self._remove_offer(
                self.get_local_information().get_resource_offers(), resource_offer
            )
            self._remove_offer(self.get_local_information().get_job_offers(), job_offer)
        # clear list of deals made in current step
        self.deals_made_in_current_step.clear()

    def emit_event(self, event: Event):
        """Emit an event and notify all subscribed event handlers."""
        self.events.append(event)
        for event_handler in self.event_handlers:
            event_handler(event)

    # TODO: transfer functionality inside policy evaluation at the agent level.
    # This is a solver-specific policy, but still a policy.
    def solve(self):
        """Solve the current matching problem by matching job offers with resource offers."""
        for job_offer_id, job_offer in (
            self.get_local_information().get_job_offers().items()
        ):
            resulting_resource_offer = self.match_job_offer(job_offer)
            if resulting_resource_offer is not None:
                # add job and resource offers to sets of currently matched offers
                resulting_resource_offer_id = resulting_resource_offer.get_id()
                self.current_matched_resource_offers.add(resulting_resource_offer_id)
                self.currently_matched_job_offers.add(job_offer_id)
                # create match
                match = self.create_match(job_offer, resulting_resource_offer)
                match.set_id()
                # create match event
                match_event = Event(name="match", data=match)
                # emit match event
                self.emit_event(match_event)
                log_json(
                    "Match event emitted",
                    {"match_event": match_event.get_data().get_id()},
                )
                # go on to the next job offer
                continue

    def match_job_offer(self, job_offer: JobOffer):
        """Match a job offer with a resource offer.

        Args:
            job_offer (JobOffer): The job offer to match.

        Returns:
            ResourceOffer: The matched resource offer, or None if no match is found.
        """
        # only look for exact matches for now
        job_offer_data = job_offer.get_data()
        job_offer_id = job_offer.get_id()
        current_resource_offers = self.local_information.get_resource_offers()
        for resource_offer_id, resource_offer in current_resource_offers.items():
            # do not consider offers that have already been matched
            if (job_offer_id in self.currently_matched_job_offers) or (
                resource_offer_id in self.current_matched_resource_offers
            ):
                continue
            if not isinstance(resource_offer, ResourceOffer):
                logging.warning(
                    f"Unexpected data type received in solver event: {type(resource_offer)}"
                )
                continue
            resource_offer_data = resource_offer.get_data()
            is_match = True
            for machine_key in self.machine_keys:
                if resource_offer_data[machine_key] != job_offer_data[machine_key]:
                    is_match = False
                else:
                    break

            if is_match:
                return resource_offer

        return None

    def add_necessary_match_data(self, match: Match):
        """Add necessary match data to a match."""
        for data_field, data_value in extra_necessary_match_data.items():
            match.add_data(data_field, data_value)

    def create_match(self, job_offer: JobOffer, resource_offer: ResourceOffer) -> Match:
        """Create a match between a job offer and a resource offer.

        Args:
            job_offer (JobOffer): The job offer.
            resource_offer (ResourceOffer): The resource offer.

        Returns:
            Match: The created match.
        """
        # deal in stage 1 solver is exact match
        match = Match()
        job_offer_data = job_offer.get_data()
        resource_offer_data = resource_offer.get_data()
        match.add_data("resource_provider_address", resource_offer_data.get("owner"))
        match.add_data("client_address", job_offer_data.get("owner"))
        match.add_data("resource_offer", resource_offer.get_id())
        match.add_data("job_offer", job_offer.get_id())

        self.add_necessary_match_data(match)

        return match
