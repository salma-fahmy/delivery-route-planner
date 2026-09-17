"""Printing and exporting a plan."""

from typing import List

from .models import Delivery, RejectedDelivery
from .planner import PlanResult, plan_trips

LINE = "-" * 62


def format_plan(result: PlanResult, rejected: List[RejectedDelivery] = None) -> str:
    rejected = rejected or []
    out: List[str] = []
    out.append(LINE)
    out.append(f"DELIVERY PLAN  (vehicle capacity: {result.capacity:g} kg)")
    out.append(LINE)

    if not result.trips:
        out.append("No trips were planned.")
    for trip in result.trips:
        out.append(
            f"Trip {trip.id:>3} | {', '.join(trip.areas):<28} "
            f"| {trip.total_weight:>5.2f}/{result.capacity:g} kg "
            f"({trip.utilisation(result.capacity):3.0f}%)"
        )
        for delivery in sorted(trip.deliveries, key=lambda d: (d.priority, d.area, d.id)):
            out.append(
                f"        - #{delivery.id:<4} {delivery.area:<18} "
                f"priority {delivery.priority:<3} {delivery.weight:>5.2f} kg"
            )
        out.append("")

    if result.unassignable:
        out.append("UNASSIGNABLE (heavier than one vehicle - needs a special/split shipment)")
        for delivery in result.unassignable:
            out.append(f"        - #{delivery.id:<4} {delivery.area:<18} {delivery.weight:>5.2f} kg")
        out.append("")

    if rejected:
        out.append("INVALID ROWS (skipped)")
        for item in rejected:
            out.append(f"        - {item.raw} -> {item.reason}")
        out.append("")

    out.append(LINE)
    out.append("SUMMARY")
    out.append(LINE)
    out.append(f"Deliveries planned      : {result.planned_count}")
    out.append(f"Unassignable deliveries : {len(result.unassignable)}")
    out.append(f"Invalid rows            : {len(rejected)}")
    out.append(f"Trips required          : {len(result.trips)}")
    out.append(f"Total weight            : {result.total_weight:g} kg")
    out.append(f"Average utilisation     : {result.average_utilisation:.1f}%")
    out.append(f"Wasted capacity         : {result.wasted_capacity:g} kg")
    out.append(f"Trips covering >1 area  : {result.split_area_trips}")
    return "\n".join(out)


def plan_to_dict(result: PlanResult, rejected: List[RejectedDelivery] = None) -> dict:
    rejected = rejected or []
    return {
        "capacity_kg": result.capacity,
        "trips": [
            {
                "trip_id": trip.id,
                "areas": trip.areas,
                "total_weight_kg": trip.total_weight,
                "utilisation_percent": round(trip.utilisation(result.capacity), 1),
                "deliveries": [
                    {"id": d.id, "area": d.area, "priority": d.priority, "weight_kg": d.weight}
                    for d in sorted(trip.deliveries, key=lambda d: (d.priority, d.id))
                ],
            }
            for trip in result.trips
        ],
        "unassignable": [
            {"id": d.id, "area": d.area, "priority": d.priority, "weight_kg": d.weight,
             "reason": "package weight exceeds vehicle capacity"}
            for d in result.unassignable
        ],
        "invalid_rows": [{"row": r.raw, "reason": r.reason} for r in rejected],
        "summary": {
            "deliveries_planned": result.planned_count,
            "trips_required": len(result.trips),
            "total_weight_kg": result.total_weight,
            "average_utilisation_percent": round(result.average_utilisation, 1),
            "wasted_capacity_kg": result.wasted_capacity,
        },
    }


def format_fleet_simulation(deliveries: List[Delivery], capacities: List[float]) -> str:
    """Extra feature: compare how many trips each vehicle size would need."""
    out = [LINE, "FLEET WHAT-IF SIMULATION", LINE,
           f"{'Capacity':>10} | {'Trips':>6} | {'Avg util.':>10} | {'Wasted':>9} | {'Undeliverable':>13}",
           f"{'-'*10}-+-{'-'*6}-+-{'-'*10}-+-{'-'*9}-+-{'-'*13}"]
    for capacity in capacities:
        result = plan_trips(deliveries, capacity=capacity)
        out.append(
            f"{capacity:>8.1f}kg | {len(result.trips):>6} | "
            f"{result.average_utilisation:>9.1f}% | {result.wasted_capacity:>7.2f}kg | "
            f"{len(result.unassignable):>13}"
        )
    out.append("")
    out.append("Fewer trips means fewer driver hours; higher utilisation means the")
    out.append("vehicle is not driving around half empty. Pick the smallest capacity")
    out.append("that keeps the trip count acceptable and leaves nothing undeliverable.")
    return "\n".join(out)
