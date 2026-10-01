"""
Builds the Executive Overview page (PBIR visual.json files).

Layout: 1280 x 720 canvas, 16 px outer margin and gutters.
  row 0  y=8    title + Year / Region / Segment slicers
  row 1  y=84   five KPI cards
  row 2  y=210  Net Sales vs Target trend | YoY growth by category
  row 3  y=440  Net Sales by region       | Top 10 customers

Run from the repo root:  python tools/build_executive_overview.py
"""

import shutil
from pathlib import Path

from pbir import (MUTED, SERIES_1, color, column, container, header, kpi_cards, lit, measure, proj,
                  standard_slicers, top_n_filter, visual, write)

PAGE = Path(__file__).resolve().parent.parent / "B2B_Sales_Analytics.Report/definition/pages/9bb511098c56693e8bc7"


def build():
    visuals_dir = PAGE / "visuals"
    if visuals_dir.exists():
        shutil.rmtree(visuals_dir)

    docs = []

    # --- header, synced slicers, KPI cards --------------------------------------------------------
    docs.append(header("exec", "Executive Overview",
                       "Arka Großhandel GmbH · Net sales in EUR · Data up to 28.09.2026"))
    docs += standard_slicers("exec")
    docs += kpi_cards("exec", [
        ("Net Sales", "Net Sales", "KPI Note Net Sales", None, 1000000.0, 1),
        ("Gross Margin %", "Gross Margin %", "KPI Note Gross Margin", None, 0.0, None),
        ("Target Attainment %", "Target Attainment", "KPI Note Target", None, 0.0, None),
        ("Orders", "Orders", "KPI Note Orders", None, 1.0, None),
        ("Active Customers", "Active Customers", "KPI Note Customers", None, 1.0, None),
    ])

    # --- trend: Net Sales vs Target (one shared axis) ------------------------------------------
    month = column("dim_date", "Month Year")
    docs.append(visual(
        "exec_trend", 16, 210, 800, 214, 9000, "lineChart",
        query_state={"Category": {"projections": [proj(month, "Month")]},
                     "Y": {"projections": [proj(measure("Net Sales")), proj(measure("Sales Target"))]}},
        sort=[{"field": month, "direction": "Ascending"}],
        objects={
            "dataPoint": [
                {"properties": {"fill": color(SERIES_1)}, "selector": {"metadata": "_measures.Net Sales"}},
                {"properties": {"fill": color(MUTED)}, "selector": {"metadata": "_measures.Sales Target"}},
            ],
            "lineStyles": [{"properties": {"lineStyle": lit("dashed")},
                            "selector": {"metadata": "_measures.Sales Target"}}],
            "categoryAxis": [{"properties": {"showAxisTitle": lit(False)}}],
            "valueAxis": [{"properties": {"showAxisTitle": lit(False)}}],
        },
        vc_objects=container(title="Net Sales vs Target by Month",
                             subtitle="Dashed line = monthly sales target",
                             alt_text="Line chart of monthly net sales against the monthly sales target."),
    ))

    # --- YoY growth by category (diverging colour via measure) ----------------------------------
    category = column("dim_product", "category")
    docs.append(visual(
        "exec_yoy_category", 832, 210, 432, 214, 10000, "clusteredBarChart",
        query_state={"Category": {"projections": [proj(category, "Category")]},
                     "Y": {"projections": [proj(measure("Net Sales YoY %"), "Growth vs last year")]}},
        sort=[{"field": measure("Net Sales YoY %"), "direction": "Descending"}],
        objects={
            "dataPoint": [{"properties": {"fill": {"solid": {"color": {"expr": measure("YoY Color")}}}},
                           "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}],
            "labels": [{"properties": {"show": lit(True)}}],
            "categoryAxis": [{"properties": {"showAxisTitle": lit(False)}}],
            "valueAxis": [{"properties": {"showAxisTitle": lit(False), "show": lit(False)}}],
        },
        vc_objects=container(title="Growth vs Last Year by Category",
                             subtitle="Blue = growth · Red = decline",
                             alt_text="Bar chart of net sales growth versus last year for each product category."),
    ))

    # --- Net Sales by region ------------------------------------------------------------------
    region = column("dim_customer", "region")
    docs.append(visual(
        "exec_region", 16, 440, 400, 264, 11000, "clusteredBarChart",
        query_state={"Category": {"projections": [proj(region, "Region")]},
                     "Y": {"projections": [proj(measure("Net Sales"))]}},
        sort=[{"field": measure("Net Sales"), "direction": "Descending"}],
        objects={
            "dataPoint": [{"properties": {"fill": color(SERIES_1)}}],
            "labels": [{"properties": {"show": lit(True), "labelDisplayUnits": lit(1000000.0),
                                       "labelPrecision": lit(1)}}],
            "categoryAxis": [{"properties": {"showAxisTitle": lit(False)}}],
            "valueAxis": [{"properties": {"showAxisTitle": lit(False), "show": lit(False)}}],
        },
        vc_objects=container(title="Net Sales by Region",
                             alt_text="Bar chart of net sales for each sales region."),
    ))

    # --- Top 10 customers ---------------------------------------------------------------------
    docs.append(visual(
        "exec_top_customers", 432, 440, 832, 264, 12000, "tableEx",
        query_state={"Values": {"projections": [
            proj(column("dim_customer", "customer_name"), "Customer"),
            proj(column("dim_customer", "region"), "Region"),
            proj(measure("Net Sales")),
            proj(measure("Net Sales YoY %"), "Growth vs LY"),
            proj(measure("Gross Margin %")),
        ]}},
        sort=[{"field": measure("Net Sales"), "direction": "Descending"}],
        objects={"total": [{"properties": {"totals": lit(False)}}],
                 "values": [{"properties": {"fontSize": lit(9.0)}}],
                 "columnHeaders": [{"properties": {"fontSize": lit(9.0)}}]},
        vc_objects=container(title="Top 10 Customers by Net Sales",
                             alt_text="Table of the ten customers with the highest net sales."),
        filters=[top_n_filter("exec_top10_filter", "dim_customer", "customer_name", "Net Sales", 10)],
    ))

    return [write(PAGE, d) for d in docs]


if __name__ == "__main__":
    for p in build():
        print(p.relative_to(PAGE.parent.parent.parent.parent))
