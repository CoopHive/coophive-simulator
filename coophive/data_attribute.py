"""This module defines the DataAttribute class used for managing data attributes within the coophive simulator.

The DataAttribute class provides methods to add data, retrieve data, set a unique ID based on the data, and retrieve the ID.
"""

import logging

from coophive.utils import hash_dict


class DataAttribute:
    """A class to manage data attributes and enforce constraints on them.

    Attributes:
        data_attributes (set): A set of valid data attributes.
        data (dict): A dictionary to store data attributes and their values.
        id (str): A unique identifier for the data, generated by hashing the data.
    """

    data_attributes = {}

    def __init__(self):
        """Initialize a new DataAttribute instance with empty data and no ID."""
        self.data = {}
        self.id = None

    def add_data(self, data_field: str, data_value):
        """Add data to the data attribute, enforcing constraints.

        Args:
            data_field (str): The data field to add.
            data_value: The value to assign to the data field.

        Raises:
            Exception: If the data field is not in the set of valid data attributes.
        """
        # enforces constraints on deals to enable matches
        if data_field not in self.data_attributes:
            logging.error(f"Trying to add invalid data field {data_field}")
            raise Exception(f"trying to add invalid data field")
        else:
            self.data[data_field] = data_value

    def get_data(self):
        """Get data from attributes."""
        data = {}
        for attribute in self.data_attributes:
            data[attribute] = getattr(self, attribute, None)
        return data

    def set_id(self):
        """Set a unique identifier for the data by hashing the data."""
        self.id = hash_dict(self.data)
