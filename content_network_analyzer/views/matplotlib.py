"""
Defines datatypes for MatPlotLib plotting.
"""

from datetime import datetime
from itertools import cycle, product
from pytz import UTC

import matplotlib  # noqa:F401
from matplotlib.dates import MonthLocator, DateFormatter
from matplotlib.figure import Figure  # noqa:F401
from matplotlib.axes._axes import Axes  # noqa:F401

from ..core import Cluster, NamedEntity, View


DATETIME_MIN = UTC.localize(datetime.min)
DATETIME_MAX = UTC.localize(datetime.max)
LINEWIDTH = 2
LINES = ["-", "--", "-.", ":"]
COLORS = [
    (31, 119, 180), (174, 199, 232), (255, 127, 14), (255, 187, 120), (44, 160, 44),
    (152, 223, 138), (214, 39, 40), (255, 152, 150), (148, 103, 189), (197, 176, 213),
    (140, 86, 75), (196, 156, 148), (227, 119, 194), (247, 182, 210), (127, 127, 127),
    (199, 199, 199), (188, 189, 34), (219, 219, 141), (23, 190, 207), (158, 218, 229),
]
LABEL_MAX_LENGTH = 100


class MatPlotLibView(View):
    """This class represents a view that plots an iterable of named clusters using MatPlotLib.

    Parameters
    ----------
    clusters : iterable of Cluster and NamedEntity
        The named clusters to view.

    Attributes
    ----------
    clusters : sequence of Cluster and NamedEntity
        The named clusters to view.
    """
    def __init__(self, clusters):
        cluster_list = list(clusters)
        for cluster in cluster_list:
            assert isinstance(cluster, Cluster)
            assert isinstance(cluster, NamedEntity)

        self.clusters = cluster_list

    def display(self, fig, ax, attr, mindate=DATETIME_MIN, maxdate=DATETIME_MAX):
        """Displays an iterable of clusters in a given datetime range.

        Parameters
        ----------
        fig : Figure
            A MatPlotLib figure that will be used for plotting.
        ax : Axes
            MatPlotLib axes that will be used for plotting.
        attr : str
            The attribute of the cluster that will be plotted.
        mindate : datetime, optional
            The minimal datetime that will be displayed.
        maxdate : datetime, optional
            The maximal datetime that will be displayed.
        """
        ax.xaxis.set_major_locator(MonthLocator())
        ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
        ax.grid(True)
        ax.set_ylabel(attr)

        lineformats = cycle(product(LINES, [(r/255., g/255., b/255.) for (r, g, b) in COLORS]))
        latest_values = {}
        for cluster in self.clusters:
            individuals = [
                individual for individual in cluster
                if individual.getDatetime() >= mindate and individual.getDatetime() <= maxdate]
            dates, values = list(zip(*(
                (individual.getDatetime(), individual.__dict__[attr])
                for individual in individuals if attr in individual.__dict__))) or ([], [])
            if not values:
                continue
            cluster_name = cluster.getName()
            if len(cluster_name) <= LABEL_MAX_LENGTH:
                label = cluster_name
            else:
                label = cluster_name[:LABEL_MAX_LENGTH - 1] + "…"
            linefmt, linecolor = next(lineformats)
            ax.plot_date(
                dates, values, fmt=linefmt, linewidth=LINEWIDTH, c=linecolor, label=label)
            latest_values[label] = values[-1]
        sorted_handles = [
            (handle, cluster_name) for handle, cluster_name, _
            in sorted([
                (handle, label, latest_values[label])
                for handle, label
                in zip(*ax.get_legend_handles_labels())
            ], key=lambda x: x[2], reverse=True)]
        ax.legend(
            [handle for handle, _ in sorted_handles],
            [label for _, label in sorted_handles],
            loc="upper left", bbox_to_anchor=(1, 1))

        fig.autofmt_xdate()
