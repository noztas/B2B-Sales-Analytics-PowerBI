"""
Builds the Customers page (PBIR visual.json files).

Question the page answers: who are our customers, how dependent are we on the biggest ones,
and who pays late?

Layout: 1280 x 720 canvas, 16 px outer margin and gutters.
  row 0  y=8    title + synced Year / Region / Segment slicers
  row 1  y=84   Active Customers | Net Sales per Customer | Top 20% share | Late Payment % | Open Receivables
  row 2  y=210  customer concentration by tier | net sales by segment | late payment % by segment
  row 3  y=440  customer list (all customers, sortable)

Run from the repo root:  python tools/build_customers.py
"""

import shutil
from pathlib import Path

from pbir import (SERIES_1, color, column, container, header, kpi_cards, lit, measure, proj, standard_slicers,
                  visual, write)

PAGE = Path(__file__).resolve().parent.parent / "B2B_Sales_Analytics.Report/definition/pages/3eac8688b170dcc100a1"


def bar(name, x, y, w, h, z, visual_type, category, value, title, alt, subtitle=None, sort_field=None,
        sort_dir="Descending", units=None, precision=None):
    labels = {"show": lit(True)}
    if units is not None:
        labels["labelDisplayUnits"] = lit(units)
    if precision is not None:
        labels["labelPrecision"] = lit(precision)
    return visual(
        name, x, y, w, h, z, visual_type,
        query_state={"Category": {"projections": [category]}, "Y": {"projections": [value]}},
        sort=[{"field": sort_field or value["field"], "direction": sort_dir}],
        objects={"dataPoint": [{"properties": {"fill": color(SERIES_1)}}],
                 "labels": [{"properties": labels}],
                 "categoryAxis": [{"properties": {"showAxisTitle": lit(False)}}],
                 "valueAxis": [{"properties": {"showAxisTitle": lit(False), "show": lit(False)}}]},
        vc_objects=container(title=title, subtitle=subtitle, alt_text=alt),
    )


def build():
    visuals_dir = PAGE / "visuals"
    if visuals_dir.exists():
        shutil.rmtree(visuals_dir)

    docs = [header("cust", "Customers",
                   "Who buys from us, how concentrated revenue is, and who pays late · Net sales in EUR")]
    docs += standard_slicers("cust")
    docs += kpi_cards("cust", [
        ("Active Customers", "Active Customers", "KPI Note Customers", None, 1.0, None),
        ("Net Sales per Customer", "Net Sales per Customer", None, "Average per active customer", 1.0, None),
        ("Top 20% Customer Share", "Customer Concentration", None, "Net sales from the top 20%", 0.0, None),
        ("Late Payment %", "Late Payments", None, "Paid > 3 days after due date", 0.0, None),
        ("Open Receivables", "Open Receivables", "KPI Note Receivables", None, 1000000.0, 2),
    ])

    tier = column("customer_tier", "Tier")
    docs.append(bar(
        "cust_concentration", 16, 210, 400, 214, 9000, "clusteredColumnChart",
        proj(tier, "Customer tier"), proj(measure("Share of Net Sales")),
        "Customer Concentration", subtitle="Share of net sales by tier (customers ranked by net sales)",
        sort_field=tier, sort_dir="Ascending",
        alt="Column chart showing the share of net sales from the top 10%, next 10%, next 30% and bottom 50% "
            "of customers."))

    segment = column("dim_customer", "segment")
    docs.append(bar(
        "cust_segment_sales", 432, 210, 400, 214, 10000, "clusteredBarChart",
        proj(segment, "Segment"), proj(measure("Net Sales")),
        "Net Sales by Segment", units=1000000.0, precision=1,
        alt="Bar chart of net sales for each customer segment."))

    docs.append(bar(
        "cust_segment_late", 848, 210, 416, 214, 11000, "clusteredBarChart",
        proj(segment, "Segment"), proj(measure("Late Payment %")),
        "Late Payments by Segment", subtitle="Share of paid invoices paid > 3 days late",
        alt="Bar chart of the late payment rate for each customer segment."))

    docs.append(visual(
        "cust_table", 16, 440, 1248, 264, 12000, "tableEx",
        query_state={"Values": {"projections": [
            proj(column("dim_customer", "customer_name"), "Customer"),
            proj(column("dim_customer", "region"), "Region"),
            proj(column("dim_customer", "segment"), "Segment"),
            proj(column("dim_customer", "account_manager"), "Account Manager"),
            proj(measure("Net Sales")),
            proj(measure("Net Sales YoY %"), "Growth vs LY"),
            proj(measure("Gross Margin %")),
            proj(measure("Open Receivables")),
            proj(measure("Late Payment %")),
        ]}},
        sort=[{"field": measure("Net Sales"), "direction": "Descending"}],
        objects={"total": [{"properties": {"totals": lit(False)}}],
                 "values": [{"properties": {"fontSize": lit(9.0)}}],
                 "columnHeaders": [{"properties": {"fontSize": lit(9.0)}}]},
        vc_objects=container(title="All Customers",
                             subtitle="Click a column header to sort · e.g. sort by Open Receivables to find "
                                      "accounts to chase",
                             alt_text="Table of all customers with net sales, growth, margin, open receivables "
                                      "and late payment rate."),
    ))

    return [write(PAGE, d) for d in docs]


if __name__ == "__main__":
    for p in build():
        print(p.relative_to(PAGE.parent.parent.parent.parent))
