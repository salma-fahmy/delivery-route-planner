"""Core data structures used by the planner.

Kept deliberately small: one immutable record for an incoming delivery
request, and one mutable container for a vehicle trip.
"""

from dataclasses import dataclass, field
from typing import List

# Floating point weights (4.5 + 3.5 + 2.0) can end up as 10.000000000000002,
# so every capacity comparison uses a tiny tolerance.
EPSILON = 1e-9


@dataclass(frozen=True)
class Delivery:
    """A single delivery request read from the input file."""

    id: str
    area: str
    priority: int          # lower number == more urgent
    weight: float          # kilograms

    def __str__(self) -> str:
        return f"#{self.id} {self.area} (p{self.priority}, {self.weight:g} kg)"


@dataclass
class RejectedDelivery:
    """A row we refused to plan, plus the reason why."""

    raw: dict
    reason: str


@dataclass
class Trip:
    """One vehicle run. Never allowed to exceed the vehicle capacity."""

    id: int = 0
    deliveries: List[Delivery] = field(default_factory=list)
    _weight: float = 0.0

    def add(self, delivery: Delivery) -> None:
        self.deliveries.append(delivery)
        self._weight += delivery.weight

    def absorb(self, other: "Trip") -> None:
        for delivery in other.deliveries:
            self.add(delivery)

    @property
    def total_weight(self) -> float:
        return round(self._weight, 6)

    def fits(self, delivery: Delivery, capacity: float) -> bool:
        return self._weight + delivery.weight <= capacity + EPSILON

    def remaining(self, capacity: float) -> float:
        return round(capacity - self._weight, 6)

    def utilisation(self, capacity: float) -> float:
        return (self._weight / capacity * 100.0) if capacity else 0.0

    @property
    def areas(self) -> List[str]:
        """Areas served by this trip, ordered by how much weight each one has."""
        seen = {}
        for d in self.deliveries:
            seen[d.area] = seen.get(d.area, 0.0) + d.weight
        return sorted(seen, key=lambda a: (-seen[a], a))

    @property
    def top_priority(self) -> int:
        return min((d.priority for d in self.deliveries), default=10**9)

    @property
    def is_single_area(self) -> bool:
        return len(self.areas) == 1
