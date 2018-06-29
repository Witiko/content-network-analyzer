"""
This module contains unit tests for the github module.
"""

from dateutil.parser import parse
from logging import getLogger
from pathlib import Path
import unittest

from .github import Language, GitHubRepository


Snapshot = GitHubRepository.Snapshot


RESOURCES = Path(__file__).parents[0] / Path("resources")
HTML_DOCUMENT_BOOTSTRAP = RESOURCES / Path("github-repository-bootstrap.html")
HTML_DOCUMENT_GIT = RESOURCES / Path("github-repository-git.html")
LOGGER = getLogger(__name__)
REPOSITORY_URL_BOOTSTRAP = "https://github.com/twbs/bootstrap"
REPOSITORY_URL_GIT = "https://github.com/git/git"
SNAPSHOT_DATE = parse("2018-05-29T16:18:21+02:00")


class TestLanguageRatios(unittest.TestCase):
    def setUp(self):
        self.ratios = Language.Ratios([("python", 0.1), ("java", 0.2), ("C", 0.7)])

    def test_invalid_ratios(self):
        with self.assertRaises(ValueError):
            Language.Ratios([("python", 1.2)])
        with self.assertRaises(ValueError):
            Language.Ratios([("java", -0.4)])

    def test_read_back_ratios(self):
        self.assertTrue("python" in self.ratios.languages)
        self.assertTrue("java" in self.ratios.languages)
        self.assertTrue("C" in self.ratios.languages)

        self.assertEqual(0.1, self.ratios.languages["python"])
        self.assertEqual(0.2, self.ratios.languages["java"])
        self.assertEqual(0.7, self.ratios.languages["C"])

    def test_iter(self):
        languages = dict(self.ratios)

        self.assertTrue("python" in languages)
        self.assertTrue("java" in languages)
        self.assertTrue("C" in languages)

        self.assertEqual(0.1, languages["python"])
        self.assertEqual(0.2, languages["java"])
        self.assertEqual(0.7, languages["C"])


class TestLanguageAverageRatios(unittest.TestCase):
    def setUp(self):
        self.ratios = [
            Language.Ratios([("python", 0.1), ("java", 0.2), ("C", 0.7)]),
            Language.Ratios([("python", 0.5), ("java", 0.5)]),
            Language.Ratios([("java", 0.5), ("C", 0.5)])]

    def test_add(self):
        average_ratios = sum(
            Language.AverageRatios(SNAPSHOT_DATE, (ratio,)) for ratio in self.ratios)
        self.assertEqual(len(self.ratios), len(average_ratios.sample))
        self.assertEqual(SNAPSHOT_DATE, average_ratios.date)

    def test_iter(self):
        average_ratios = Language.AverageRatios(SNAPSHOT_DATE, self.ratios)
        self.assertEqual(SNAPSHOT_DATE, average_ratios.date)

        languages = dict(average_ratios)

        self.assertTrue("python" in languages)
        self.assertTrue("java" in languages)
        self.assertTrue("C" in languages)

        self.assertEqual((0.1 + 0.5 + 0.0) / 3, languages["python"])
        self.assertEqual((0.2 + 0.5 + 0.5) / 3, languages["java"])
        self.assertEqual((0.7 + 0.0 + 0.5) / 3, languages["C"])


class TestGitHubRepositorySnapshot(unittest.TestCase):
    def test_from_html_bootstrap(self):
        repository = GitHubRepository(REPOSITORY_URL_BOOTSTRAP)
        with HTML_DOCUMENT_BOOTSTRAP.open("rt", encoding="utf8") as f:
            snapshot = Snapshot.from_html(repository, SNAPSHOT_DATE, f)
        self.assertEqual(repository, snapshot.repository)
        self.assertEqual("twbs", snapshot.owner)
        self.assertEqual("bootstrap", snapshot.title)
        self.assertEqual(SNAPSHOT_DATE, snapshot.date)
        self.assertEqual(7356, snapshot.watching)
        self.assertEqual(125696, snapshot.stars)
        self.assertEqual(60569, snapshot.forks)
        self.assertEqual(400, snapshot.issues)
        self.assertEqual(123, snapshot.pull_requests)
        self.assertEqual(6, snapshot.projects)
        self.assertEqual(17739, snapshot.commits)
        self.assertEqual(29, snapshot.branches)
        self.assertEqual(47, snapshot.releases)
        self.assertEqual(("MIT",), tuple(snapshot.licenses))
        languages = dict(snapshot.languages)
        self.assertAlmostEqual(4, len(languages))
        self.assertAlmostEqual(0.429, languages["JavaScript"])
        self.assertAlmostEqual(0.427, languages["CSS"])
        self.assertAlmostEqual(0.138, languages["HTML"])
        self.assertAlmostEqual(0.006, languages["Other"])

    def test_from_html_git(self):
        repository = GitHubRepository(REPOSITORY_URL_GIT)
        with HTML_DOCUMENT_GIT.open("rt", encoding="utf8") as f:
            snapshot = Snapshot.from_html(repository, SNAPSHOT_DATE, f)
        self.assertEqual(repository, snapshot.repository)
        self.assertEqual("git", snapshot.owner)
        self.assertEqual("git", snapshot.title)
        self.assertEqual(SNAPSHOT_DATE, snapshot.date)
        self.assertEqual(1941, snapshot.watching)
        self.assertEqual(23093, snapshot.stars)
        self.assertEqual(13391, snapshot.forks)
        self.assertEqual(0, snapshot.issues)
        self.assertEqual(143, snapshot.pull_requests)
        self.assertEqual(0, snapshot.projects)
        self.assertEqual(51934, snapshot.commits)
        self.assertEqual(5, snapshot.branches)
        self.assertEqual(693, snapshot.releases)
        self.assertFalse(snapshot.licenses)
        languages = dict(snapshot.languages)
        self.assertAlmostEqual(7, len(languages))
        self.assertAlmostEqual(0.475, languages["C"])
        self.assertAlmostEqual(0.356, languages["Shell"])
        self.assertAlmostEqual(0.074, languages["Perl"])
        self.assertAlmostEqual(0.051, languages["Tcl"])
        self.assertAlmostEqual(0.022, languages["Python"])
        self.assertAlmostEqual(0.009, languages["Makefile"])
        self.assertAlmostEqual(0.013, languages["Other"])

    def test_add(self):
        first_repository = GitHubRepository(REPOSITORY_URL_BOOTSTRAP)
        with HTML_DOCUMENT_BOOTSTRAP.open("rt", encoding="utf8") as f:
            first_snapshot = Snapshot.from_html(first_repository, SNAPSHOT_DATE, f)
        second_repository = GitHubRepository(REPOSITORY_URL_GIT)
        with HTML_DOCUMENT_GIT.open("rt", encoding="utf8") as f:
            second_snapshot = Snapshot.from_html(second_repository, SNAPSHOT_DATE, f)
        snapshot = first_snapshot + second_snapshot
        self.assertEqual(None, snapshot.repository)
        self.assertEqual(None, snapshot.owner)
        self.assertEqual(None, snapshot.title)
        self.assertEqual(SNAPSHOT_DATE, snapshot.date)
        self.assertEqual(7356 + 1941, snapshot.watching)
        self.assertEqual(125696 + 23093, snapshot.stars)
        self.assertEqual(60569 + 13391, snapshot.forks)
        self.assertEqual(400 + 0, snapshot.issues)
        self.assertEqual(123 + 143, snapshot.pull_requests)
        self.assertEqual(6 + 0, snapshot.projects)
        self.assertEqual(17739 + 51934, snapshot.commits)
        self.assertEqual(29 + 5, snapshot.branches)
        self.assertEqual(47 + 693, snapshot.releases)
        self.assertEqual(("MIT",), tuple(snapshot.licenses))
        languages = dict(snapshot.languages)
        self.assertAlmostEqual(10, len(languages))
        self.assertAlmostEqual((0.475 + 0) / 2, languages["C"])
        self.assertAlmostEqual((0.356 + 0) / 2, languages["Shell"])
        self.assertAlmostEqual((0.074 + 0) / 2, languages["Perl"])
        self.assertAlmostEqual((0.051 + 0) / 2, languages["Tcl"])
        self.assertAlmostEqual((0.022 + 0) / 2, languages["Python"])
        self.assertAlmostEqual((0.009 + 0) / 2, languages["Makefile"])
        self.assertAlmostEqual((0 + 0.429) / 2, languages["JavaScript"])
        self.assertAlmostEqual((0 + 0.427) / 2, languages["CSS"])
        self.assertAlmostEqual((0 + 0.138) / 2, languages["HTML"])
        self.assertAlmostEqual((0.013 + 0.006) / 2, languages["Other"])


class TestLanguage(unittest.TestCase):
    def setUp(self):
        self.first_repository = GitHubRepository(REPOSITORY_URL_BOOTSTRAP)
        with HTML_DOCUMENT_BOOTSTRAP.open("rt", encoding="utf8") as f:
            self.first_snapshot = Snapshot.from_html(self.first_repository, SNAPSHOT_DATE, f)
        self.second_repository = GitHubRepository(REPOSITORY_URL_GIT)
        with HTML_DOCUMENT_GIT.open("rt", encoding="utf8") as f:
            self.second_snapshot = Snapshot.from_html(self.second_repository, SNAPSHOT_DATE, f)

    def test_iter(self):
        python = Language("python", [self.first_repository, self.second_repository])
        self.assertEqual("python", python.getName())

        projections = list(python)
        self.assertEqual(1, len(projections))

        projection = projections[0]
        self.assertAlmostEqual(0, projection.__dict__[self.first_repository])
        self.assertAlmostEqual(0.022, projection.__dict__[self.second_repository])

    def test_add(self):
        python = Language("python", [self.first_repository, self.second_repository])
        other = Language("other", [self.first_repository, self.second_repository])

        projections = list(python + other)
        self.assertEqual(1, len(projections))

        projection = projections[0]
        self.assertAlmostEqual(0 + 0.006, projection.__dict__[self.first_repository])
        self.assertAlmostEqual(0.022 + 0.013, projection.__dict__[self.second_repository])


if __name__ == '__main__':
    unittest.main()
