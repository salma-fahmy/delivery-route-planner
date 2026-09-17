"""Reads delivery requests from a CSV or JSON file and validates every row.

Input format (CSV, with header row):

    id,area,priority,weight
    1,Nasr City,2,4.5

The same fields are expected in JSON, as a list of objects.

Validation never raises on a single bad row: the row is collected into a
`RejectedDelivery` list so the program can still plan the healthy rows and
report the bad ones at the end.
"""

import csv
import json
import os
from typing import List, Tuple

from .models import Delivery, RejectedDelivery

REQUIRED_FIELDS = ("id", "area", "priority", "weight")


def load_deliveries(path: str) -> Tuple[List[Delivery], List[RejectedDelivery]]:
    """Return (valid deliveries, rejected rows)."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Input file not found: {path}")

    extension = os.path.splitext(path)[1].lower()
    rows = _read_json(path) if extension == ".json" else _read_csv(path)
    return _validate(rows)


def _read_csv(path: str) -> List[dict]:
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:          # completely empty file
            return []
        reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
        return [row for row in reader if any((value or "").strip() for value in row.values())]


def _read_json(path: str) -> List[dict]:
    with open(path, encoding="utf-8-sig") as handle:
        content = handle.read().strip()
    if not content:
        return []
    data = json.loads(content)
    if isinstance(data, dict):                 # allow {"deliveries": [...]}
        data = data.get("deliveries", [])
    return [{str(k).strip().lower(): v for k, v in row.items()} for row in data]


def _validate(rows: List[dict]) -> Tuple[List[Delivery], List[RejectedDelivery]]:
    deliveries: List[Delivery] = []
    rejected: List[RejectedDelivery] = []
    seen_ids = set()

    for row in rows:
        missing = [f for f in REQUIRED_FIELDS if str(row.get(f, "")).strip() == ""]
        if missing:
            rejected.append(RejectedDelivery(row, f"missing field(s): {', '.join(missing)}"))
            continue

        delivery_id = str(row["id"]).strip()
        area = str(row["area"]).strip()

        try:
            priority = int(str(row["priority"]).strip())
        except ValueError:
            rejected.append(RejectedDelivery(row, f"priority is not an integer: {row['priority']!r}"))
            continue

        try:
            weight = float(str(row["weight"]).strip())
        except ValueError:
            rejected.append(RejectedDelivery(row, f"weight is not a number: {row['weight']!r}"))
            continue

        if priority < 1:
            rejected.append(RejectedDelivery(row, f"priority must be >= 1 (got {priority})"))
            continue
        if weight <= 0:
            rejected.append(RejectedDelivery(row, f"weight must be greater than 0 (got {weight:g})"))
            continue
        if delivery_id in seen_ids:
            rejected.append(RejectedDelivery(row, f"duplicate delivery id: {delivery_id}"))
            continue

        seen_ids.add(delivery_id)
        deliveries.append(Delivery(id=delivery_id, area=area, priority=priority, weight=weight))

    return deliveries, rejected
