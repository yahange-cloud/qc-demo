"""
Data loading and cleaning module.
Reads CSV files and provides cleaned, typed DataFrames.
"""
import os
import json
import pandas as pd
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


@st.cache_data(ttl=300)
def load_inspection_requests(path=None):
    """Load and clean inspection requests data."""
    if path is None:
        path = os.path.join(DATA_DIR, "inspection_requests.csv")
    df = pd.read_csv(path)
    df["requested_date"] = pd.to_datetime(df["requested_date"])
    df["shipment_deadline"] = pd.to_datetime(df["shipment_deadline"])
    df["order_qty"] = df["order_qty"].astype(int)
    return df


@st.cache_data(ttl=300)
def load_inspection_reports(path=None):
    """Load and clean inspection reports data."""
    if path is None:
        path = os.path.join(DATA_DIR, "inspection_reports.csv")
    df = pd.read_csv(path)
    df["inspection_date"] = pd.to_datetime(df["inspection_date"])
    df["sample_size"] = df["sample_size"].astype(int)
    df["total_defects"] = df["total_defects"].astype(int)
    df["critical_defects"] = df["critical_defects"].astype(int)
    df["major_defects"] = df["major_defects"].astype(int)
    df["minor_defects"] = df["minor_defects"].astype(int)
    # Parse defect_details JSON
    df["defect_details_parsed"] = df["defect_details"].apply(_parse_json_safe)
    return df


@st.cache_data(ttl=300)
def load_sampling_rules(path=None):
    """Load sampling rules data."""
    if path is None:
        path = os.path.join(DATA_DIR, "sampling_rules.csv")
    df = pd.read_csv(path)
    return df


@st.cache_data(ttl=300)
def load_factory_personnel(path=None):
    """Load factory and inspector information."""
    if path is None:
        path = os.path.join(DATA_DIR, "factory_personnel.csv")
    df = pd.read_csv(path)
    df["quality_rating"] = df["quality_rating"].astype(float)
    df["max_inspections_per_day"] = df["max_inspections_per_day"].astype(int)
    return df


def load_all_data():
    """Load all data files and return as a dict."""
    return {
        "requests": load_inspection_requests(),
        "reports": load_inspection_reports(),
        "rules": load_sampling_rules(),
        "personnel": load_factory_personnel(),
    }


def get_factory_list(personnel_df):
    """Get unique factory list with their info."""
    return personnel_df.drop_duplicates(subset=["factory_id"])[
        ["factory_id", "factory_name", "region", "city", "capability", "quality_rating"]
    ].reset_index(drop=True)


def get_inspector_list(personnel_df):
    """Get unique inspector list."""
    return personnel_df.drop_duplicates(subset=["inspector_id"])[
        ["inspector_id", "inspector_name", "inspector_region", "max_inspections_per_day", "available_days"]
    ].reset_index(drop=True)


def merge_requests_reports(requests_df, reports_df):
    """Merge requests with their corresponding reports."""
    return requests_df.merge(
        reports_df,
        on="request_id",
        how="left",
        suffixes=("", "_report"),
    )


def _parse_json_safe(val):
    """Safely parse JSON string, return empty list on failure."""
    if pd.isna(val) or val == "":
        return []
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return []
