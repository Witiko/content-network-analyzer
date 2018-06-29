"""
Defines random variable, and sample datatypes.
"""

from abc import abstractmethod
from datetime import datetime

from .cluster import Cluster


class RandomVariable(Cluster):
    """This class represents a random variable.
    """
    def __iter__(self):
        for individual in self.sample:
            yield individual


class Individual(object):
    """This class represents an individual in a population.
    """
    @abstractmethod
    def __add__(self, other):
        """Returns the aggregate of two individuals.

        Parameters
        ----------
        other : cluster
            The other individual.

        Returns
        -------
        individual
            An aggregate individual aggregated from this individual, and the other individual.
        """
        pass

    def __radd__(self, other):
        return self.__add__(other)

    def __repr__(self):
        return "%s" % (self.__class__)


class SampledIndividual(Individual):
    """This class represents a sampled individual in a population.

    Parameters
    ----------
    individual : Individual
        An individual in a population.
    datetime : datetime
        The datetime at which the individual was sampled.
    """
    def __init__(self, individual, date):
        assert isinstance(individual, Individual)
        assert isinstance(datetime, date)
        self._individual = individual
        self._date = date

    def __add__(self, other):
        return self._individual + other

    def getDatetime(self):
        """Returns the datetime at which the individual was sampled.
        """
        return self._date

    def __lt__(self, other):
        return isinstance(other, SampledIndividual) and self.getDatetime() < other.getDatetime()

    def __le__(self, other):
        return isinstance(other, SampledIndividual) and self.getDatetime() <= other.getDatetime()
