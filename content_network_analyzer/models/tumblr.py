"""
Defines datatypes for Tumblr posts.
"""

from datetime import datetime
from logging import getLogger
from weakref import WeakValueDictionary

from bs4 import BeautifulSoup
from sortedcontainers import SortedSet

from ..core import SampledIndividual, RandomVariable, NamedEntity, parse_int


LOGGER = getLogger(__name__)


class TumblrPost(RandomVariable, NamedEntity):
    """This class represents a Tumblr post along with its associated snapshots.

    Parameters
    ----------
    url : str
        The URL that uniquely identifies the Tumblr post.

    Attributes
    ----------
    sample : sortedcontainers.SortedSet of TumblrPost.Snapshot
        The associated snapshots.
    """
    _samples = WeakValueDictionary()

    def __init__(self, url):
        self.url = url
        if url in TumblrPost._samples:
            self.sample = TumblrPost._samples[url]
        else:
            self.sample = SortedSet()
            TumblrPost._samples[url] = self.sample

    def _add(self, snapshot):
        """Associate a snapshot with the post.

        Parameters
        ----------
        shapshot : TumblrPost.Snapshot
            The snapshot that will be associated with the post.
        """
        assert isinstance(snapshot, TumblrPost.Snapshot)
        self.sample.add(snapshot)

    def getName(self):
        return self.sample[-1].title if self.sample else "(unknown title)"

    def getTags(self):
        """Returns the tags of the latest snapshot, or an empty set if no snapshot exists.

        Returns
        -------
        set of str
            The tags of the latest snapshot, or an empty set if no snapshot exists.
        """
        return self.sample[-1].tags if self.sample else set()

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
        """This class represents a Tumblr post snapshot.

        Parameters
        ----------
        post : TumblrPost or None
            The Tumblr post the snapshot belongs to. The snapshot is associated with the post
            immediately after construction. None if the snapshot belongs to a cluster.
        title : str or None
            The title the post had at the time of the snapshot. None if the snapshot belongs to a
            cluster.
        date : datetime
            The date, and time at which the snapshot was taken.
        tags : iterator of str
            The tags the post has at the time of the snapshot.
        notes : int
            The number of notes the post had at the time of the snapshot.

        Attributes
        ----------
        post : TumblrPost or None
            The Tumblr post the snapshot belongs to. None if the snapshot belongs to a cluster.
        title : str or None
            The title the post had at the time of the snapshot. None if the snapshot belongs to a
            cluster.
        date : datetime
            The date, and time at which the snapshot was taken.
        tags : set of str
            The tags the post has at the time of the snapshot.
        notes : int
            The number of notes the post had at the time of the snapshot.
        """
        def __init__(self, post, title, date, tags, notes):
            assert isinstance(post, TumblrPost) or post is None
            assert isinstance(title, str) or (title is None and post is None)
            assert isinstance(date, datetime)
            assert isinstance(notes, int)

            self.post = post
            self.title = title
            self.date = date
            self.tags = set(tags)
            self.notes = notes

            if self.post:
                self.post._add(self)

        def getDatetime(self):
            return self.date

        def __lt__(self, other):
            return isinstance(other, TumblrPost.Snapshot) and self.date < other.date

        def __le__(self, other):
            return isinstance(other, TumblrPost.Snapshot) and self.date <= other.date

        def __hash__(self):
            return hash((self.post, self.date))

        def __eq__(self, other):
            return isinstance(other, TumblrPost.Snapshot) and self.post == other.post \
                and self.date == other.date

        def __repr__(self):
            return "%s(%s)" % (self.__class__.__name__, self.__dict__)

        def __add__(self, other):
            assert isinstance(other, TumblrPost.Snapshot)
            return TumblrPost.Snapshot(
                post=None, title=None, date=self.date, tags=self.tags & other.tags,
                notes=self.notes + other.notes)

        def __getstate__(self):
            return {
                "post": self.post,
                "title": self.title,
                "date": self.date,
                "tags": tuple(self.tags),
                "notes": self.notes,
            }

        def __setstate__(self, state):
            self.__init__(**state)

        def __getnewargs__(self):
            return (self.post, self.title, self.date, tuple(self.tags), self.notes)

        @staticmethod
        def from_html(post, date, f):
            """Constructs a Tumblr post snapshot from an HTML dump.

            Parameters
            ----------
            post : TumblrPost or None
                The Tumblr post the snapshot belongs to.
            date : datetime
                The date, and time at which the dump was taken.
            f : file-like readable object
                The HTML dump.

            Returns
            -------
            TumblrPost.Snapshot
                The snapshot constructed from the HTML dump.
            """
            document = BeautifulSoup(f, "html.parser")
            assert document, "Not an HTML document"

            description_element = document.find("meta", {"name": "description"}) \
                or document.find("meta", {"property": "og:description"})
            assert description_element, "Description not found"

            description = description_element["content"]

            tags_element = document.find("meta", {"name": "keywords"})
            assert tags_element, "Tags not found"

            tags = tags_element["content"].split(',')
            title = description if description else ' '.join(tags)

            post_element = document.find("div", {"class": "main"}).find("article")
            assert post_element, "Post element not found"

            notes_element = post_element.find("a", {"class": "post-notes"})
            notes = parse_int(notes_element.text) if notes_element else 0

            return TumblrPost.Snapshot(post, title, date, tags, notes)
