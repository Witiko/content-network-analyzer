"""
Defines cluster datatypes.
"""

from abc import abstractmethod
from heapq import merge
from logging import getLogger

from .namedentity import NamedEntity


LOGGER = getLogger(__name__)


class Cluster(object):
    """This class represents a set of random variables and their associated random samples.
    """
    @abstractmethod
    def __iter__(self):
        """Returns an iterator that iterates over sorted individuals in the aggregate random sample.

        The aggregate random sample has been aggregated from the random samples of the random
        variables in the cluster. The individuals are sorted in the ascending order of sample time.

        Returns
        -------
        iterator of .sample.SampledIndividual
            The random sample aggregated from the random samples of the random variables in the
            cluster.
        """
        pass

    def __add__(self, other):
        """Returns the union of two clusters.

        Note
        ----
        Any future changes to the original clusters will be reflected in the merged cluster. To
        materialize the union, pass it to the materialized_cluster constructor.

        Parameters
        ----------
        other : Cluster, int
            The other cluster to be merged with this cluster, or the integer 0 that acts as the
            neutral element.

        Returns
        -------
        LazyUnion
            A new cluster that corresponds to the union of this cluster and the other cluster.
        """
        assert isinstance(other, Cluster) or other == 0
        if other == 0:
            return self
        else:
            return LazyUnion(self, other)

    def __radd__(self, other):
        return self.__add__(other)

    def __repr__(self):
        return "%s" % (self.__class__.__name__)


class LazyUnion(Cluster):
    """This class represents a cluster before the aggregate random sample has been aggregated.

    The aggregate random sample has not yet been aggregated from the random samples of the random
    variables in the cluster.

    Note
    ----
    Future additions of individuals to the random samples of the random variables in the cluster
    will be reflected.

    Parameters
    ----------
    first : Cluster
        The first cluster to be merged
    second : Cluster
        The second cluster to be merged
    """
    def __init__(self, first, second):
        assert isinstance(first, Cluster)
        assert isinstance(second, Cluster)
        self.first = first
        self.second = second
        LOGGER.debug("Lazy-merging clusters %s + %s -> %s", first, second, self)

    def __iter__(self):
        individuals = [None, None]
        first = ((individual, 0, 1) for individual in self.first)
        second = ((individual, 1, 0) for individual in self.second)
        for first_individual, first_individual_index, second_individual_index \
                in merge(first, second):
            second_individual = individuals[second_individual_index]
            if second_individual is not None:
                yield first_individual + second_individual
            else:
                yield first_individual
            individuals[first_individual_index] = first_individual

    def __repr__(self):
        return "%s(%s, %s)" % (self.__class__.__name__, self.first, self.second)


class NamedCluster(Cluster, NamedEntity):
    """This class represents a named cluster.

    Parameters
    ----------
    name : str
        The name of the cluster.
    cluster : Cluster
        A cluster.
    """
    def __init__(self, name, cluster):
        assert isinstance(name, str)
        assert isinstance(cluster, Cluster)
        self._cluster = cluster
        self._name = name

    def __iter__(self):
        return self._cluster.__iter__()

    def getName(self):
        return self._name

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self._name)
