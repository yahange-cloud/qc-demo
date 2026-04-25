"""
Page 1: Inspection Scheduling
Interactive scheduling with Gantt chart and workload heatmap.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
import plotly.graph_objects as go
from datetime import datetime, timedelta

from utils.helpers import t, init_session_state
from utils.export import export_dataframe_to_excel
from modules.data_loader import load_inspection_requests, load_factory_personnel
from modules.scheduler import (
    generate_schedule,
    detect_conflicts,
    get_inspector_workload,
    calculate_priority_score,
)

init_session_state()

st.header(t("scheduling_title"))

# --- Load data ---
requests_df = load_inspection_requests()
personnel_df = load_factory_personnel()

# --- Sidebar filters ---
with st.sidebar:
    st.subheader(t("filter_date_range"))
    min_date = requests_df["requested_date"].min().date()
    max_date = requests_df["shipment_deadline"].max().date()
    date_range = st.date_input(
        t("filter_date_range"),
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        label_visibility="collapsed",
    )

    st.subheader(t("filter_region"))
    all_regions = requests_df["region"].unique().tolist()
    selected_regions = st.multiselect(t("filter_region"), all_regions, default=all_regions, label_visibility="collapsed")

    st.subheader(t("filter_factory"))
    filtered_factories = requests_df[requests_df["region"].isin(selected_regions)]["factory_name"].unique().tolist()
    selected_factories = st.multiselect(t("filter_factory"), filtered_factories, default=filtered_factories, label_visibility="collapsed")

    st.subheader(t("filter_priority"))
    all_priorities = ["High", "Medium", "Low"]
    selected_priorities = st.multiselect(t("filter_priority"), all_priorities, default=all_priorities, label_visibility="collapsed")

# --- Apply filters ---
filtered_requests = requests_df.copy()
if len(date_range) == 2:
    start_d, end_d = date_range
    filtered_requests = filtered_requests[
        (filtered_requests["requested_date"].dt.date >= start_d)
        & (filtered_requests["requested_date"].dt.date <= end_d)
    ]
filtered_requests = filtered_requests[
    (filtered_requests["region"].isin(selected_regions))
    & (filtered_requests["factory_name"].isin(selected_factories))
    & (filtered_requests["priority"].isin(selected_priorities))
]

# --- Generate schedule button ---
st.divider()
col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    generate_btn = st.button(t("scheduling_generate"), type="primary", use_container_width=True)

if generate_btn or "schedule_df" in st.session_state:
    if generate_btn:
        with st.spinner(t("scheduling_generate") + "..."):
            schedule_df = generate_schedule(filtered_requests, personnel_df)
            st.session_state["schedule_df"] = schedule_df

    schedule_df = st.session_state["schedule_df"]

    if schedule_df.empty:
        st.warning("No schedulable requests found (Pending/Scheduled status required).")
    else:
        # --- Conflict Detection ---
        conflicts = detect_conflicts(schedule_df, personnel_df)
        if conflicts:
            st.error(t("scheduling_conflict_found", count=len(conflicts)))
            with st.expander(t("scheduling_conflict"), expanded=False):
                for c in conflicts:
                    st.warning(c["description"])
        else:
            st.success(t("scheduling_no_conflict"))

        # --- Schedule Results Table ---
        st.subheader(t("scheduling_result_table"))

        display_cols = [
            "request_id", "factory_name", "product_line", "sku",
            "customer_level", "priority", "priority_score",
            "requested_date", "shipment_deadline",
            "inspector_name", "scheduled_date", "region",
        ]
        display_df = schedule_df[[c for c in display_cols if c in schedule_df.columns]].copy()

        # Translate column names
        col_rename = {
            "request_id": t("col_request_id"),
            "factory_name": t("col_factory_name"),
            "product_line": t("col_product_line"),
            "sku": t("col_sku"),
            "customer_level": t("col_customer_level"),
            "priority": t("col_priority"),
            "priority_score": t("scheduling_score"),
            "requested_date": t("col_requested_date"),
            "shipment_deadline": t("col_shipment_deadline"),
            "inspector_name": t("scheduling_assigned_inspector"),
            "scheduled_date": t("scheduling_assigned_date"),
            "region": t("col_region"),
        }
        display_df = display_df.rename(columns=col_rename)

        # Color-code priority score
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=400,
        )

        # --- Export ---
        excel_buffer = export_dataframe_to_excel(display_df, sheet_name="Schedule")
        st.download_button(
            label=t("scheduling_export"),
            data=excel_buffer,
            file_name=f"inspection_schedule_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # --- Gantt Chart ---
        st.subheader(t("scheduling_gantt"))
        gantt_data = schedule_df.dropna(subset=["scheduled_date"]).copy()

        if not gantt_data.empty:
            # Each inspection is a 1-day task
            gantt_data["start"] = gantt_data["scheduled_date"]
            gantt_data["end"] = gantt_data["scheduled_date"] + timedelta(days=1)
            gantt_data["task"] = gantt_data["factory_name"] + " - " + gantt_data["sku"]

            # Color by priority
            color_map = {"High": "#d62728", "Medium": "#ff7f0e", "Low": "#2ca02c"}

            fig_gantt = px.timeline(
                gantt_data,
                x_start="start",
                x_end="end",
                y="inspector_name",
                color="priority",
                color_discrete_map=color_map,
                hover_data=["factory_name", "sku", "customer_level", "priority_score"],
                title=t("scheduling_gantt"),
                labels={
                    "inspector_name": t("scheduling_assigned_inspector"),
                    "priority": t("col_priority"),
                },
            )
            fig_gantt.update_yaxes(autorange="reversed")
            fig_gantt.update_layout(height=400, showlegend=True)
            st.plotly_chart(fig_gantt, use_container_width=True)
        else:
            st.info("No assigned inspections to display.")

        # --- Inspector Workload Heatmap ---
        st.subheader(t("scheduling_heatmap"))
        workload = get_inspector_workload(schedule_df)

        if not workload.empty:
            # Pivot for heatmap: rows = inspector, cols = date
            pivot = workload.pivot_table(
                index="inspector_name",
                columns="scheduled_date",
                values="count",
                fill_value=0,
                aggfunc="sum",
            )

            # Format column names as dates
            pivot.columns = [c.strftime("%m-%d") if hasattr(c, "strftime") else str(c) for c in pivot.columns]

            fig_heat = go.Figure(data=go.Heatmap(
                z=pivot.values,
                x=pivot.columns,
                y=pivot.index,
                colorscale=[
                    [0, "#f0f0f0"],
                    [0.5, "#ff7f0e"],
                    [1.0, "#d62728"],
                ],
                hoverongaps=False,
                text=pivot.values,
                texttemplate="%{text}",
                zmin=0,
                zmax=max(3, pivot.values.max()),
            ))
            fig_heat.update_layout(
                title=t("scheduling_heatmap"),
                xaxis_title=t("col_inspection_date"),
                yaxis_title=t("col_inspector"),
                height=350,
            )
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("No workload data to display.")

else:
    # Show pending requests summary before generating schedule
    st.subheader(t("scheduling_result_table"))
    pending_count = len(filtered_requests[filtered_requests["status"].isin(["Pending", "Scheduled"])])
    total_count = len(filtered_requests)
    col1, col2, col3 = st.columns(3)
    col1.metric(t("dashboard_pending_requests"), pending_count)
    col2.metric(t("dashboard_total_inspections"), total_count)
    col3.metric(t("filter_factory"), filtered_requests["factory_name"].nunique())

    # Show priority score preview
    if not filtered_requests.empty:
        scored = calculate_priority_score(filtered_requests, personnel_df)
        preview_cols = ["request_id", "factory_name", "product_line", "priority", "priority_score",
                        "requested_date", "shipment_deadline", "customer_level", "status"]
        preview = scored[[c for c in preview_cols if c in scored.columns]].head(20)

        col_rename = {
            "request_id": t("col_request_id"),
            "factory_name": t("col_factory_name"),
            "product_line": t("col_product_line"),
            "priority": t("col_priority"),
            "priority_score": t("scheduling_score"),
            "requested_date": t("col_requested_date"),
            "shipment_deadline": t("col_shipment_deadline"),
            "customer_level": t("col_customer_level"),
            "status": t("col_status"),
        }
        preview = preview.rename(columns=col_rename)
        st.dataframe(preview, use_container_width=True, hide_index=True)
