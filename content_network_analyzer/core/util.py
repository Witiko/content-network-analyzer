"""
Defines utility functions.
"""

from logging import getLogger
import re


LOGGER = getLogger(__name__)


def fraction(numerator, denominator, bottom=0.0):
    """Computes a fraction.

    Parameters
    ----------
    numerator : int
        The numerator.
    denominator : int
        The denominator.
    bottom : float, optional
        The value of the fraction if the denominator is zero.

    Returns
    -------
    float
        The value of the fraction.
    """
    assert isinstance(numerator, int)
    assert isinstance(denominator, int)
    assert isinstance(bottom, float)

    if denominator == 0:
        value = bottom
    else:
        value = 1.0 * numerator / denominator
    assert isinstance(value, float)

    return value


def parse_int(text):
    """Returns the first integer in a string, disregarding any whitespaces.

    Parameters
    ----------
    text : str
        A string.

    Returns
    -------
    int
        The first integer in the string.
    """
    assert isinstance(text, str)

    match = re.match(r"[^\d]*([\d\s]+)", text)
    assert match, "Can't parse \"%s\" as an integer" % text

    return int(re.sub(r"\s*", "", match.group(1)))
