"""Unit tests. Run with:  python -m unittest discover -s tests -t .  """

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planner.loader import load_deliveries              # noqa: E402
from planner.models import Delivery                     # noqa: E402
from planner.planner import plan_trips                  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def make(id_, area, priority, weight):
    return Delivery(id=str(id_), area=area, priority=priority, weight=weight)


class TestPlanner(unittest.TestCase):

    def test_empty_input_produces_no_trips(self):
        result = plan_trips([])
        self.assertEqual(result.trips, [])
        self.assertEqual(result.unassignable, [])

    def test_no_trip_exceeds_capacity(self):
        deliveries = [make(i, "Maadi", 1, 3.3) for i in range(1, 10)]
        result = plan_trips(deliveries, capacity=10)
        for trip in result.trips:
            self.assertLessEqual(trip.total_weight, 10 + 1e-9)

    def test_every_delivery_appears_exactly_once(self):
        deliveries, _ = load_deliveries(os.path.join(DATA, "edge_cases.csv"))
        result = plan_trips(deliveries)
        planned = [d.id for trip in result.trips for d in trip.deliveries]
        planned += [d.id for d in result.unassignable]
        self.assertEqual(sorted(planned), sorted(d.id for d in deliveries))
        self.assertEqual(len(planned), len(set(planned)))

    def test_oversized_package_is_quarantined_not_dropped(self):
        deliveries = [make(1, "Maadi", 1, 12.5), make(2, "Maadi", 1, 2.0)]
        result = plan_trips(deliveries, capacity=10)
        self.assertEqual([d.id for d in result.unassignable], ["1"])
        self.assertEqual(len(result.trips), 1)

    def test_same_area_is_grouped_when_it_fits(self):
        deliveries = [make(1, "Maadi", 1, 2.0), make(2, "Maadi", 2, 3.5),
                      make(3, "Nasr City", 1, 4.0)]
        result = plan_trips(deliveries, capacity=10, consolidate=False)
        maadi = [t for t in result.trips if "Maadi" in t.areas]
        self.assertEqual(len(maadi), 1)
        self.assertEqual(len(maadi[0].deliveries), 2)

    def test_urgent_trip_comes_first(self):
        deliveries = [make(1, "Maadi", 5, 4.0), make(2, "Nasr City", 1, 4.0)]
        result = plan_trips(deliveries, capacity=10, consolidate=False)
        self.assertEqual(result.trips[0].top_priority, 1)

    def test_consolidation_reduces_trip_count(self):
        deliveries = [make(1, "Maadi", 1, 4.0), make(2, "Nasr City", 1, 4.0)]
        without = plan_trips(deliveries, capacity=10, consolidate=False)
        with_merge = plan_trips(deliveries, capacity=10, consolidate=True)
        self.assertEqual(len(without.trips), 2)
        self.assertEqual(len(with_merge.trips), 1)

    def test_equal_priority_is_deterministic(self):
        deliveries = [make(1, "Maadi", 2, 3.0), make(2, "Maadi", 2, 3.0),
                      make(3, "Maadi", 2, 6.0)]
        first = plan_trips(list(deliveries))
        second = plan_trips(list(reversed(deliveries)))
        self.assertEqual(
            [sorted(d.id for d in t.deliveries) for t in first.trips],
            [sorted(d.id for d in t.deliveries) for t in second.trips],
        )


class TestLoader(unittest.TestCase):

    def test_invalid_rows_are_rejected_with_a_reason(self):
        deliveries, rejected = load_deliveries(os.path.join(DATA, "edge_cases.csv"))
        self.assertEqual(len(deliveries), 11)
        self.assertEqual(len(rejected), 4)
        self.assertTrue(all(item.reason for item in rejected))

    def test_csv_and_json_give_the_same_result(self):
        csv_deliveries, _ = load_deliveries(os.path.join(DATA, "sample_deliveries.csv"))
        json_deliveries, _ = load_deliveries(os.path.join(DATA, "sample_deliveries.json"))
        self.assertEqual(csv_deliveries, json_deliveries)

    def test_file_with_only_a_header_is_empty(self):
        deliveries, rejected = load_deliveries(os.path.join(DATA, "empty.csv"))
        self.assertEqual(deliveries, [])
        self.assertEqual(rejected, [])


if __name__ == "__main__":
    unittest.main()
