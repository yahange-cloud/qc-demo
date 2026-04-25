"""
Page 2: Factory Quality Dashboard
Multi-dimensional quality analysis with interactive charts.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.helpers import t, init_session_state, format_percentage, format_number
from utils.export import export_dataframe_to_excel
from modules.data_loader import (
    load_inspection_requests,
    load_inspection_reports,
    load_factory_personnel,
    get_factory_list,
)
from modules.dashboard import (
    calc_kpi_summary,
    calc_pass_rate,
    calc_defect_distribution,
    calc_trend,
    calc_factory_ranking,
    calc_aql_switch_status,
    calc_region_summary,
)
from config import COLORS

init_session_state()

st.header(t("dashboard_title"))

# --- Load data ---
requests_df = load_inspection_requests()
reports_df = load_inspection_reports()
personnel_df = load_factory_personnel()

# --- Sidebar filters ---
with st.sidebar:
    st.subheader(t("filter_date_range"))
    min_date = reports_df["inspection_date"].min().date()
    max_date = reports_df["inspection_date"].max().date()
    date_range = st.date_input(
        t("filter_date_range"),
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        label_visibility="collapsed",
    )

    st.subheader(t("filter_region"))
    all_regions = sorted(reports_df["factory_id"].map(
        personnel_df.drop_duplicates("factory_id").set_index("factory_id")["region"]
    ).dropna().unique().tolist())
    selected_regions = st.multiselect(t("filter_region"), all_regions, default=all_regions, label_visibility="collapsed")

    st.subheader(t("filter_product_line"))
    all_product_lines = sorted(reports_df["product_line"].unique().tolist())
    selected_products = st.multiselect(t("filter_product_line"), all_product_lines, default=all_product_lines, label_visibility="collapsed")

    st.subheader(t("filter_factory"))
    factory_region_map = personnel_df.drop_duplicates("factory_id").set_index("factory_id")["region"]
    available_factories = sorted(
        reports_df[
            reports_df["factory_id"].map(factory_region_map).isin(selected_regions)
        ]["factory_id"].map(
            personnel_df.drop_duplicates("factory_id").set_index("factory_id")["factory_name"]
        ).dropna().unique().tolist()
    )
    selected_factories = st.multiselect(t("filter_factory"), available_factories, default=available_factories, label_visibility="collapsed")

# --- Apply filters ---
factory_name_to_id = personnel_df.drop_duplicates("factory_id").set_index("factory_name")["factory_id"]
selected_factory_ids = [factory_name_to_id[fn] for fn in selected_factories if fn in factory_name_to_id.index]

filtered_reports = reports_df.copy()
if len(date_range) == 2:
    start_d, end_d = date_range
    filtered_reports = filtered_reports[
        (filtered_reports["inspection_date"].dt.date >= start_d)
        & (filtered_reports["inspection_date"].dt.date <= end_d)
    ]
filtered_reports = filtered_reports[
    (filtered_reports["factory_id"].isin(selected_factory_ids))
    & (filtered_reports["product_line"].isin(selected_products))
]

# Add factory_name to reports for display
factory_id_to_name = personnel_df.drop_duplicates("factory_id").set_index("factory_id")["factory_name"]
filtered_reports["factory_name"] = filtered_reports["factory_id"].map(factory_id_to_name)

if filtered_reports.empty:
    st.warning("No data matches the current filters.")
    st.stop()

# ============================================================
# KPI Cards
# ============================================================
kpi = calc_kpi_summary(filtered_reports, requests_df)

col1, col2, col3, col4 = st.columns(4)
col1.metric(t("dashboard_total_inspections"), format_number(kpi["total_inspections"]))
col2.metric(t("dashboard_avg_pass_rate"), format_percentage(kpi["avg_pass_rate"]))
col3.metric(t("dashboard_avg_defect_rate"), format_percentage(kpi["avg_defect_rate"]))
col4.metric(t("dashboard_pending_requests"), format_number(kpi["pending_requests"]))

st.divider()

# ============================================================
# Row 1: Pass Rate Bar + Defect Pareto
# ============================================================
chart_col1, chart_col2 = st.columns(2)

# --- Factory Pass Rate Bar Chart ---
with chart_col1:
    st.subheader(t("dashboard_pass_rate_chart"))
    pass_rate_df = calc_pass_rate(filtered_reports, "factory_name")

    fig_pass = go.Figure()
    fig_pass.add_trace(go.Bar(
        y=pass_rate_df["factory_name"],
        x=pass_rate_df["pass_rate"],
        orientation="h",
        marker_color=[
            COLORS["danger"] if r < 80 else COLORS["warning"] if r < 90 else COLORS["success"]
            for r in pass_rate_df["pass_rate"]
        ],
        text=pass_rate_df["pass_rate"].apply(lambda x: f"{x}%"),
        textposition="auto",
        hovertemplate="<b>%{y}</b><br>Pass Rate: %{x}%<br>Total: %{customdata[0]}<extra></extra>",
        customdata=pass_rate_df[["total"]].values,
    ))
    fig_pass.add_vline(x=90, line_dash="dash", line_color="gray", annotation_text="90%")
    fig_pass.update_layout(
        height=400,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="Pass Rate (%)",
        xaxis_range=[0, 105],
    )
    st.plotly_chart(fig_pass, use_container_width=True)

# --- Defect Pareto Chart ---
with chart_col2:
    st.subheader(t("dashboard_defect_pareto"))
    defect_dist = calc_defect_distribution(filtered_reports)

    if not defect_dist.empty:
        fig_pareto = make_subplots(specs=[[{"secondary_y": True}]])
        fig_pareto.add_trace(
            go.Bar(
                x=defect_dist["defect_type"],
                y=defect_dist["count"],
                marker_color=COLORS["primary"],
                name="Count",
                hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>",
            ),
            secondary_y=False,
        )
        fig_pareto.add_trace(
            go.Scatter(
                x=defect_dist["defect_type"],
                y=defect_dist["cumulative_pct"],
                mode="lines+markers",
                marker_color=COLORS["danger"],
                name="Cumulative %",
                hovertemplate="%{y}%<extra></extra>",
            ),
            secondary_y=True,
        )
        fig_pareto.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
        )
        fig_pareto.update_yaxes(title_text="Count", secondary_y=False)
        fig_pareto.update_yaxes(title_text="Cumulative %", range=[0, 110], secondary_y=True)
        st.plotly_chart(fig_pareto, use_container_width=True)
    else:
        st.info("No defect data available.")

# ============================================================
# Row 2: Quality Trend + Factory Radar
# ============================================================
st.divider()
chart_col3, chart_col4 = st.columns(2)

# --- Quality Trend ---
with chart_col3:
    st.subheader(t("dashboard_trend"))
    trend_mode = st.radio(
        "View",
        ["Overall", "By Factory"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if trend_mode == "Overall":
        trend_df = calc_trend(filtered_reports, period="M")
        if not trend_df.empty:
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=trend_df["period"],
                y=trend_df["pass_rate"],
                mode="lines+markers",
                name="Pass Rate",
                line=dict(color=COLORS["success"], width=2),
                hovertemplate="%{x|%Y-%m}<br>Pass Rate: %{y}%<extra></extra>",
            ))
            fig_trend.add_trace(go.Scatter(
                x=trend_df["period"],
                y=trend_df["defect_rate"],
                mode="lines+markers",
                name="Defect Rate",
                line=dict(color=COLORS["danger"], width=2),
                yaxis="y2",
                hovertemplate="%{x|%Y-%m}<br>Defect Rate: %{y}%<extra></extra>",
            ))
            fig_trend.update_layout(
                height=400,
                margin=dict(l=10, r=50, t=10, b=10),
                yaxis=dict(title="Pass Rate (%)", range=[0, 105]),
                yaxis2=dict(title="Defect Rate (%)", overlaying="y", side="right", range=[0, max(15, trend_df["defect_rate"].max() * 1.5)]),
                legend=dict(orientation="h", y=1.1),
            )
            st.plotly_chart(fig_trend, use_container_width=True)
    else:
        trend_df = calc_trend(filtered_reports, period="M", group_by="factory_name")
        if not trend_df.empty:
            fig_trend = px.line(
                trend_df,
                x="period",
                y="pass_rate",
                color="factory_name",
                markers=True,
                labels={"pass_rate": "Pass Rate (%)", "period": "", "factory_name": "Factory"},
            )
            fig_trend.update_layout(
                height=400,
                margin=dict(l=10, r=10, t=10, b=10),
                yaxis_range=[0, 105],
                legend=dict(orientation="h", y=-0.2),
            )
            st.plotly_chart(fig_trend, use_container_width=True)

# --- Factory Radar Chart ---
with chart_col4:
    st.subheader(t("dashboard_radar"))
    ranking_df = calc_factory_ranking(filtered_reports, personnel_df)

    if not ranking_df.empty:
        # Select top factories for radar (max 6 for readability)
        radar_factories = st.multiselect(
            "Select factories",
            ranking_df["factory_name"].tolist(),
            default=ranking_df["factory_name"].head(4).tolist(),
            label_visibility="collapsed",
        )

        if radar_factories:
            radar_data = ranking_df[ranking_df["factory_name"].isin(radar_factories)]
            categories = ["Pass Rate", "Low Defect", "Quality Rating", "Improvement", "Volume"]

            fig_radar = go.Figure()
            for _, row in radar_data.iterrows():
                # Normalize each dimension to 0-100
                values = [
                    min(row["pass_rate"], 100),
                    max(0, 100 - row["defect_rate"] * 10),
                    row["quality_rating"],
                    min(100, max(0, (row["improvement_trend"] + 10) * 5)),
                    min(100, row.get("inspection_count", 0) / max(1, ranking_df["inspection_count"].max()) * 100),
                ]
                fig_radar.add_trace(go.Scatterpolar(
                    r=values + [values[0]],  # close the polygon
                    theta=categories + [categories[0]],
                    name=row["factory_name"],
                    fill="toself",
                    opacity=0.6,
                ))

            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                height=400,
                margin=dict(l=40, r=40, t=10, b=10),
                legend=dict(orientation="h", y=-0.15),
            )
            st.plotly_chart(fig_radar, use_container_width=True)

# ============================================================
# Row 3: Region Map + AQL Status
# ============================================================
st.divider()
chart_col5, chart_col6 = st.columns(2)

# --- Region Quality Map ---
with chart_col5:
    st.subheader(t("dashboard_region_map"))
    region_data = calc_region_summary(filtered_reports, personnel_df)

    if not region_data.empty:
        fig_map = px.choropleth(
            region_data,
            locations="iso_alpha",
            color="pass_rate",
            hover_name="region",
            hover_data={
                "pass_rate": ":.1f",
                "defect_rate": ":.2f",
                "total": True,
                "iso_alpha": False,
            },
            color_continuous_scale=["#d62728", "#ff7f0e", "#2ca02c"],
            range_color=[60, 100],
            labels={"pass_rate": "Pass Rate (%)"},
        )
        fig_map.update_geos(
            visible=True,
            resolution=50,
            showcountries=True,
            countrycolor="lightgray",
            center=dict(lat=20, lon=90),
            projection_scale=2.5,
            lataxis_range=[-5, 45],
            lonaxis_range=[60, 130],
        )
        fig_map.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=0, b=0),
        )
        st.plotly_chart(fig_map, use_container_width=True)

# --- AQL Switch Status ---
with chart_col6:
    st.subheader("AQL Status")
    aql_status = calc_aql_switch_status(filtered_reports)

    if aql_status:
        aql_rows = []
        for fid, info in aql_status.items():
            fname = factory_id_to_name.get(fid, fid)
            aql_rows.append({
                t("col_factory_name"): fname,
                "AQL Status": info["status"],
                "Consecutive Passes": info["consecutive_passes"],
                "Consecutive Fails": info["consecutive_fails"],
            })

        aql_df = pd.DataFrame(aql_rows)

        # Color-coded status display
        def style_status(val):
            if val == "Tightened":
                return "background-color: #ffcccc; color: #d62728; font-weight: bold"
            elif val == "Reduced":
                return "background-color: #ccffcc; color: #2ca02c; font-weight: bold"
            return ""

        styled = aql_df.style.map(style_status, subset=["AQL Status"])
        st.dataframe(styled, use_container_width=True, hide_index=True, height=350)

# ============================================================
# Row 4: Factory Detail Drill-down
# ============================================================
st.divider()
st.subheader(t("dashboard_factory_detail"))

selected_factory = st.selectbox(
    t("filter_factory"),
    options=filtered_reports["factory_name"].unique().tolist(),
    label_visibility="collapsed",
)

if selected_factory:
    factory_reports = filtered_reports[filtered_reports["factory_name"] == selected_factory]

    # Summary metrics
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    f_total = len(factory_reports)
    f_pass = (factory_reports["result"] == "Pass").sum()
    f_fail = (factory_reports["result"] == "Fail").sum()
    f_pass_rate = round(f_pass / f_total * 100, 1) if f_total > 0 else 0

    f_col1.metric(t("dashboard_total_inspections"), f_total)
    f_col2.metric(t("dashboard_avg_pass_rate"), f"{f_pass_rate}%")
    f_col3.metric(t("dashboard_pass"), f_pass)
    f_col4.metric(t("dashboard_fail"), f_fail)

    # Detail table
    detail_cols = [
        "report_id", "inspection_date", "product_line", "sku",
        "sample_size", "total_defects", "critical_defects",
        "major_defects", "minor_defects", "result", "remarks",
    ]
    detail_df = factory_reports[[c for c in detail_cols if c in factory_reports.columns]].copy()
    detail_rename = {
        "report_id": t("col_report_id"),
        "inspection_date": t("col_inspection_date"),
        "product_line": t("col_product_line"),
        "sku": t("col_sku"),
        "sample_size": t("col_sample_size"),
        "total_defects": t("col_total_defects"),
        "critical_defects": t("col_critical_defects"),
        "major_defects": t("col_major_defects"),
        "minor_defects": t("col_minor_defects"),
        "result": t("col_result"),
        "remarks": t("col_remarks"),
    }
    detail_df = detail_df.rename(columns=detail_rename)

    def style_result(val):
        if val == "Fail":
            return "background-color: #ffcccc; color: #d62728; font-weight: bold"
        elif val == "Conditional":
            return "background-color: #fff3cd; color: #856404; font-weight: bold"
        elif val == "Pass":
            return "background-color: #d4edda; color: #155724"
        return ""

    styled_detail = detail_df.style.map(style_result, subset=[t("col_result")])
    st.dataframe(styled_detail, use_container_width=True, hide_index=True)

    # Export detail data
    from datetime import datetime
    excel_buf = export_dataframe_to_excel(
        detail_df, sheet_name=selected_factory,
        title=f"{selected_factory} — {t('dashboard_factory_detail')}"
    )
    st.download_button(
        label=f"📊 {t('report_export_excel')} — {selected_factory}",
        data=excel_buf,
        file_name=f"factory_detail_{selected_factory}_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
