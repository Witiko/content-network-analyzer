"""
Defines datatypes for GitHub repositories.
"""

from datetime import datetime
from heapq import merge
from logging import getLogger
import re
from weakref import WeakValueDictionary

from bs4 import BeautifulSoup
from bs4.element import Tag
from sortedcontainers import SortedSet

from ..core import SampledIndividual, RandomVariable, Cluster, NamedEntity


LICENSE_FILENAMES = ["COPYING", "LICENSE", "LICENSE.md", "LICENSE.txt"]
LOGGER = getLogger(__name__)


def parse_percentage(text):
    """Translates percentage into a ratio in the range [0; 1].

    Parameters
    ----------
    text : str
        A percentage.

    Returns
    -------
    float
        A ratio in the range [0; 1].
    """
    assert isinstance(text, str)

    match = re.match(r"([\d.]+)%", text.strip())
    assert match, "Can't parse \"%s\" as a percentage" % text

    ratio = float(match.group(1)) / 100.0
    assert ratio >= 0.0 and ratio <= 1.0, "Ratio %f is outside the range [0; 1]"

    return ratio


def parse_counter_text(text):
    """Translates an integer with thousands-separators (e.g. "3,619") into an integer (e.g. 3619).

    Parameters
    ----------
    text : str
        An integer with thousands-separators.

    Returns
    -------
    int
        An integer.
    """
    assert isinstance(text, str)

    return int(text.replace(',', ""))


def read_navitem_counter(document, target):
    """Reads the value of an integer counter from a navigation menu item.

    Parameters
    ----------
    document : Tag
        The document in which the counter is sought.
    target : str
        The target of the navigation menu item, such as issues, pulls, or projects.

    Returns
    -------
    int
        The value of the counter.
    """
    assert isinstance(document, Tag)
    assert isinstance(target, str)

    navitem = document.find("a", {
        "class": "reponav-item",
        "href": lambda x: x.endswith("/%s" % target)})

    if not navitem:
        LOGGER.debug("Navigation menu item pointing to \"%s\" not found", target)
        return 0

    counter = navitem.find("span", {"class": "Counter"})
    assert counter, "Navigation menu item pointing to \"%s\" has no counter" % target

    return int(counter.text)


def read_summary_counter(document, target):
    """
    Reads the value of an integer counter from a summary item.

    Parameters
    ----------
    document : Tag
        The document in which the counter is sought.
    target : str
        The target of the navigation menu item, such as commits, branches, or releases.

    Returns
    -------
    int
        The value of the counter.
    """
    assert isinstance(document, Tag)
    assert isinstance(target, str)

    navitem = document.find("li", {"class": target}) or document.find("a", {
        "href": lambda x: x.endswith("/%s" % target)})
    assert navitem, "Summary item pointing to \"%s\" not found" % target

    counter = navitem.find("span", {"class": "num"})
    assert counter, "Summary item pointing to \"%s\" has no counter" % target

    return parse_counter_text(counter.text)


def read_social_counter(document, target):
    """
    Reads the value of an integer counter from a social button.

    Parameters
    ----------
    document : Tag
        The document in which the counter is sought.
    target : str
        The target of the navigation menu item, such as watchers, stargazers, or network.

    Returns
    -------
    int
        The value of the counter.
    """
    assert isinstance(document, Tag)
    assert isinstance(target, str)

    button = document.find("a", {
        "class": "social-count", "href": lambda x: x.endswith("/%s" % target)})
    assert button, "Social button pointing to \"%s\" not found" % target

    return parse_counter_text(button.text)


class Language(Cluster, NamedEntity):
    """This class represents a language, and its ratio in named GitHub repository clusters.

    Parameters
    ----------
    language : str
        The name of the represented language. The name is case-insensitive.
    clusters : iterator of Cluster
        An iterable of named GitHub repository clusters to view.

    Attributes
    ----------
    language : str
        The name of the represented language. The name is case-insensitive.
    clusters : iterable of Cluster
        An iterable of named GitHub repository clusters to view.
    """
    def __init__(self, language, clusters):
        assert isinstance(language, str)
        cluster_list = list(clusters)
        for cluster in cluster_list:
            assert isinstance(cluster, Cluster)

        self.clusters = cluster_list
        self.language = language

    def __iter__(self):
        tagged_samples = (
            [(individual, cluster) for individual in cluster]
            for cluster in self.clusters)
        previous_date = None
        previous_languages = {}
        future_yield = None
        for snapshot, cluster in merge(*tagged_samples):
            assert isinstance(snapshot, GitHubRepository.Snapshot)
            assert isinstance(snapshot.languages, Language.AverageRatios)
            assert isinstance(snapshot.date, datetime)
            previous_languages[cluster] = snapshot.languages
            projection = Language.AverageRatiosProjection(
                set((self.language,)), dict(previous_languages))

            if previous_date is None:  # Squash together snapshots with the same datetime.
                previous_date = snapshot.date
            assert isinstance(previous_date, datetime)
            if snapshot.date > previous_date:
                previous_date = snapshot.date
                if future_yield:
                    yield future_yield
                future_yield = projection
            elif not future_yield or len(projection.clusters) > len(future_yield.clusters):
                future_yield = projection
        if future_yield:
            yield future_yield

    def getName(self):
        return self.language

    class AverageRatiosProjection(SampledIndividual):
        """This class represents the ratio of a set of prog. languages in clusters of repositories.

        Parameters
        ----------
        languages : set of str
            The name of the represented languages. The names are case-insensitive.
        clusters : dict of (Cluster, AverageRatios)
            The clusters of repositories, each with programming language ratios.

        Attributes
        ----------
        languages : set of str
            The names of the represented languages. The names are case-insensitive.
        clusters : dict of (Cluster, AverageRatios)
            The clusters of repositories, each with programming language ratios.
        __dict__ : dict of (Cluster, float)
            The ratio of the represented languages in cluster c is available in __dict__[c].
        """
        def __init__(self, languages, clusters):
            assert isinstance(languages, set)

            self.languages = languages
            self.clusters = clusters

            for cluster, average_ratios_iterator in self.clusters.items():
                average_ratios = dict(
                    (language.lower(), ratio) for (language, ratio) in average_ratios_iterator)
                self.__dict__[cluster] = sum(
                    average_ratios[language.lower()] for language in languages
                    if language.lower() in average_ratios.keys())

        def getDatetime(self):
            return max(average_ratios.date for average_ratios in self.clusters.values())

        def __add__(self, other):
            assert isinstance(other, Language.AverageRatiosProjection) or other == 0
            return self if other == 0 else Language.AverageRatiosProjection(
                languages=self.languages | other.languages, clusters=max(self, other).clusters)

        def __repr__(self):
            return "%s(%s, %s, %s)" % (
                self.__class__.__name__, self.getDatetime(), self.languages, self.clusters.keys())

    class AverageRatios(SampledIndividual):
        """This class represents programming language ratios of a cluster of repositories.

        Parameters
        ----------
        date : datetime
            The date, and time at which the snapshot of the language ratios was taken.
        sample : iterator of Language.Ratios
            The programming language ratios of individual repositories.

        Attributes
        ----------
        date : datetime
            The date, and time at which the snapshot of the language ratios was taken.
        sample : iterable of Language.Ratios
            The programming language ratios of individual repositories.
        """
        def __init__(self, date, sample):
            assert isinstance(date, datetime)
            sample_list = list(sample)
            assert len(sample_list)

            self.date = date
            self.sample = sample_list

        def getDatetime(self):
            return self.date

        def _average(self):
            """Returns average programming language ratios of the cluster of repositories.

            Returns
            -------
            Language.Ratios
                The arithmetic mean of programming language ratios of the cluster.
            """
            languages = dict()
            for ratios in self.sample:
                for language in ratios.languages.keys():
                    if language not in languages:
                        languages[language] = []
                    assert language in languages
                    languages[language].append(ratios)
            ratios = Language.Ratios(
                (name, sum(ratios.languages[name] for ratios in sample) / len(self.sample))
                for name, sample in languages.items())
            return ratios

        def __iter__(self):
            """Iterates over the programming languages, and their mean usage ratios in the cluster.

            Yields
            ------
            (str, double)
                Programming languages, and the arithmetic mean of their usage ratios in the cluster.
            """
            for name, ratio in self._average():
                yield (name, ratio)

        def __add__(self, other):
            assert isinstance(other, Language.AverageRatios) or other == 0
            return self if other == 0 else Language.AverageRatios(
                date=max(self.date, other.date), sample=self.sample + other.sample)

        def __repr__(self):
            return "%s(%s)" % (self.__class__.__name__, self.sample)

    class Ratios(object):
        """This class represents the programming language ratios of a repository.

        Parameters
        ----------
        languages : iterator of (str, double)
            Programming languages, and their usage ratios in a repository.

        Attributes
        ----------
        languages : dict of (str, double)
            Programming languages, and their usage ratios in a repository.
        """
        def __init__(self, languages):
            language_dict = dict()
            for name, ratio in languages:
                assert isinstance(name, str)
                assert isinstance(ratio, float)
                if ratio <= 0.0 or ratio > 1.0:
                    raise ValueError("Ratio %f is outside the range (0; 1]" % ratio)
                language_dict[name] = ratio
            self.languages = language_dict

        def __iter__(self):
            """Iterates over the programming languages, and their usage ratios.

            Yields
            ------
            (str, double)
                Programming languages, and their usage ratios in a repository.
            """
            for name, ratio in self.languages.items():
                yield (name, ratio)

        def __repr__(self):
            return "%s(%s)" % (self.__class__.__name__, self.languages.items())


class GitHubRepository(RandomVariable, NamedEntity):
    """This class represents a GitHub repository along with its associated snapshots.

    Parameters
    ----------
    url : str
        The URL that uniquely identifies the GitHub repository.

    Attributes
    ----------
    sample : sortedcontainers.SortedSet of GitHubRepository.Snapshot
        The associated snapshots.
    owner : str
        The nickname of the owner of the repository.
    title : str
        The title of the repository.
    """
    _samples = WeakValueDictionary()

    def __init__(self, url):
        assert isinstance(url, str)

        self.url = url
        self.owner, self.title = url.split('/')[-2:]
        if url in GitHubRepository._samples:
            self.sample = GitHubRepository._samples[url]
        else:
            self.sample = SortedSet()
            GitHubRepository._samples[url] = self.sample

    def _add(self, snapshot):
        """Associate a snapshot with the repository.

        Parameters
        ----------
        shapshot : GitHubRepository.Snapshot
            The snapshot that will be associated with the repository.
        """
        assert isinstance(snapshot, GitHubRepository.Snapshot)
        self.sample.add(snapshot)

    def getName(self):
        if self.sample:
            return "%s/%s" % (self.sample[-1].owner, self.sample[-1].title)
        else:
            return "%s/%s" % (self.owner, self.title)

    def getLanguages(self):
        """Returns languages from the latest snapshot, or an empty set if no snapshot exists.

        Returns
        -------
        set of str
            The languages of the latest snapshot, or an empty set if no snapshot exists.
        """
        if self.sample:
            return set(dict(self.sample[-1].languages).keys())
        else:
            return set()

    def getOwner(self):
        """Returns the nickname of the owner of the repository.

        Returns
        -------
        str
            The nickname of the owner of the repository.
        """
        if self.sample:
            return self.sample[-1].owner
        else:
            return self.owner

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
        """This class represents a GitHub repository snapshot.

        Parameters
        ----------
        repository : GitHubRepository or None
            The GitHub repository the snapshot belongs to. The snapshot is associated with the
            repository immediately after construction. None if the snapshot belongs to a cluster.
        owner : str or None
            The owner of the repository at the time of the snapshot. None if the snapshot belongs to
            a cluster.
        title : str or None
            The title the repository had at the time of the snapshot. None if the snapshot belongs
            to a cluster.
        date : datetime
            The date, and time at which the snapshot was taken.
        watching : int
            The number of accounts watching.
        stars : int
            The number of stars.
        forks : int
            The number of forks.
        issues : int
            The number of open issues.
        pull_requests : int
            The number of open pull requests.
        projects : int
            The number of active projects.
        commits : int
            The number of commits.
        branches : int
            The number of branches.
        releases : int
            The number of releases.
        license : str or None
            The license of the repository.
        languages : Language.AverageRatios
            The programming languages used in this repository or cluster.

        Attributes
        ----------
        repository : GitHubRepository or None
            The GitHub repository the snapshot belongs to. None if the snapshot belongs to a
            cluster.
        owner : str or None
            The owner of the repository at the time of the snapshot. None if the snapshot belongs to
            a cluster.
        title : str or None
            The title the repository had at the time of the snapshot. None if the snapshot belongs
            to a cluster.
        date : datetime
            The date, and time at which the snapshot was taken.
        watching : int
            The number of accounts watching.
        stars : int
            The number of stars.
        forks : int
            The number of forks.
        issues : int
            The number of open issues.
        pull_requests : int
            The number of open pull requests.
        projects : int
            The number of active projects.
        commits : int
            The number of commits.
        branches : int
            The number of branches.
        releases : int
            The number of releases.
        license : set of str
            The licenses of the repository
        languages : Language.AverageRatios
            The programming languages used in this repository or cluster.
        """
        def __init__(
                self, repository, owner, title, date, watching, stars, forks, issues, pull_requests,
                projects, commits, branches, releases, licenses, languages):
            assert isinstance(repository, GitHubRepository) or repository is None
            if owner is None or title is None:
                assert repository is None
            else:
                assert isinstance(owner, str)
                assert isinstance(title, str)
            assert isinstance(date, datetime)
            assert isinstance(watching, int)
            assert isinstance(stars, int)
            assert isinstance(forks, int)
            assert isinstance(issues, int)
            assert isinstance(pull_requests, int)
            assert isinstance(projects, int)
            assert isinstance(commits, int)
            assert isinstance(branches, int)
            assert isinstance(releases, int)
            assert isinstance(languages, Language.AverageRatios)

            self.repository = repository
            self.owner = owner
            self.title = title
            self.date = date
            self.watching = watching
            self.stars = stars
            self.forks = forks
            self.issues = issues
            self.pull_requests = pull_requests
            self.projects = projects
            self.commits = commits
            self.branches = branches
            self.releases = releases
            self.licenses = set(licenses)
            self.languages = languages

            if self.repository:
                self.repository._add(self)

        def getDatetime(self):
            return self.date

        def __hash__(self):
            return hash((self.repository, self.date))

        def __eq__(self, other):
            return isinstance(other, GitHubRepository.Snapshot) \
                and self.repository == other.repository \
                and self.date == other.date

        def __repr__(self):
            return "%s(%s)" % (self.__class__.__name__, self.__dict__)

        def __add__(self, other):
            assert isinstance(other, GitHubRepository.Snapshot) or other == 0
            return self if other == 0 else GitHubRepository.Snapshot(
                repository=None, owner=None, title=None, date=max(self.date, other.date),
                watching=self.watching + other.watching, stars=self.stars + other.stars,
                forks=self.forks + other.forks, issues=self.issues + other.issues,
                pull_requests=self.pull_requests + other.pull_requests,
                projects=self.projects + other.projects, commits=self.commits + other.commits,
                branches=self.branches + other.branches, releases=self.releases + other.releases,
                licenses=self.licenses | other.licenses, languages=self.languages + other.languages)

        def __getstate__(self):
            return {
                "repository": self.repository,
                "owner": self.owner,
                "title": self.title,
                "date": self.date,
                "watching": self.watching,
                "stars": self.stars,
                "forks": self.forks,
                "issues": self.issues,
                "pull_requests": self.pull_requests,
                "projects": self.projects,
                "commits": self.commits,
                "branches": self.branches,
                "releases": self.releases,
                "licenses": tuple(self.licenses),
                "languages": self.languages,
            }

        def __setstate__(self, state):
            self.__init__(**state)

        def __getnewargs__(self):
            return (
                self.repository, self.owner, self.title, self.date, self.watching, self.stars,
                self.forks, self.issues, self.pull_requests, self.projects, self.commits,
                self.branches, self.releases, self.licenses, self.languages)

        @staticmethod
        def from_html(repository, date, f):
            """Constructs a GitHub repository snapshot from an HTML dump.

            Parameters
            ----------
            repository : GitHubRepository or None
                The GitHub repository the snapshot belongs to.
            date : datetime
                The date, and time at which the dump was taken.
            f : file-like readable object
                The HTML dump.

            Returns
            -------
            GitHubRepository.Snapshot
                The snapshot constructed from the HTML dump.
            """
            document = BeautifulSoup(f, "html.parser")
            assert document, "Not an HTML document"

            title_element = document.find("meta", {"property": "og:title"})
            assert title_element, "Title not found"

            owner, title = title_element["content"].split('/')

            watching = read_social_counter(document, "watchers")
            stars = read_social_counter(document, "stargazers")
            forks = read_social_counter(document, "network")

            issues = read_navitem_counter(document, "issues")
            pull_requests = read_navitem_counter(document, "pulls")
            projects = read_navitem_counter(document, "projects")

            commits = read_summary_counter(document, "commits")
            branches = read_summary_counter(document, "branches")
            releases = read_summary_counter(document, "releases")

            summary_element = document.find("div", {"class": "overall-summary"})
            assert summary_element, "Summary not found"

            license_element = summary_element.find("a", {
                "href": lambda x: any(
                    x.endswith("/%s" % filename)
                    for filename in LICENSE_FILENAMES)})
            if license_element:
                licenses = set((license_element.text.strip(),))
            else:
                licenses = set()

            language_stats_element = document.find("div", {"class": "repository-lang-stats"})
            if language_stats_element:
                language_elements = language_stats_element.find_all("li")
                languages = []
            else:
                language_elements = []
                languages = [("Other", 1.0)]

            for language_element in language_elements:
                language_name_element = language_element.find("span", {"class": "lang"})
                assert language_name_element, "No name found for a language"

                language_name = language_name_element.text

                language_percent_element = language_element.find("span", {"class": "percent"})
                assert language_percent_element, \
                    "No percentage found for language %s" % language_name

                language_ratio = parse_percentage(language_percent_element.text)
                languages.append((language_name, language_ratio))

            return GitHubRepository.Snapshot(
                    repository, owner, title, date, watching, stars, forks, issues, pull_requests,
                    projects, commits, branches, releases, licenses,
                    Language.AverageRatios(date, (Language.Ratios(languages),)))
