"""
Mock data generator for QC Inspection Management System.
Generates realistic inspection data covering 6 months.
"""
import os
import sys
import random
import json
from datetime import datetime, timedelta

import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DEFECT_TYPES, PRODUCT_LINES

random.seed(42)

# --- Constants ---
START_DATE = datetime(2025, 10, 1)
END_DATE = datetime(2026, 3, 26)
DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Factory definitions ---
FACTORIES = [
    {"factory_id": "FAC-CAYI-CN", "factory_name": "CAYI China", "region": "China", "city": "Wuyi", "capability": "Welding/Vacuum/Assembly", "quality_rating": 92.5},
    {"factory_id": "FAC-CAYI-VN", "factory_name": "CAYI Vietnam", "region": "Vietnam", "city": "Ho Chi Minh", "capability": "Welding/Assembly", "quality_rating": 88.0},
    {"factory_id": "FAC-ANSHENG", "factory_name": "ANSHENG", "region": "China", "city": "Yongkang", "capability": "Stamping/Welding/Vacuum", "quality_rating": 78.5},
    {"factory_id": "FAC-GINT", "factory_name": "GINT", "region": "China", "city": "Guangzhou", "capability": "Welding/Coating/Assembly", "quality_rating": 95.0},
    {"factory_id": "FAC-HAERS", "factory_name": "HAERS", "region": "China", "city": "Yongkang", "capability": "Vacuum/Welding/Polishing", "quality_rating": 91.0},
    {"factory_id": "FAC-LISI", "factory_name": "LISI", "region": "Vietnam", "city": "Hanoi", "capability": "Welding/Assembly/Packaging", "quality_rating": 73.0},
    {"factory_id": "FAC-FLYCUP", "factory_name": "FlyCup", "region": "India", "city": "Mumbai", "capability": "Welding/Coating", "quality_rating": 82.0},
    {"factory_id": "FAC-YKPHX", "factory_name": "YKPHX", "region": "China", "city": "Yongkang", "capability": "Vacuum/Welding/Assembly", "quality_rating": 89.5},
    {"factory_id": "FAC-DLJM", "factory_name": "DLJM", "region": "India", "city": "Delhi", "capability": "Stamping/Welding", "quality_rating": 70.5},
]

# --- Inspector definitions ---
INSPECTORS = [
    {"inspector_id": "INS-001", "inspector_name": "Zhang Wei", "inspector_region": "East China", "max_inspections_per_day": 2, "available_days": "Mon-Fri"},
    {"inspector_id": "INS-002", "inspector_name": "Li Fang", "inspector_region": "East China", "max_inspections_per_day": 2, "available_days": "Mon-Fri"},
    {"inspector_id": "INS-003", "inspector_name": "Wang Jun", "inspector_region": "South China", "max_inspections_per_day": 2, "available_days": "Mon-Fri"},
    {"inspector_id": "INS-004", "inspector_name": "Nguyen Thi", "inspector_region": "Vietnam", "max_inspections_per_day": 2, "available_days": "Mon-Sat"},
    {"inspector_id": "INS-005", "inspector_name": "Tran Van", "inspector_region": "Vietnam", "max_inspections_per_day": 2, "available_days": "Mon-Sat"},
    {"inspector_id": "INS-006", "inspector_name": "Raj Patel", "inspector_region": "India", "max_inspections_per_day": 3, "available_days": "Mon-Sat"},
    {"inspector_id": "INS-007", "inspector_name": "Chen Ming", "inspector_region": "East China", "max_inspections_per_day": 2, "available_days": "Mon-Fri"},
]

# Region to inspector mapping
REGION_INSPECTOR_MAP = {
    "China": ["INS-001", "INS-002", "INS-003", "INS-007"],
    "Vietnam": ["INS-004", "INS-005"],
    "India": ["INS-006"],
}

# SKU definitions per product line
SKU_MAP = {
    "Iceflow": ["SKU-IF-500ML", "SKU-IF-750ML", "SKU-IF-1L"],
    "Aerolight": ["SKU-AL-350ML", "SKU-AL-500ML", "SKU-AL-700ML"],
    "Quencher": ["SKU-QC-600ML", "SKU-QC-900ML", "SKU-QC-1.2L"],
    "Adventure": ["SKU-AD-500ML", "SKU-AD-750ML"],
    "Classic": ["SKU-CL-350ML", "SKU-CL-500ML", "SKU-CL-750ML"],
}

# Defect severity probabilities per type
DEFECT_SEVERITY = {
    "welding_defect": {"critical": 0.05, "major": 0.35, "minor": 0.60},
    "surface_scratch": {"critical": 0.0, "major": 0.10, "minor": 0.90},
    "dimension_deviation": {"critical": 0.10, "major": 0.40, "minor": 0.50},
    "logo_misalignment": {"critical": 0.0, "major": 0.20, "minor": 0.80},
    "vacuum_leak": {"critical": 0.30, "major": 0.50, "minor": 0.20},
    "color_deviation": {"critical": 0.0, "major": 0.15, "minor": 0.85},
    "packaging_damage": {"critical": 0.0, "major": 0.10, "minor": 0.90},
    "functional_failure": {"critical": 0.40, "major": 0.40, "minor": 0.20},
}

# Defect display names (for defect_details JSON)
DEFECT_NAMES_ZH = {
    "welding_defect": "焊接不良",
    "surface_scratch": "外观划伤",
    "dimension_deviation": "尺寸偏差",
    "logo_misalignment": "logo偏位",
    "vacuum_leak": "真空泄漏",
    "color_deviation": "颜色色差",
    "packaging_damage": "包装破损",
    "functional_failure": "功能异常",
}


def random_date(start, end):
    """Generate a random date between start and end."""
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def generate_factory_personnel():
    """Generate factory_personnel.csv with factory + inspector info."""
    rows = []
    for factory in FACTORIES:
        region = factory["region"]
        inspectors = REGION_INSPECTOR_MAP.get(region, [])
        for ins_id in inspectors:
            ins = next(i for i in INSPECTORS if i["inspector_id"] == ins_id)
            rows.append({
                "factory_id": factory["factory_id"],
                "factory_name": factory["factory_name"],
                "region": factory["region"],
                "city": factory["city"],
                "capability": factory["capability"],
                "quality_rating": factory["quality_rating"],
                "inspector_id": ins["inspector_id"],
                "inspector_name": ins["inspector_name"],
                "inspector_region": ins["inspector_region"],
                "max_inspections_per_day": ins["max_inspections_per_day"],
                "available_days": ins["available_days"],
            })
    return pd.DataFrame(rows)


def generate_sampling_rules():
    """Generate sampling_rules.csv based on ISO 2859-1 / AQL standards."""
    rules = [
        {"rule_id": "RULE-001", "aql_level": "Level II", "inspection_level": "Normal",
         "lot_size_min": 2, "lot_size_max": 8, "sample_size": 2,
         "critical_accept": 0, "major_accept": 0, "minor_accept": 0,
         "trigger_tightened": "2 consecutive fails", "trigger_reduced": "5 consecutive passes"},
        {"rule_id": "RULE-002", "aql_level": "Level II", "inspection_level": "Normal",
         "lot_size_min": 9, "lot_size_max": 150, "sample_size": 13,
         "critical_accept": 0, "major_accept": 1, "minor_accept": 2,
         "trigger_tightened": "2 consecutive fails", "trigger_reduced": "5 consecutive passes"},
        {"rule_id": "RULE-003", "aql_level": "Level II", "inspection_level": "Normal",
         "lot_size_min": 151, "lot_size_max": 1200, "sample_size": 50,
         "critical_accept": 0, "major_accept": 2, "minor_accept": 5,
         "trigger_tightened": "2 consecutive fails", "trigger_reduced": "5 consecutive passes"},
        {"rule_id": "RULE-004", "aql_level": "Level II", "inspection_level": "Normal",
         "lot_size_min": 1201, "lot_size_max": 3200, "sample_size": 80,
         "critical_accept": 0, "major_accept": 3, "minor_accept": 7,
         "trigger_tightened": "2 consecutive fails", "trigger_reduced": "5 consecutive passes"},
        {"rule_id": "RULE-005", "aql_level": "Level II", "inspection_level": "Normal",
         "lot_size_min": 3201, "lot_size_max": 10000, "sample_size": 125,
         "critical_accept": 0, "major_accept": 5, "minor_accept": 10,
         "trigger_tightened": "2 consecutive fails", "trigger_reduced": "5 consecutive passes"},
        {"rule_id": "RULE-006", "aql_level": "Level II", "inspection_level": "Normal",
         "lot_size_min": 10001, "lot_size_max": 35000, "sample_size": 200,
         "critical_accept": 0, "major_accept": 7, "minor_accept": 14,
         "trigger_tightened": "2 consecutive fails", "trigger_reduced": "5 consecutive passes"},
        {"rule_id": "RULE-007", "aql_level": "Level II", "inspection_level": "Tightened",
         "lot_size_min": 1201, "lot_size_max": 3200, "sample_size": 125,
         "critical_accept": 0, "major_accept": 2, "minor_accept": 5,
         "trigger_tightened": "N/A", "trigger_reduced": "5 consecutive passes"},
        {"rule_id": "RULE-008", "aql_level": "Level II", "inspection_level": "Reduced",
         "lot_size_min": 1201, "lot_size_max": 3200, "sample_size": 32,
         "critical_accept": 0, "major_accept": 1, "minor_accept": 3,
         "trigger_tightened": "1 fail reverts to Normal", "trigger_reduced": "N/A"},
    ]
    return pd.DataFrame(rules)


def get_sample_size(order_qty, rules_df):
    """Look up sample size from sampling rules based on order quantity."""
    normal_rules = rules_df[rules_df["inspection_level"] == "Normal"]
    for _, rule in normal_rules.iterrows():
        if rule["lot_size_min"] <= order_qty <= rule["lot_size_max"]:
            return rule["sample_size"]
    return 200  # default for large lots


def generate_defect_details(total_defects, factory_quality):
    """Generate realistic defect details JSON based on factory quality."""
    if total_defects == 0:
        return "[]"

    # Lower quality factories tend to have more welding and vacuum issues
    if factory_quality < 80:
        weights = [0.25, 0.10, 0.15, 0.05, 0.20, 0.05, 0.05, 0.15]
    else:
        weights = [0.15, 0.20, 0.10, 0.15, 0.05, 0.15, 0.15, 0.05]

    details = []
    remaining = total_defects
    selected_types = random.choices(DEFECT_TYPES, weights=weights, k=min(total_defects, random.randint(2, 5)))
    selected_types = list(set(selected_types))

    for i, defect_type in enumerate(selected_types):
        if i == len(selected_types) - 1:
            count = remaining
        else:
            count = random.randint(1, max(1, remaining - (len(selected_types) - i - 1)))
            remaining -= count

        if count <= 0:
            continue

        sev_probs = DEFECT_SEVERITY[defect_type]
        severity = random.choices(
            ["critical", "major", "minor"],
            weights=[sev_probs["critical"], sev_probs["major"], sev_probs["minor"]],
            k=1
        )[0]

        details.append({
            "type": DEFECT_NAMES_ZH[defect_type],
            "type_key": defect_type,
            "count": count,
            "severity": severity,
        })

    return json.dumps(details, ensure_ascii=False)


def generate_inspection_requests(n=120):
    """Generate inspection_requests.csv with realistic data."""
    rows = []
    for i in range(1, n + 1):
        factory = random.choice(FACTORIES)
        product_line = random.choice(PRODUCT_LINES)
        sku = random.choice(SKU_MAP[product_line])
        requested_date = random_date(START_DATE, END_DATE)
        shipment_deadline = requested_date + timedelta(days=random.randint(7, 21))
        customer_level = random.choices(["A", "B", "C"], weights=[0.3, 0.45, 0.25], k=1)[0]

        # Priority correlates with customer level and deadline proximity
        if customer_level == "A" or (shipment_deadline - requested_date).days <= 10:
            priority = random.choices(["High", "Medium", "Low"], weights=[0.6, 0.3, 0.1], k=1)[0]
        elif customer_level == "B":
            priority = random.choices(["High", "Medium", "Low"], weights=[0.2, 0.5, 0.3], k=1)[0]
        else:
            priority = random.choices(["High", "Medium", "Low"], weights=[0.1, 0.3, 0.6], k=1)[0]

        # Status based on date relative to "now"
        if requested_date > END_DATE - timedelta(days=14):
            status = random.choices(["Pending", "Scheduled"], weights=[0.6, 0.4], k=1)[0]
        elif requested_date > END_DATE - timedelta(days=30):
            status = random.choices(["Pending", "Scheduled", "Completed"], weights=[0.1, 0.3, 0.6], k=1)[0]
        else:
            status = random.choices(["Scheduled", "Completed"], weights=[0.1, 0.9], k=1)[0]

        rows.append({
            "request_id": f"REQ-{requested_date.year}-{i:03d}",
            "factory_id": factory["factory_id"],
            "factory_name": factory["factory_name"],
            "product_line": product_line,
            "sku": sku,
            "order_id": f"PO-{requested_date.year}-{random.randint(1000, 9999)}",
            "order_qty": random.choice([5000, 8000, 10000, 15000, 20000, 30000, 50000]),
            "customer_level": customer_level,
            "requested_date": requested_date.strftime("%Y-%m-%d"),
            "shipment_deadline": shipment_deadline.strftime("%Y-%m-%d"),
            "priority": priority,
            "status": status,
            "region": factory["region"],
        })

    return pd.DataFrame(rows)


def generate_inspection_reports(requests_df, rules_df):
    """Generate inspection_reports.csv for completed/scheduled requests."""
    eligible = requests_df[requests_df["status"].isin(["Completed", "Scheduled"])].copy()
    rows = []
    factory_map = {f["factory_id"]: f for f in FACTORIES}

    for idx, (_, req) in enumerate(eligible.iterrows(), 1):
        factory = factory_map[req["factory_id"]]
        quality = factory["quality_rating"]
        region = factory["region"]
        inspectors = REGION_INSPECTOR_MAP.get(region, ["INS-001"])

        sample_size = get_sample_size(req["order_qty"], rules_df)
        inspection_date = datetime.strptime(req["requested_date"], "%Y-%m-%d") + timedelta(days=random.randint(1, 5))

        # Defect generation based on factory quality
        base_defect_rate = (100 - quality) / 100 * 0.3
        defect_rate = max(0, base_defect_rate + random.gauss(0, 0.02))
        total_defects = max(0, int(sample_size * defect_rate))

        # Split defects
        if total_defects == 0:
            critical, major, minor = 0, 0, 0
        else:
            # Lower quality factories more likely to have critical defects
            if quality < 75:
                critical = random.choices([0, 1, 2], weights=[0.5, 0.35, 0.15], k=1)[0]
            elif quality < 85:
                critical = random.choices([0, 1], weights=[0.85, 0.15], k=1)[0]
            else:
                critical = random.choices([0, 1], weights=[0.95, 0.05], k=1)[0]

            critical = min(critical, total_defects)
            remaining = total_defects - critical
            major = int(remaining * random.uniform(0.2, 0.4))
            minor = remaining - major

        # Determine result
        if critical > 0:
            result = "Fail"
        elif quality < 75 and total_defects > sample_size * 0.05:
            result = random.choices(["Fail", "Conditional"], weights=[0.6, 0.4], k=1)[0]
        elif total_defects > sample_size * 0.04:
            result = random.choices(["Conditional", "Pass"], weights=[0.5, 0.5], k=1)[0]
        elif total_defects > sample_size * 0.02:
            result = random.choices(["Pass", "Conditional"], weights=[0.7, 0.3], k=1)[0]
        else:
            result = "Pass"

        defect_details = generate_defect_details(total_defects, quality)

        # Generate remarks based on result
        remarks_map = {
            "Pass": "",
            "Conditional": random.choice([
                "Minor cosmetic issues, acceptable with rework",
                "Slight dimension deviation within tolerance",
                "Minor packaging damage, needs re-inspection after fix",
            ]),
            "Fail": random.choice([
                "Weld seam misalignment, full rework required",
                "Vacuum leak detected, batch rejected",
                "Multiple critical defects, production line review needed",
                "Logo position out of spec, re-production required",
            ]),
        }

        rows.append({
            "report_id": f"RPT-{inspection_date.year}-{idx:03d}",
            "request_id": req["request_id"],
            "factory_id": req["factory_id"],
            "inspector_id": random.choice(inspectors),
            "inspection_date": inspection_date.strftime("%Y-%m-%d"),
            "product_line": req["product_line"],
            "sku": req["sku"],
            "sample_size": sample_size,
            "total_defects": total_defects,
            "critical_defects": critical,
            "major_defects": major,
            "minor_defects": minor,
            "defect_details": defect_details,
            "result": result,
            "remarks": remarks_map[result],
        })

    return pd.DataFrame(rows)


def main():
    """Generate all mock data files."""
    print("Generating mock data...")

    # 1. Factory & Personnel
    personnel_df = generate_factory_personnel()
    personnel_df.to_csv(os.path.join(DATA_DIR, "factory_personnel.csv"), index=False)
    print(f"  factory_personnel.csv: {len(personnel_df)} rows")

    # 2. Sampling rules
    rules_df = generate_sampling_rules()
    rules_df.to_csv(os.path.join(DATA_DIR, "sampling_rules.csv"), index=False)
    print(f"  sampling_rules.csv: {len(rules_df)} rows")

    # 3. Inspection requests
    requests_df = generate_inspection_requests(120)
    requests_df.to_csv(os.path.join(DATA_DIR, "inspection_requests.csv"), index=False)
    print(f"  inspection_requests.csv: {len(requests_df)} rows")

    # 4. Inspection reports
    reports_df = generate_inspection_reports(requests_df, rules_df)
    reports_df.to_csv(os.path.join(DATA_DIR, "inspection_reports.csv"), index=False)
    print(f"  inspection_reports.csv: {len(reports_df)} rows")

    print("Done! All mock data generated.")


if __name__ == "__main__":
    main()
