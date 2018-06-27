"""
Provides datatypes, and methods for analyzing, and visualizing data collected from content networks.
"""

from .core import NamedCluster  # noqa:F401
from .models import SoundCloudTrack, YouTubeTrack, WattPadBook, WattPadPage  # noqa:F401
from .views import MatPlotLibView  # noqa:F401


__author__ = "Vit Novotny"
__version__ = "0.1.0"
__license__ = "MIT"
