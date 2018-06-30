"""
Defines datatypes for YouTube tracks.
"""

from datetime import datetime
from logging import getLogger
from weakref import WeakValueDictionary

from bs4 import BeautifulSoup
from sortedcontainers import SortedSet

from ..core import SampledIndividual, RandomVariable, NamedEntity, fraction, parse_int


LOGGER = getLogger(__name__)


class YouTubeTrack(RandomVariable, NamedEntity):
    """This class represents a YouTube track along with its associated snapshots.

    Parameters
    ----------
    url : str
        The URL that uniquely identifies the YouTube track.

    Attributes
    ----------
    sample : sortedcontainers.SortedSet of YouTubeTrack.Snapshot
        The associated snapshots.
    """
    _samples = WeakValueDictionary()

    def __init__(self, url):
        self.url = url
        if url in YouTubeTrack._samples:
            self.sample = YouTubeTrack._samples[url]
        else:
            self.sample = SortedSet()
            YouTubeTrack._samples[url] = self.sample

    def _add(self, snapshot):
        """Associate a snapshot with the track.

        Parameters
        ----------
        shapshot : YouTubeTrack.Snapshot
            The snapshot that will be associated with the track.
        """
        assert isinstance(snapshot, YouTubeTrack.Snapshot)
        self.sample.add(snapshot)

    def getName(self):
        return self.sample[-1].title if self.sample else "(unknown title)"

    def __repr__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            ("%s \"%s\"" % (self.url, self.getName())) if self.sample else self.url)

    def __hash__(self):
        return hash(self.url)

    def __getstate__(self):
        return self.url

    def __setstate__(self, url):
        self.__init__(url)

    def __getnewargs__(self):
        return (self.url, )

    class Snapshot(SampledIndividual):
        """This class represents a YouTube track snapshot.

        Parameters
        ----------
        track : YouTubeTrack or None
            The YouTube track the snapshot belongs to. None if the snapshot belongs to a cluster.
            The snapshot is associated with the track immediately after construction.
        title : str or None
            The title the track had at the time of the snapshot. None if the snapshot belongs to a
            cluster.
        date : datetime
            The date, and time at which the snapshot was taken.
        views : int
            The number of views the track had at the time of the snapshot.
        likes : int
            The number of likes the track had at the time of the snapshot.
        dislikes : int
            The number of dislikes the track had at the time of the snapshot.

        Attributes
        ----------
        track : YouTubeTrack or None
            The YouTube track the snapshot belongs to. None if the snapshot
            belongs to a cluster.
        title : str or None
            The title the track had at the time of the snapshot. None if the
            snapshot belongs to a cluster.
        date : datetime
            The date, and time at which the snapshot was taken.
        views : int
            The number of views the track had at the time of the snapshot.
        likes : int
            The number of likes the track had at the time of the snapshot.
        dislikes : int
            The number of dislikes the track had at the time of the snapshot.
        likes / views : float
            The ratio between the number of likes, and the number of views in percent if the number
            of views is non-zero and zero otherwise.
        likes / (likes + dislikes) : float
            The ratio between the number of likes, and the number of likes and dislikes in percent
            if the number of likes and dislikes is non-zero and zero otherwise.
        """
        def __init__(self, track, title, date, views, likes, dislikes):
            assert isinstance(track, YouTubeTrack) or track is None
            if title is None:
                assert track is None
            else:
                assert isinstance(title, str)
            assert isinstance(date, datetime)
            assert isinstance(views, int)
            assert isinstance(likes, int)
            assert isinstance(dislikes, int)

            self.track = track
            self.title = title
            self.date = date
            self.views = views
            self.likes = likes
            self.__dict__["likes / views"] = fraction(likes, views)
            self.dislikes = dislikes
            self.__dict__["likes / (likes + dislikes)"] = fraction(likes, likes + dislikes)

            if self.track:
                self.track._add(self)

        def getDatetime(self):
            return self.date

        def __hash__(self):
            return hash((self.track, self.date))

        def __eq__(self, other):
            return isinstance(other, YouTubeTrack.Snapshot) and self.track == other.track \
                and self.date == other.date

        def __repr__(self):
            return "%s(%s)" % (self.__class__.__name__, self.__dict__)

        def __add__(self, other):
            assert isinstance(other, YouTubeTrack.Snapshot) or other == 0
            return self if other == 0 else YouTubeTrack.Snapshot(
                track=None, title=None, date=self.date, views=self.views + other.views,
                likes=self.likes + other.likes, dislikes=self.dislikes + other.dislikes)

        def __getstate__(self):
            return {
                "track": self.track,
                "title": self.title,
                "date": self.date,
                "views": self.views,
                "likes": self.likes,
                "dislikes": self.dislikes,
            }

        def __setstate__(self, state):
            self.__init__(**state)

        def __getnewargs__(self):
            return (self.track, self.title, self.date, self.views, self.likes, self.dislikes)

        @staticmethod
        def from_html(track, date, f):
            """Constructs a YouTube track snapshot from an HTML dump.

            Parameters
            ----------
            track : YouTubeTrack or None
                The YouTube track the snapshot belongs to.
            date : datetime
                The date, and time at which the dump was taken.
            f : file-like readable object
                The HTML dump.

            Returns
            -------
            YouTubeTrack.Snapshot
                The snapshot constructed from the HTML dump.
            """
            document = BeautifulSoup(f, "html.parser")
            title = document.find("meta", property="og:title")["content"]
            views = parse_int(document.find("div", {"class": "watch-view-count"}).text)
            likes = parse_int(
                document.find("button", {"class": "like-button-renderer-like-button"}).text)
            dislikes = parse_int(
                document.find("button", {"class": "like-button-renderer-dislike-button"}).text)
            return YouTubeTrack.Snapshot(track, title, date, views, likes, dislikes)
