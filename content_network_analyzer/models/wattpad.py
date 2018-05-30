"""
Defines datatypes for WattPad books.
"""

from datetime import datetime
from logging import getLogger
from re import compile
from weakref import WeakValueDictionary

from bs4 import BeautifulSoup
from sortedcontainers import SortedSet

from ..core import SampledIndividual, RandomVariable, NamedEntity


LOGGER = getLogger(__name__)


def parse_int(text):
    """Translates a human-readable string into an integer.

    Parameters
    ----------
    text : str
        A human-readable string.

    Returns
    -------
    int
        An integer.
    """
    stripped_text = text.strip().split(' ')[0]
    if stripped_text.endswith('K'):
        return int(round(float(stripped_text[:-1]) * 10**3))
    elif stripped_text.endswith('M'):
        return int(round(float(stripped_text[:-1]) * 10**6))
    else:
        try:
            return int(stripped_text)
        except ValueError:
            raise ValueError('"%s" is not in human-readable format' % stripped_text)


class WattPadBook(RandomVariable, NamedEntity):
    """This class represents a WattPad book along with its associated snapshots.

    Parameters
    ----------
    url : str
        The URL that uniquely identifies the WattPad book.

    Attributes
    ----------
    sample : sortedcontainers.SortedSet of WattPadBook.Snapshot
        The associated snapshots.
    """
    _samples = WeakValueDictionary()

    class Snapshot(SampledIndividual):
        """This class represents a WattPad book snapshot.

        Parameters
        ----------
        book : WattPadBook
            The WattPad book the snapshot belongs to. The snapshot is associated with the book
            immediately after construction.
        title : str
            The title the book had at the time of the snapshot.
        date : datetime
            The date, and time at which the snapshot was taken.
        reads : int
            The number of reads the book has received at the time of the snapshot.
        votes : int
            The number of votes the book has received at the time of the snapshot.

        Attributes
        ----------
        book : WattPadBook or None
            The WattPad book the snapshot belongs to. None if the snapshot belongs to a
            cluster.
        title : str
            The title the book had at the time of the snapshot.
        date : datetime
            The date, and time at which the snapshot was taken.
        reads : int
            The number of reads the book has received at the time of the snapshot.
        votes : int
            The number of votes the book has received at the time of the snapshot.
        votes_reads : float
            The ratio between the number of votes, and the number of reads in percent if the number
            of reads is non-zero and zero otherwise.
        """
        def __init__(self, book, title, date, reads, votes):
            assert isinstance(book, WattPadBook) or book is None
            assert isinstance(title, str) or (title is None and book is None)
            assert isinstance(date, datetime)
            assert isinstance(reads, int)
            assert isinstance(votes, int)

            self.book = book
            self.title = title
            self.date = date
            self.reads = reads
            self.votes = votes
            self.votes_reads = (100.0 * votes / reads) if reads != 0 else 0.0

            if self.book:
                self.book._add(self)

        def getDatetime(self):
            return self.date

        def __lt__(self, other):
            return isinstance(other, WattPadBook.Snapshot) and self.date < other.date

        def __le__(self, other):
            return isinstance(other, WattPadBook.Snapshot) and self.date <= other.date

        def __hash__(self):
            return hash((self.book, self.date))

        def __eq__(self, other):
            return isinstance(other, WattPadBook.Snapshot) and self.book == other.book \
                and self.date == other.date

        def __repr__(self):
            return "%s(%s)" % (self.__class__.__name__, self.__dict__)

        def __add__(self, other):
            assert isinstance(other, WattPadBook.Snapshot)
            return WattPadBook.Snapshot(
                book=None, title=None, date=self.date, reads=self.reads + other.reads,
                votes=self.votes + other.votes)

        def __getstate__(self):
            return {
                "book": self.book,
                "title": self.title,
                "date": self.date,
                "reads": self.reads,
                "votes": self.votes,
            }

        def __setstate__(self, state):
            self.__init__(**state)

        def __getnewargs__(self):
            return (self.book, self.title, self.date, self.reads, self.votes)

        @staticmethod
        def from_html(book, date, f):
            """Constructs a WattPad book snapshot from an HTML dump.

            Parameters
            ----------
            book : WattPadBook or None
                The WattPad book the snapshot belongs to.
            date : datetime
                The date, and time at which the dump was taken.
            f : file-like readable object
                The HTML dump.

            Returns
            -------
            WattPadBook.Snapshot
                The snapshot constructed from the HTML dump.
            """
            document = BeautifulSoup(f, "html.parser")
            title = document.find("h1").text.strip()
            reads = parse_int(document.find(
                "span", {"data-toggle": "tooltip"}, text=compile(r".* Reads")).text)
            votes = parse_int(document.find(
                "span", {"data-toggle": "tooltip"}, text=compile(r".* Votes")).text)
            return WattPadBook.Snapshot(book, title, date, reads, votes)

    def __init__(self, url):
        self.url = url
        if url in WattPadBook._samples:
            self.sample = WattPadBook._samples[url]
        else:
            self.sample = SortedSet()
            WattPadBook._samples[url] = self.sample

    def _add(self, snapshot):
        """Associate a snapshot with the book.

        Parameters
        ----------
        shapshot : WattPadBook.Snapshot
            The snapshot that will be associated with the book.
        """
        assert isinstance(snapshot, WattPadBook.Snapshot)
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
