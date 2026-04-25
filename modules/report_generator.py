"""
Quality improvement report generator.
Scans for alert triggers, generates rule-based summaries, and orchestrates AI analysis.
"""
import pandas as pd
from config import ALERT_TRIGGERS
from modules.ai_analyzer import (
    build_prompt,
    call_claude_api,
    generate_rule_based_report,
)


def scan_triggers(reports_df, personnel_df):
    """Scan all factories for alert trigger conditions.

    Trigger conditions:
    - pass_rate_below: pass rate < threshold
    - critical_defect_found: any critical defect > 0
    - consecutive_fails: N consecutive Fail results
    - defect_rate_spike: defect rate increased by >50% month-over-month
    - same_defect_recurring: same defect type appears N+ times

    Args:
        reports_df: Inspection reports DataFrame (with defect_details_parsed).
        personnel_df: Personnel DataFrame.

    Returns:
        List of dicts: [{factory_id, factory_name, triggers: [reason_strings], risk_level}]
    """
    factory_info = personnel_df.drop_duplicates("factory_id").set_index("factory_id")
    alerts = []

    for factory_id, group in reports_df.groupby("factory_id"):
        if factory_id not in factory_info.index:
            continue

        fname = factory_info.loc[factory_id, "factory_name"]
        triggers = []

        # 1. Pass rate below threshold
        total = len(group)
        pass_count = (group["result"] == "Pass").sum()
        pass_rate = round(pass_count / total * 100, 1) if total > 0 else 0
        if pass_rate < ALERT_TRIGGERS["pass_rate_below"]:
            triggers.append(f"Pass rate {pass_rate}% < {ALERT_TRIGGERS['pass_rate_below']}%")

        # 2. Critical defect found
        if ALERT_TRIGGERS["critical_defect_found"]:
            critical_total = group["critical_defects"].sum()
            if critical_total > 0:
                triggers.append(f"Critical defects found: {critical_total}")

        # 3. Consecutive fails
        ordered = group.sort_values("inspection_date")
        results_list = ordered["result"].tolist()
        max_consecutive_fails = 0
        current_fails = 0
        for r in reversed(results_list):
            if r == "Fail":
                current_fails += 1
                max_consecutive_fails = max(max_consecutive_fails, current_fails)
            else:
                break
        if max_consecutive_fails >= ALERT_TRIGGERS["consecutive_fails"]:
            triggers.append(f"{max_consecutive_fails} consecutive failed batches")

        # 4. Defect rate spike (month-over-month)
        group_sorted = group.copy()
        group_sorted["month"] = group_sorted["inspection_date"].dt.to_period("M")
        months = sorted(group_sorted["month"].unique())
        if len(months) >= 2:
            last_month = group_sorted[group_sorted["month"] == months[-1]]
            prev_month = group_sorted[group_sorted["month"] == months[-2]]
            last_rate = last_month["total_defects"].sum() / max(1, last_month["sample_size"].sum())
            prev_rate = prev_month["total_defects"].sum() / max(1, prev_month["sample_size"].sum())
            if prev_rate > 0 and last_rate / prev_rate >= ALERT_TRIGGERS["defect_rate_spike"]:
                spike_pct = round((last_rate / prev_rate - 1) * 100, 0)
                triggers.append(f"Defect rate spiked by {spike_pct}% MoM")

        # 5. Same defect recurring
        defect_counts = {}
        for details in group["defect_details_parsed"]:
            if isinstance(details, list):
                for d in details:
                    dtype = d.get("type", "Unknown")
                    defect_counts[dtype] = defect_counts.get(dtype, 0) + 1
        for dtype, count in defect_counts.items():
            if count >= ALERT_TRIGGERS["same_defect_recurring"]:
                triggers.append(f"Recurring defect: {dtype} ({count} occurrences)")

        if triggers:
            # Determine risk level
            if pass_rate < 75 or max_consecutive_fails >= 3 or group["critical_defects"].sum() > 2:
                risk_level = "high"
            elif pass_rate < 90 or max_consecutive_fails >= 2:
                risk_level = "medium"
            else:
                risk_level = "low"

            alerts.append({
                "factory_id": factory_id,
                "factory_name": fname,
                "region": factory_info.loc[factory_id, "region"],
                "quality_rating": factory_info.loc[factory_id, "quality_rating"],
                "pass_rate": pass_rate,
                "inspection_count": total,
                "triggers": triggers,
                "risk_level": risk_level,
            })

    # Sort by risk level
    risk_order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda x: (risk_order.get(x["risk_level"], 3), x["pass_rate"]))

    return alerts


def build_factory_data(factory_id, reports_df, personnel_df, triggers):
    """Build the data dict needed for report generation.

    Args:
        factory_id: Factory ID.
        reports_df: Reports DataFrame.
        personnel_df: Personnel DataFrame.
        triggers: List of trigger reason strings.

    Returns:
        dict suitable for build_prompt() and generate_rule_based_report().
    """
    factory_info = personnel_df.drop_duplicates("factory_id").set_index("factory_id")
    factory_reports = reports_df[reports_df["factory_id"] == factory_id]

    # Basic info
    fname = factory_info.loc[factory_id, "factory_name"]
    region = factory_info.loc[factory_id, "region"]
    quality_rating = factory_info.loc[factory_id, "quality_rating"]

    # Pass rate
    total = len(factory_reports)
    pass_count = (factory_reports["result"] == "Pass").sum()
    pass_rate = round(pass_count / total * 100, 1) if total > 0 else 0

    # Top defects
    defect_counts = {}
    for details in factory_reports["defect_details_parsed"]:
        if isinstance(details, list):
            for d in details:
                dtype = d.get("type", "Unknown")
                cnt = d.get("count", 0)
                defect_counts[dtype] = defect_counts.get(dtype, 0) + cnt

    sorted_defects = sorted(defect_counts.items(), key=lambda x: x[1], reverse=True)
    top_defects = ", ".join(f"{d[0]}({d[1]})" for d in sorted_defects[:5])

    # Defect detail table
    detail_lines = ["| Defect Type | Count | Frequency |"]
    detail_lines.append("|---|---|---|")
    total_defects = sum(d[1] for d in sorted_defects)
    for dtype, cnt in sorted_defects:
        pct = round(cnt / max(1, total_defects) * 100, 1)
        detail_lines.append(f"| {dtype} | {cnt} | {pct}% |")
    defect_detail_table = "\n".join(detail_lines)

    return {
        "factory_name": fname,
        "region": region,
        "quality_rating": quality_rating,
        "inspection_count": total,
        "pass_rate": pass_rate,
        "top_defects": top_defects if top_defects else "N/A",
        "trigger_reasons": "; ".join(triggers),
        "defect_detail_table": defect_detail_table,
    }


def generate_report(factory_id, reports_df, personnel_df, triggers, lang="zh", use_ai=True):
    """Generate a complete quality improvement report for a factory.

    Tries AI first, falls back to rule-based if AI is unavailable.

    Args:
        factory_id: Factory ID.
        reports_df: Reports DataFrame.
        personnel_df: Personnel DataFrame.
        triggers: List of trigger reason strings.
        lang: 'zh' or 'en'.
        use_ai: Whether to attempt AI generation.

    Returns:
        tuple: (report_text, source) where source is 'ai' or 'rule-based'.
    """
    factory_data = build_factory_data(factory_id, reports_df, personnel_df, triggers)

    if use_ai:
        prompt = build_prompt(factory_data, lang)
        response, success = call_claude_api(prompt)
        if success:
            return response, "ai"

    # Fallback to rule-based
    report = generate_rule_based_report(factory_data, lang)
    return report, "rule-based"


def generate_all_reports(alerts, reports_df, personnel_df, lang="zh", use_ai=True):
    """Generate reports for all alerted factories.

    Args:
        alerts: List from scan_triggers().
        reports_df: Reports DataFrame.
        personnel_df: Personnel DataFrame.
        lang: 'zh' or 'en'.
        use_ai: Whether to attempt AI generation.

    Returns:
        List of dicts: [{factory_id, factory_name, report, source, risk_level}]
    """
    results = []
    for alert in alerts:
        report_text, source = generate_report(
            alert["factory_id"],
            reports_df,
            personnel_df,
            alert["triggers"],
            lang=lang,
            use_ai=use_ai,
        )
        results.append({
            "factory_id": alert["factory_id"],
            "factory_name": alert["factory_name"],
            "risk_level": alert["risk_level"],
            "triggers": alert["triggers"],
            "report": report_text,
            "source": source,
        })
    return results
