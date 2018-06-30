"""
Defines datatypes for SoundCloud tracks.
"""

from datetime import datetime
from logging import getLogger
from weakref import WeakValueDictionary

from bs4 import BeautifulSoup
from sortedcontainers import SortedSet

from ..core import SampledIndividual, RandomVariable, NamedEntity, fraction


LOGGER = getLogger(__name__)


class SoundCloudTrack(RandomVariable, NamedEntity):
    """This class represents a SoundCloud track along with its associated snapshots.

    Parameters
    ----------
    url : str
        The URL that uniquely identifies the SoundCloud track.

    Attributes
    ----------
    sample : sortedcontainers.SortedSet of SoundCloudTrack.Snapshot
        The associated snapshots.
    """
    _samples = WeakValueDictionary()

    def __init__(self, url):
        self.url = url
        if url in SoundCloudTrack._samples:
            self.sample = SoundCloudTrack._samples[url]
        else:
            self.sample = SortedSet()
            SoundCloudTrack._samples[url] = self.sample

    def _add(self, snapshot):
        """Associate a snapshot with the track.

        Parameters
        ----------
        shapshot : SoundCloudTrack.Snapshot
            The snapshot that will be associated with the track.
        """
        assert isinstance(snapshot, SoundCloudTrack.Snapshot)
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
        """This class represents a SoundCloud track snapshot.

        Parameters
        ----------
        track : SoundCloudTrack or None
            The SoundCloud track the snapshot belongs to. None if the snapshot belongs to a cluster.
            The snapshot is associated with the track immediately after construction.
        title : str or None
            The title the track had at the time of the snapshot. None if the snapshot belongs to a
            cluster.
        date : datetime
            The date, and time at which the snapshot was taken.
        plays : int
            The number of plays the track had at the time of the snapshot.
        downloads : int
            The number of downloads the track had at the time of the snapshot.
        comments : int
            The number of comments the track had at the time of the snapshot.
        likes : int
            The number of likes the track had at the time of the snapshot.

        Attributes
        ----------
        track : SoundCloudTrack or None
            The SoundCloud track the snapshot belongs to. None if the snapshot
            belongs to a cluster.
        title : str or None
            The title the track had at the time of the snapshot. None if the
            snapshot belongs to a cluster.
        date : datetime
            The date, and time at which the snapshot was taken.
        plays : int
            The number of plays the track had at the time of the snapshot.
        downloads : int
            The number of downloads the track had at the time of the snapshot.
        comments : int
            The number of comments the track had at the time of the snapshot.
        likes : int
            The number of likes the track had at the time of the snapshot.
        likes / plays : float
            The ratio between the number of likes, and the number of plays in percent if the number
            of plays is non-zero and zero otherwise.
        """
        def __init__(self, track, title, date, plays, downloads, comments, likes):
            assert isinstance(track, SoundCloudTrack) or track is None
            if title is None:
                assert track is None
            else:
                assert isinstance(title, str)
            assert isinstance(date, datetime)
            assert isinstance(plays, int)
            assert isinstance(downloads, int)
            assert isinstance(comments, int)
            assert isinstance(likes, int)

            self.track = track
            self.title = title
            self.date = date
            self.plays = plays
            self.downloads = downloads
            self.comments = comments
            self.likes = likes
            self.__dict__["likes / plays"] = fraction(likes, plays)

            if self.track:
                self.track._add(self)

        def getDatetime(self):
            return self.date

        def __lt__(self, other):
            return isinstance(other, SoundCloudTrack.Snapshot) and self.date < other.date

        def __le__(self, other):
            return isinstance(other, SoundCloudTrack.Snapshot) and self.date <= other.date

        def __hash__(self):
            return hash((self.track, self.date))

        def __eq__(self, other):
            return isinstance(other, SoundCloudTrack.Snapshot) and self.track == other.track \
                and self.date == other.date

        def __repr__(self):
            return "%s(%s)" % (self.__class__.__name__, self.__dict__)

        def __add__(self, other):
            assert isinstance(other, SoundCloudTrack.Snapshot) or other == 0
            return self if other == 0 else SoundCloudTrack.Snapshot(
                track=None, title=None, date=self.date, plays=self.plays + other.plays,
                downloads=self.downloads + other.downloads,
                comments=self.comments + other.comments, likes=self.likes + other.likes)

        def __getstate__(self):
            return {
                "track": self.track,
                "title": self.title,
                "date": self.date,
                "plays": self.plays,
                "downloads": self.downloads,
                "comments": self.comments,
                "likes": self.likes,
            }

        def __setstate__(self, state):
            self.__init__(**state)

        def __getnewargs__(self):
            return (
                self.track, self.title, self.date, self.plays, self.downloads, self.comments,
                self.likes)

        @staticmethod
        def from_html(track, date, f):
            """Constructs a SoundCloud track snapshot from an HTML dump.

            Parameters
            ----------
            track : SoundCloudTrack or None
                The SoundCloud track the snapshot belongs to.
            date : datetime
                The date, and time at which the dump was taken.
            f : file-like readable object
                The HTML dump.

            Returns
            -------
            SoundCloudTrack.Snapshot
                The snapshot constructed from the HTML dump.
            """
            document = BeautifulSoup(f, "html.parser")
            title = document.find("meta", property="og:title")["content"]
            plays = int(document.find("meta", property="soundcloud:play_count")["content"])
            downloads = int(document.find("meta", property="soundcloud:download_count")["content"])
            comments = int(document.find("meta", property="soundcloud:comments_count")["content"])
            likes = int(document.find("meta", property="soundcloud:like_count")["content"])
            return SoundCloudTrack.Snapshot(track, title, date, plays, downloads, comments, likes)
