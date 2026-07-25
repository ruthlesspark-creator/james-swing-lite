from __future__ import annotations

import sys

from .domain import HealthState


RESEARCH_PREFIXES = ("james_swing.external", "research")
LEGACY_PREFIXES = ("james.",)


class HealthMonitor:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def state(self, order_count: int) -> HealthState:
        loaded = set(sys.modules)
        legacy_loaded = any(name.startswith(LEGACY_PREFIXES) for name in loaded)
        research_loaded = any(name.startswith(RESEARCH_PREFIXES) for name in loaded)
        return HealthState(
            status="정상" if not self.errors else "주의",
            live_blocked=True,
            private_orders_blocked=True,
            legacy_loaded=legacy_loaded,
            research_loaded=research_loaded,
            order_count=order_count,
            errors=list(self.errors),
        )
