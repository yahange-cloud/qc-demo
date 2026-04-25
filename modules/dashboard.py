"""
Quality Dashboard analytics module.
Provides calculations for pass rates, defect distributions, trends, and rankings.
"""
import pandas as pd
import numpy as np
import json


def calc_pass_rate(reports_df, group_by="factory_name"):
    """Calculate pass rate grouped by a given column.

    Args:
        reports_df: Inspection reports DataFrame.
        group_by: Column to group by (factory_name, product_line, region, etc.)

    Returns:
        DataFrame with group, total, pass_count, fail_count, conditional_count, pass_rate.
    """
    grouped = reports_df.groupby(group_by).agg(
        total=("result", "count"),
        pass_count=("result", lambda x: (x == "Pass").sum()),
        fail_count=("result", lambda x: (x == "Fail").sum()),
        conditional_count=("result", lambda x: (x == "Conditional").sum()),
    ).reset_index()

    grouped["pass_rate"] = (grouped["pass_count"] / grouped["total"] * 100).round(1)
    grouped["fail_rate"] = (grouped["fail_count"] / grouped["total"] * 100).round(1)
    return grouped.sort_values("pass_rate", ascending=True)


def calc_defect_distribution(reports_df):
    """Calculate defect type distribution from defect_details_parsed.

    Returns:
        DataFrame with defect_type, count, cumulative_pct (for Pareto chart).
    """
    all_defects = []
    for details in reports_df["defect_details_parsed"]:
        if isinstance(details, list):
            for d in details:
                all_defects.append({
                    "defect_type": d.get("type", "Unknown"),
                    "defect_key": d.get("type_key", "unknown"),
                    "count": d.get("count", 0),
                    "severity": d.get("severity", "minor"),
                })

    if not all_defects:
        return pd.DataFrame(columns=["defect_type", "count", "cumulative_pct"])

    df = pd.DataFrame(all_defects)
    summary = df.groupby(["defect_type", "defect_key"]).agg(
        count=("count", "sum"),
    ).reset_index().sort_values("count", ascending=False)

    total = summary["count"].sum()
    summary["pct"] = (summary["count"] / total * 100).round(1)
    summary["cumulative_pct"] = summary["pct"].cumsum().round(1)

    return summary


def calc_defect_severity_distribution(reports_df):
    """Calculate defect severity breakdown.

    Returns:
        DataFrame with severity, count.
    """
    all_defects = []
    for details in reports_df["defect_details_parsed"]:
        if isinstance(details, list):
            for d in details:
                all_defects.append({
                    "severity": d.get("severity", "minor"),
                    "count": d.get("count", 0),
                })

    if not all_defects:
        return pd.DataFrame(columns=["severity", "count"])

    df = pd.DataFrame(all_defects)
    return df.groupby("severity").agg(count=("count", "sum")).reset_index()


def calc_trend(reports_df, period="M", group_by=None):
    """Calculate quality trend over time.

    Args:
        reports_df: Inspection reports DataFrame.
        period: 'M' for monthly, 'Q' for quarterly.
        group_by: Optional column to group by (e.g. 'factory_name').

    Returns:
        DataFrame with period, pass_rate, defect_rate, and optional group.
    """
    df = reports_df.copy()
    df["period"] = df["inspection_date"].dt.to_period(period).dt.to_timestamp()

    if group_by:
        grouped = df.groupby(["period", group_by]).agg(
            total=("result", "count"),
            pass_count=("result", lambda x: (x == "Pass").sum()),
            total_defects=("total_defects", "sum"),
            total_samples=("sample_size", "sum"),
        ).reset_index()
    else:
        grouped = df.groupby("period").agg(
            total=("result", "count"),
            pass_count=("result", lambda x: (x == "Pass").sum()),
            total_defects=("total_defects", "sum"),
            total_samples=("sample_size", "sum"),
        ).reset_index()

    grouped["pass_rate"] = (grouped["pass_count"] / grouped["total"] * 100).round(1)
    grouped["defect_rate"] = (grouped["total_defects"] / grouped["total_samples"] * 100).round(2)

    return grouped.sort_values("period")


def calc_factory_ranking(reports_df, personnel_df):
    """Calculate factory ranking with multi-dimensional scores.

    Returns:
        DataFrame with factory_name, pass_rate, defect_rate, avg_response,
        improvement_trend, quality_rating, overall_score.
    """
    # Pass rate per factory
    pass_rates = calc_pass_rate(reports_df, "factory_id")

    # Defect rate per factory
    factory_defect = reports_df.groupby("factory_id").agg(
        total_defects=("total_defects", "sum"),
        total_samples=("sample_size", "sum"),
        inspection_count=("report_id", "count"),
    ).reset_index()
    factory_defect["defect_rate"] = (
        factory_defect["total_defects"] / factory_defect["total_samples"] * 100
    ).round(2)

    # Get factory info
    factory_info = personnel_df.drop_duplicates("factory_id")[
        ["factory_id", "factory_name", "region", "quality_rating"]
    ]

    # Improvement trend (compare last 2 months)
    df = reports_df.copy()
    df["month"] = df["inspection_date"].dt.to_period("M")
    months = sorted(df["month"].unique())

    improvement = {}
    if len(months) >= 2:
        last_month = df[df["month"] == months[-1]]
        prev_month = df[df["month"] == months[-2]]
        for fid in df["factory_id"].unique():
            last_pr = last_month[last_month["factory_id"] == fid]
            prev_pr = prev_month[prev_month["factory_id"] == fid]
            if len(last_pr) > 0 and len(prev_pr) > 0:
                last_rate = (last_pr["result"] == "Pass").mean() * 100
                prev_rate = (prev_pr["result"] == "Pass").mean() * 100
                improvement[fid] = round(last_rate - prev_rate, 1)
            else:
                improvement[fid] = 0.0

    # Merge all metrics
    ranking = factory_info.merge(pass_rates[["factory_id", "pass_rate", "total"]], on="factory_id", how="left")
    ranking = ranking.merge(factory_defect[["factory_id", "defect_rate", "inspection_count"]], on="factory_id", how="left")
    ranking["improvement_trend"] = ranking["factory_id"].map(improvement).fillna(0)

    # Overall score (weighted)
    ranking["overall_score"] = (
        ranking["pass_rate"].fillna(0) * 0.35
        + (100 - ranking["defect_rate"].fillna(0) * 10) * 0.25
        + ranking["quality_rating"] * 0.25
        + ranking["improvement_trend"].clip(-10, 10).add(10).mul(5) * 0.15
    ).round(1)

    return ranking.sort_values("overall_score", ascending=False)


def calc_aql_switch_status(reports_df):
    """Determine AQL inspection level switch status per factory.

    Logic:
    - 2 consecutive fails -> Tightened
    - 5 consecutive passes -> Reduced
    - Otherwise -> Normal

    Returns:
        Dict of factory_id -> {'status': str, 'consecutive_passes': int, 'consecutive_fails': int}
    """
    result = {}

    for factory_id, group in reports_df.groupby("factory_id"):
        ordered = group.sort_values("inspection_date")
        results_list = ordered["result"].tolist()

        consecutive_passes = 0
        consecutive_fails = 0

        # Count from most recent
        for r in reversed(results_list):
            if r == "Pass":
                if consecutive_fails > 0:
                    break
                consecutive_passes += 1
            elif r == "Fail":
                if consecutive_passes > 0:
                    break
                consecutive_fails += 1
            else:  # Conditional
                break

        if consecutive_fails >= 2:
            status = "Tightened"
        elif consecutive_passes >= 5:
            status = "Reduced"
        else:
            status = "Normal"

        result[factory_id] = {
            "status": status,
            "consecutive_passes": consecutive_passes,
            "consecutive_fails": consecutive_fails,
        }

    return result


def calc_kpi_summary(reports_df, requests_df):
    """Calculate top-level KPI metrics.

    Returns:
        dict with total_inspections, avg_pass_rate, avg_defect_rate, pending_requests.
    """
    total_inspections = len(reports_df)
    avg_pass_rate = round((reports_df["result"] == "Pass").mean() * 100, 1) if len(reports_df) > 0 else 0
    avg_defect_rate = round(
        (reports_df["total_defects"].sum() / reports_df["sample_size"].sum() * 100), 2
    ) if reports_df["sample_size"].sum() > 0 else 0
    pending_requests = len(requests_df[requests_df["status"] == "Pending"])

    return {
        "total_inspections": total_inspections,
        "avg_pass_rate": avg_pass_rate,
        "avg_defect_rate": avg_defect_rate,
        "pending_requests": pending_requests,
    }


def calc_region_summary(reports_df, personnel_df):
    """Calculate quality metrics per region for map visualization.

    Returns:
        DataFrame with region, pass_rate, defect_rate, inspection_count, lat, lon.
    """
    # Map factory to region
    factory_region = personnel_df.drop_duplicates("factory_id").set_index("factory_id")["region"]
    df = reports_df.copy()
    df["region"] = df["factory_id"].map(factory_region)

    region_stats = df.groupby("region").agg(
        total=("result", "count"),
        pass_count=("result", lambda x: (x == "Pass").sum()),
        total_defects=("total_defects", "sum"),
        total_samples=("sample_size", "sum"),
    ).reset_index()

    region_stats["pass_rate"] = (region_stats["pass_count"] / region_stats["total"] * 100).round(1)
    region_stats["defect_rate"] = (region_stats["total_defects"] / region_stats["total_samples"] * 100).round(2)

    # Country coordinates for map
    coords = {
        "China": {"lat": 35.0, "lon": 105.0, "iso_alpha": "CHN"},
        "Vietnam": {"lat": 16.0, "lon": 108.0, "iso_alpha": "VNM"},
        "India": {"lat": 20.5, "lon": 79.0, "iso_alpha": "IND"},
    }
    region_stats["lat"] = region_stats["region"].map(lambda r: coords.get(r, {}).get("lat", 0))
    region_stats["lon"] = region_stats["region"].map(lambda r: coords.get(r, {}).get("lon", 0))
    region_stats["iso_alpha"] = region_stats["region"].map(lambda r: coords.get(r, {}).get("iso_alpha", ""))

    return region_stats
