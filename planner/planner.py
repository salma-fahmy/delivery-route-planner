"""The trip planning algorithm.

Strategy (three passes, all greedy and deterministic):

1. Quarantine  - any package heavier than the vehicle capacity can never be
                 loaded without breaking the hard capacity rule, so it is set
                 aside as "unassignable" and reported instead of being dropped
                 silently or forced into a trip.

2. Pack by area - deliveries are grouped by area. Inside an area they are
                 sorted by (priority, heaviest first, id) and packed with
                 First Fit. This is "priority-aware First Fit", NOT classic
                 First Fit Decreasing (FFD): FFD sorts by weight only, and its
                 well-known approximation bound relies on that. Here priority
                 is the primary key and weight is only a tie-breaker, so that
                 bound does not carry over - this is a plain greedy heuristic
                 with no optimality guarantee.

3. Consolidate - after step 2 each area may leave one half empty trip behind.
                 Those partial trips ARE sorted heaviest-first and merged with
                 First Fit, which is classic FFD applied to whole trips (no
                 priority involved at this stage), whenever two of them fit in
                 one vehicle. This keeps "same area together" as the default
                 while still avoiding sending out nearly empty vans.
                 Area grouping is a preference, not a hard constraint: only
                 the 10 kg capacity is enforced absolutely; area cohesion is
                 optimised for and yields to capacity utilisation here.

Finally trips are ordered by urgency so the dispatcher runs the most urgent
trip first.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

from .models import EPSILON, Delivery, Trip

DEFAULT_CAPACITY = 10.0


@dataclass
class PlanResult:
    trips: List[Trip] = field(default_factory=list)
    unassignable: List[Delivery] = field(default_factory=list)
    capacity: float = DEFAULT_CAPACITY

    @property
    def planned_count(self) -> int:
        return sum(len(trip.deliveries) for trip in self.trips)

    @property
    def total_weight(self) -> float:
        return round(sum(trip.total_weight for trip in self.trips), 6)

    @property
    def average_utilisation(self) -> float:
        if not self.trips:
            return 0.0
        return sum(t.utilisation(self.capacity) for t in self.trips) / len(self.trips)

    @property
    def wasted_capacity(self) -> float:
        return round(len(self.trips) * self.capacity - self.total_weight, 6)

    @property
    def split_area_trips(self) -> int:
        return sum(1 for t in self.trips if not t.is_single_area)


def plan_trips(deliveries: List[Delivery],
               capacity: float = DEFAULT_CAPACITY,
               consolidate: bool = True) -> PlanResult:
    """Group deliveries into trips. Never exceeds `capacity` on any trip."""
    if capacity <= 0:
        raise ValueError("capacity must be greater than 0")

    result = PlanResult(capacity=capacity)
    if not deliveries:                                  # edge case: empty input
        return result

    # --- pass 1: quarantine oversized packages -------------------------------
    packable: List[Delivery] = []
    for delivery in deliveries:
        if delivery.weight > capacity + EPSILON:
            result.unassignable.append(delivery)
        else:
            packable.append(delivery)

    # --- pass 2: pack each area on its own ------------------------------------
    by_area: Dict[str, List[Delivery]] = defaultdict(list)
    for delivery in packable:
        by_area[delivery.area].append(delivery)

    # Areas that contain the most urgent delivery are packed first; heavier
    # areas win the tie so the big loads claim whole vehicles early.
    area_order = sorted(
        by_area,
        key=lambda area: (min(d.priority for d in by_area[area]),
                          -sum(d.weight for d in by_area[area]),
                          area),
    )

    trips: List[Trip] = []
    for area in area_order:
        # Priority-aware First Fit: priority is the primary sort key (urgency
        # comes first, per the requirements), weight-descending is only the
        # tie-breaker for equal priorities. This is deliberately NOT classic
        # FFD - see module docstring for why that distinction matters.
        items = sorted(by_area[area], key=lambda d: (d.priority, -d.weight, d.id))
        area_trips: List[Trip] = []
        for delivery in items:
            target = next((t for t in area_trips if t.fits(delivery, capacity)), None)
            if target is None:
                target = Trip()
                area_trips.append(target)
            target.add(delivery)
        trips.extend(area_trips)

    # --- pass 3: merge leftover partial trips ---------------------------------
    if consolidate:
        trips = _consolidate(trips, capacity)

    trips.sort(key=lambda t: (t.top_priority, -t.total_weight, t.areas[0]))
    for number, trip in enumerate(trips, start=1):
        trip.id = number

    result.trips = trips
    return result


def _consolidate(trips: List[Trip], capacity: float) -> List[Trip]:
    """Classic First Fit Decreasing over the half-empty trips left by pass 2.

    Trips are sorted heaviest-first (no priority involved here - priority was
    already respected when trips were formed) and each partial trip is merged
    into the first already-merged trip it fits into, else it starts a new
    merged trip. This is a genuine FFD application, unlike the area sort in
    plan_trips().
    """
    full = [t for t in trips if t.total_weight >= capacity - EPSILON]
    partial = sorted(
        (t for t in trips if t.total_weight < capacity - EPSILON),
        key=lambda t: (-t.total_weight, t.top_priority),
    )

    merged: List[Trip] = []
    for trip in partial:
        host = next(
            (m for m in merged if m.total_weight + trip.total_weight <= capacity + EPSILON),
            None,
        )
        if host is None:
            merged.append(trip)
        else:
            host.absorb(trip)

    return full + merged
