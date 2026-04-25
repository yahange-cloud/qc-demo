"""
Inspection Scheduling Engine.
Implements multi-factor priority scoring, inspector assignment, and conflict detection.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config import SCHEDULING_WEIGHTS, CUSTOMER_LEVEL_SCORES


def calculate_priority_score(requests_df, personnel_df, reference_date=None):
    """Calculate priority score for each pending/schedulable request.

    Score = W1 * urgency + W2 * risk + W3 * customer_level + W4 * capacity

    Args:
        requests_df: Inspection requests DataFrame.
        personnel_df: Factory personnel DataFrame.
        reference_date: Date to calculate urgency from. Defaults to today.

    Returns:
        DataFrame with added 'priority_score' and component columns.
    """
    if reference_date is None:
        reference_date = pd.Timestamp.now().normalize()
    else:
        reference_date = pd.Timestamp(reference_date)

    df = requests_df.copy()
    W = SCHEDULING_WEIGHTS

    # Get factory quality ratings
    factory_quality = personnel_df.drop_duplicates("factory_id").set_index("factory_id")["quality_rating"]

    # 1. Urgency: 1 / days_until_deadline (capped)
    days_remaining = (df["shipment_deadline"] - reference_date).dt.days.clip(lower=1)
    df["urgency_score"] = (1.0 / days_remaining).clip(upper=1.0)

    # 2. Risk: 1 - (quality_rating / 100)
    df["risk_score"] = df["factory_id"].map(
        lambda fid: 1.0 - factory_quality.get(fid, 80) / 100.0
    )

    # 3. Customer level score
    df["customer_score"] = df["customer_level"].map(CUSTOMER_LEVEL_SCORES).fillna(0.3)

    # 4. Capacity: computed per-region per-date during assignment
    # Use a placeholder here (will be refined during assignment)
    df["capacity_score"] = 0.5

    # Weighted total
    df["priority_score"] = (
        W["urgency"] * df["urgency_score"]
        + W["risk"] * df["risk_score"]
        + W["customer"] * df["customer_score"]
        + W["capacity"] * df["capacity_score"]
    )

    # Normalize to 0-100
    score_min = df["priority_score"].min()
    score_max = df["priority_score"].max()
    if score_max > score_min:
        df["priority_score"] = ((df["priority_score"] - score_min) / (score_max - score_min) * 100).round(1)
    else:
        df["priority_score"] = 50.0

    return df.sort_values("priority_score", ascending=False)


def check_inspector_availability(inspector_id, date, current_assignments, personnel_df):
    """Check if an inspector is available on a given date.

    Args:
        inspector_id: Inspector ID to check.
        date: Date to check availability.
        current_assignments: List of dicts with 'inspector_id' and 'scheduled_date'.
        personnel_df: Personnel DataFrame.

    Returns:
        bool: True if available.
    """
    inspector_info = personnel_df[personnel_df["inspector_id"] == inspector_id].iloc[0]
    max_per_day = inspector_info["max_inspections_per_day"]
    available_days_str = inspector_info["available_days"]

    # Check day of week
    date_ts = pd.Timestamp(date)
    day_name = date_ts.day_name()[:3]
    available_map = {
        "Mon-Fri": ["Mon", "Tue", "Wed", "Thu", "Fri"],
        "Mon-Sat": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        "Mon-Sun": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    }
    allowed_days = available_map.get(available_days_str, ["Mon", "Tue", "Wed", "Thu", "Fri"])
    if day_name not in allowed_days:
        return False

    # Check daily capacity
    daily_count = sum(
        1 for a in current_assignments
        if a["inspector_id"] == inspector_id
        and pd.Timestamp(a["scheduled_date"]).date() == date_ts.date()
    )
    return daily_count < max_per_day


def get_region_inspectors(factory_id, personnel_df):
    """Get list of inspectors available for a factory's region."""
    factory_rows = personnel_df[personnel_df["factory_id"] == factory_id]
    if factory_rows.empty:
        return []
    return factory_rows["inspector_id"].unique().tolist()


def assign_inspector(request, personnel_df, current_assignments, date_range_days=5):
    """Assign the best available inspector for a request.

    Tries to assign within date_range_days of the requested date.
    Uses load balancing to distribute work evenly.

    Args:
        request: Series with request data.
        personnel_df: Personnel DataFrame.
        current_assignments: List of existing assignments.
        date_range_days: Days after requested_date to search for availability.

    Returns:
        dict with 'inspector_id', 'scheduled_date', or None if no slot found.
    """
    factory_id = request["factory_id"]
    requested_date = pd.Timestamp(request["requested_date"])
    deadline = pd.Timestamp(request["shipment_deadline"])

    inspectors = get_region_inspectors(factory_id, personnel_df)
    if not inspectors:
        return None

    # Try each date from requested_date up to deadline (max date_range_days)
    max_date = min(requested_date + timedelta(days=date_range_days), deadline - timedelta(days=1))

    best_option = None
    min_load = float("inf")

    current_date = requested_date
    while current_date <= max_date:
        for ins_id in inspectors:
            if check_inspector_availability(ins_id, current_date, current_assignments, personnel_df):
                # Calculate load for this inspector on nearby dates
                load = sum(
                    1 for a in current_assignments
                    if a["inspector_id"] == ins_id
                    and abs((pd.Timestamp(a["scheduled_date"]) - current_date).days) <= 3
                )
                if load < min_load:
                    min_load = load
                    best_option = {
                        "inspector_id": ins_id,
                        "scheduled_date": current_date,
                    }
        current_date += timedelta(days=1)

    return best_option


def generate_schedule(requests_df, personnel_df, reference_date=None):
    """Generate full inspection schedule.

    1. Score all pending/scheduled requests.
    2. Sort by priority score (descending).
    3. Assign inspectors greedily.

    Args:
        requests_df: Inspection requests DataFrame.
        personnel_df: Personnel DataFrame.
        reference_date: Reference date for scoring.

    Returns:
        DataFrame with schedule assignments.
    """
    if reference_date is None:
        reference_date = pd.Timestamp.now().normalize()

    # Filter schedulable requests
    schedulable = requests_df[requests_df["status"].isin(["Pending", "Scheduled"])].copy()
    if schedulable.empty:
        return pd.DataFrame()

    # Calculate priority scores
    scored = calculate_priority_score(schedulable, personnel_df, reference_date)

    # Assign inspectors
    assignments = []
    current_assignments = []

    for _, req in scored.iterrows():
        result = assign_inspector(req, personnel_df, current_assignments)
        if result:
            inspector_info = personnel_df[
                personnel_df["inspector_id"] == result["inspector_id"]
            ].iloc[0]

            assignment = {
                "request_id": req["request_id"],
                "factory_id": req["factory_id"],
                "factory_name": req["factory_name"],
                "product_line": req["product_line"],
                "sku": req["sku"],
                "order_qty": req["order_qty"],
                "customer_level": req["customer_level"],
                "priority": req["priority"],
                "priority_score": req["priority_score"],
                "requested_date": req["requested_date"],
                "shipment_deadline": req["shipment_deadline"],
                "region": req["region"],
                "inspector_id": result["inspector_id"],
                "inspector_name": inspector_info["inspector_name"],
                "scheduled_date": result["scheduled_date"],
            }
            assignments.append(assignment)
            current_assignments.append({
                "inspector_id": result["inspector_id"],
                "scheduled_date": result["scheduled_date"],
            })
        else:
            # Unassigned - no available inspector slot
            assignments.append({
                "request_id": req["request_id"],
                "factory_id": req["factory_id"],
                "factory_name": req["factory_name"],
                "product_line": req["product_line"],
                "sku": req["sku"],
                "order_qty": req["order_qty"],
                "customer_level": req["customer_level"],
                "priority": req["priority"],
                "priority_score": req["priority_score"],
                "requested_date": req["requested_date"],
                "shipment_deadline": req["shipment_deadline"],
                "region": req["region"],
                "inspector_id": None,
                "inspector_name": "Unassigned",
                "scheduled_date": None,
            })

    schedule_df = pd.DataFrame(assignments)
    if not schedule_df.empty and "scheduled_date" in schedule_df.columns:
        schedule_df["scheduled_date"] = pd.to_datetime(schedule_df["scheduled_date"])

    return schedule_df


def detect_conflicts(schedule_df, personnel_df):
    """Detect scheduling conflicts.

    Checks for:
    1. Same inspector assigned to multiple factories on the same day
       in different regions/cities.
    2. Inspector exceeding daily capacity.

    Args:
        schedule_df: Schedule DataFrame from generate_schedule().
        personnel_df: Personnel DataFrame.

    Returns:
        List of conflict dicts with details.
    """
    conflicts = []
    assigned = schedule_df.dropna(subset=["inspector_id", "scheduled_date"])

    if assigned.empty:
        return conflicts

    # Get factory city info
    factory_info = personnel_df.drop_duplicates("factory_id").set_index("factory_id")[["city", "region"]]

    # Group by inspector + date
    for (ins_id, date), group in assigned.groupby(["inspector_id", "scheduled_date"]):
        # Check capacity
        inspector_row = personnel_df[personnel_df["inspector_id"] == ins_id].iloc[0]
        max_per_day = inspector_row["max_inspections_per_day"]

        if len(group) > max_per_day:
            conflicts.append({
                "type": "over_capacity",
                "inspector_id": ins_id,
                "inspector_name": inspector_row["inspector_name"],
                "date": date,
                "count": len(group),
                "max": max_per_day,
                "factories": group["factory_name"].tolist(),
                "description": f"{inspector_row['inspector_name']} has {len(group)} inspections on {date.strftime('%Y-%m-%d')} (max: {max_per_day})",
            })

        # Check cross-city on same day
        if len(group) > 1:
            cities = set()
            for _, row in group.iterrows():
                fid = row["factory_id"]
                if fid in factory_info.index:
                    cities.add(factory_info.loc[fid, "city"])
            if len(cities) > 1:
                conflicts.append({
                    "type": "cross_city",
                    "inspector_id": ins_id,
                    "inspector_name": inspector_row["inspector_name"],
                    "date": date,
                    "cities": list(cities),
                    "factories": group["factory_name"].tolist(),
                    "description": f"{inspector_row['inspector_name']} assigned to multiple cities ({', '.join(cities)}) on {date.strftime('%Y-%m-%d')}",
                })

    return conflicts


def get_inspector_workload(schedule_df):
    """Calculate inspector workload summary for heatmap.

    Returns:
        DataFrame with inspector_id, inspector_name, date, inspection_count.
    """
    assigned = schedule_df.dropna(subset=["inspector_id", "scheduled_date"])
    if assigned.empty:
        return pd.DataFrame(columns=["inspector_name", "scheduled_date", "count"])

    workload = (
        assigned.groupby(["inspector_id", "inspector_name", "scheduled_date"])
        .size()
        .reset_index(name="count")
    )
    return workload
