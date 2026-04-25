"""
Global configuration for QC Inspection Management System.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Claude API ---
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# --- Scheduling weights ---
SCHEDULING_WEIGHTS = {
    "urgency": 0.35,      # W1: shipment deadline urgency
    "risk": 0.30,         # W2: factory quality risk
    "customer": 0.20,     # W3: customer level
    "capacity": 0.15,     # W4: inspector availability
}

CUSTOMER_LEVEL_SCORES = {
    "A": 1.0,
    "B": 0.6,
    "C": 0.3,
}

# --- Quality thresholds ---
QUALITY_THRESHOLDS = {
    "pass_rate_warning": 90,       # pass rate below this triggers alert (%)
    "pass_rate_critical": 80,      # critical alert threshold (%)
    "critical_defect_tolerance": 0,
    "consecutive_fails_trigger": 2,
    "defect_rate_spike": 1.5,      # 50% increase triggers alert
    "recurring_defect_count": 3,
}

# --- Alert triggers ---
ALERT_TRIGGERS = {
    "pass_rate_below": 90,
    "critical_defect_found": True,
    "consecutive_fails": 2,
    "defect_rate_spike": 1.5,
    "same_defect_recurring": 3,
}

# --- Defect types (bilingual keys) ---
DEFECT_TYPES = [
    "welding_defect",
    "surface_scratch",
    "dimension_deviation",
    "logo_misalignment",
    "vacuum_leak",
    "color_deviation",
    "packaging_damage",
    "functional_failure",
]

# --- Product lines ---
PRODUCT_LINES = ["Iceflow", "Aerolight", "Quencher", "Adventure", "Classic"]

# --- Color theme ---
COLORS = {
    "primary": "#1f77b4",
    "success": "#2ca02c",
    "warning": "#ff7f0e",
    "danger": "#d62728",
    "info": "#17becf",
    "pass": "#2ca02c",
    "fail": "#d62728",
    "conditional": "#ff7f0e",
    "chart_palette": [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
    ],
}

# --- Data paths (relative to project root) ---
DATA_DIR = "data"
DATA_FILES = {
    "inspection_requests": f"{DATA_DIR}/inspection_requests.csv",
    "inspection_reports": f"{DATA_DIR}/inspection_reports.csv",
    "sampling_rules": f"{DATA_DIR}/sampling_rules.csv",
    "factory_personnel": f"{DATA_DIR}/factory_personnel.csv",
}
