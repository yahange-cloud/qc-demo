"""
QC Inspection Management System - Main Entry Point
"""
import os
import streamlit as st
import pandas as pd
from utils.helpers import init_session_state, switch_language, t

# Page config must be the first Streamlit command
st.set_page_config(
    page_title="QC Inspection System",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
init_session_state()

# --- Custom CSS ---
st.markdown("""
<style>
    /* Header styling */
    .stApp header {
        background-color: transparent;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-right: 1px solid #e0e0e0;
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #555;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e8e8e8;
        border-radius: 8px;
        padding: 12px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    [data-testid="stMetric"] label {
        font-size: 0.8rem !important;
        color: #888 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #1f77b4 !important;
    }

    /* Dataframe styling */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
    }

    /* Button styling */
    .stButton > button[kind="primary"] {
        background-color: #1f77b4;
        border: none;
        border-radius: 6px;
        font-weight: 600;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #1565a0;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
    }

    /* Divider */
    hr {
        border-color: #e8e8e8 !important;
    }

    /* Upload area */
    [data-testid="stFileUploader"] {
        border: 2px dashed #ccc;
        border-radius: 8px;
        padding: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar: Language switcher ---
with st.sidebar:
    st.title(t("app_title"))
    lang_options = {"中文": "zh", "English": "en"}
    selected_lang = st.selectbox(
        t("language"),
        options=list(lang_options.keys()),
        index=0 if st.session_state["lang"] == "zh" else 1,
    )
    new_lang = lang_options[selected_lang]
    if new_lang != st.session_state["lang"]:
        switch_language(new_lang)
        st.rerun()

    st.divider()

    # --- Data Upload ---
    with st.expander(t("upload_title"), expanded=False):
        st.caption(t("upload_description"))
        uploaded_file = st.file_uploader(
            "CSV / Excel",
            type=["csv", "xlsx"],
            label_visibility="collapsed",
        )
        upload_target = st.selectbox(
            "Target",
            ["inspection_requests", "inspection_reports", "factory_personnel", "sampling_rules"],
            label_visibility="collapsed",
        )

        if uploaded_file and st.button("Upload", use_container_width=True):
            try:
                data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
                if uploaded_file.name.endswith(".csv"):
                    new_df = pd.read_csv(uploaded_file)
                else:
                    new_df = pd.read_excel(uploaded_file)

                save_path = os.path.join(data_dir, f"{upload_target}.csv")
                new_df.to_csv(save_path, index=False)

                # Clear cached data so it reloads
                st.cache_data.clear()
                st.success(t("upload_success"))
                st.rerun()
            except Exception as e:
                st.error(t("upload_error", error=str(e)))

# --- Main page: Navigation ---
scheduling_page = st.Page("pages/1_Scheduling.py", title=t("nav_scheduling"), icon="📅")
dashboard_page = st.Page("pages/2_Dashboard.py", title=t("nav_dashboard"), icon="📊")

pg = st.navigation([scheduling_page, dashboard_page])
pg.run()
