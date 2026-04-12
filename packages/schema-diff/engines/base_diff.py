"""Abstract base differ — all engine differs must inherit from this."""

import os
import sys
from abc import ABC, abstractmethod

# Allow importing from the schema-diff package root
_pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from models import DiffResult  # noqa: E402  (resolved via sys.path above)


class BaseDiff(ABC):
    """Abstract base class for all schema diff engines.

    Each engine implements diff() with its own comparison logic but returns
    a standardised list of DiffResult objects so downstream consumers
    (Zero, alert dispatcher, impact analyzer) don't need engine-specific code.
    """

    @abstractmethod
    def diff(self, before: dict, after: dict) -> list[DiffResult]:
        """Compare two schema snapshots and return detected changes.

        Parameters
        ----------
        before:
            The schema snapshot captured before the change event.
        after:
            The schema snapshot captured after the change event.

        Returns
        -------
        list[DiffResult]
            One DiffResult per detected change. Empty list if no changes.
        """
