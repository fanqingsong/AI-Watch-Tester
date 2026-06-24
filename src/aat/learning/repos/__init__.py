"""Single-concern repositories backing :class:`~aat.learning.store.LearnedStore`.

Each repository owns the DDL and CRUD for exactly one SQL table and operates
against the shared ``sqlite3.Connection`` handed to it by the facade. The
repositories do not import one another; they are composed by ``LearnedStore``.
"""

from __future__ import annotations

from aat.learning.repos.element_repo import ElementRepo
from aat.learning.repos.failure_repo import FailureRepo
from aat.learning.repos.match_history_repo import MatchHistoryRepo
from aat.learning.repos.platform_repo import PlatformRepo
from aat.learning.repos.state_coords_repo import StateCoordsRepo
from aat.learning.repos.strategy_repo import StrategyRepo

__all__ = [
    "ElementRepo",
    "FailureRepo",
    "MatchHistoryRepo",
    "PlatformRepo",
    "StateCoordsRepo",
    "StrategyRepo",
]
