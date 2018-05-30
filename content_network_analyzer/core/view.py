"""
Defines view datatypes.
"""

from abc import abstractmethod


class View(object):
    """This class represents a view of an iterable of named clusters.
    """
    @abstractmethod
    def display(self, *args, **kwargs):
        """Displays an iterable of named clusters.
        """
        pass
