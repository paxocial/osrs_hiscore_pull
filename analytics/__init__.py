"""OSRS Analytics Package.

This package provides comprehensive analytics calculations for OSRS hiscore data.
Transforms raw snapshot data into meaningful insights about progress, rates, and trends.
"""

from .engine import AnalyticsEngine, XPRate, SkillProgression, Milestone, ProgressDelta, ActivityTrend

__version__ = "1.0.0"
__all__ = [
    "AnalyticsEngine",
    "XPRate",
    "SkillProgression",
    "Milestone",
    "ProgressDelta",
    "ActivityTrend"
]