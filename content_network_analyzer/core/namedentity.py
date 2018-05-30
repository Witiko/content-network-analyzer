"""
Defines a named entity datatype.
"""

from abc import abstractmethod


class NamedEntity(object):
    """This class represents a named entity.
    """
    @abstractmethod
    def getName():
        """Returns the name of the entity.

        Returns
        -------
        name : str
            The name of the entity.
        """
        pass

    def __hash__(self):
        return hash(self.getName())

    def __eq__(self, other):
        return isinstance(other, NamedEntity) and self.getName() == other.getName()
