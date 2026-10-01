"""
Builds the Marketing & Inventory page (PBIR visual.json files).

Questions the page answers: which campaigns pay off, and do we have the right stock?

Layout: 1280 x 720 canvas, 16 px outer margin and gutters.
  row 0  y=8    title + synced Year / Region / Segment slicers
  row 1  y=84   Campaign Spend | Campaign Sales | ROAS | Stock Value | Out-of-Stock Products
  row 2  y=210  campaign table | ROAS by channel
  row 3  y=440  months of cover by category | out-of-stock products by month | stock value by category

Run from the repo root:  python tools/build_marketing_inventory.py
"""

import shutil
from pathlib import Path

from pbir import (SERIES_1, color, column, container, header, kpi_cards, lit, measure, proj, standard_slicers,
                  visual, write)

PAGE = Path(__file__).resolve().parent.parent / "B2B_Sales_Analytics.Report/definition/pages/fef69ec30576a254c459"


def chart(name, x, y, w, h, z, visual_type, category, value, title, alt, subtitle=None, sort_field=None,
          sort_dir="Descending", label_units=None, label_precision=None):
    label = {"show": lit(True)}
    if label_units is not None:
        label["labelDisplayUnits"] = lit(label_units)
    if label_precision is not None:
        label["labelPrecision"] = lit(label_precision)
    return visual(
        name, x, y, w, h, z, visual_type,
        query_state={"Category": {"projections": [category]}, "Y": {"projections": [value]}},
        sort=[{"field": sort_field or value["field"], "direction": sort_dir}],
        objects={"dataPoint": [{"properties": {"fill": color(SERIES_1)}}],
                 "labels": [{"properties": label}],
                 "categoryAxis": [{"properties": {"showAxisTitle": lit(False)}}],
                 "valueAxis": [{"properties": {"showAxisTitle": lit(False), "show": lit(False)}}]},
        vc_objects=container(title=title, subtitle=subtitle, alt_text=alt),
    )


def build():
    visuals_dir = PAGE / "visuals"
    if visuals_dir.exists():
        shutil.rmtree(visuals_dir)

    docs = [header("mkt", "Marketing & Inventory",
                   "Which campaigns pay off, and whether we hold the right stock · EUR")]
    docs += standard_slicers("mkt")
    docs += kpi_cards("mkt", [
        ("Campaign Spend", "Campaign Spend", "KPI Note Budget", None, 1000.0, 0),
        ("Campaign Sales", "Campaign Sales", None, "Sales of promoted products", 1000000.0, 2),
        ("ROAS", "Return on Ad Spend", None, "Campaign sales per € spent", 0.0, None),
        ("Stock Value", "Stock Value", "KPI Note Stock", None, 1000000.0, 2),
        ("Out-of-Stock Products", "Out-of-Stock Products", None, "Zero stock at latest month end", 1.0, None),
    ])

    # --- campaigns ---------------------------------------------------------------------------
    docs.append(visual(
        "mkt_campaigns", 16, 210, 832, 214, 9000, "tableEx",
        query_state={"Values": {"projections": [
            proj(column("dim_campaign", "campaign_name"), "Campaign"),
            proj(column("dim_campaign", "channel"), "Channel"),
            proj(measure("Campaign Budget"), "Budget"),
            proj(measure("Campaign Spend"), "Spend"),
            proj(measure("Clicks")),
            proj(measure("CTR")),
            proj(measure("CPC")),
            proj(measure("Campaign Sales"), "Attributed sales"),
            proj(measure("ROAS")),
        ]}},
        sort=[{"field": measure("ROAS"), "direction": "Descending"}],
        objects={"total": [{"properties": {"totals": lit(False)}}],
                 "values": [{"properties": {"fontSize": lit(9.0)}}],
                 "columnHeaders": [{"properties": {"fontSize": lit(9.0)}}]},
        vc_objects=container(
            title="Campaign Performance",
            subtitle="Attributed sales = net sales of promoted products while the campaign ran (not incremental)",
            alt_text="Table of marketing campaigns with budget, spend, clicks, click-through rate, cost per click, "
                     "attributed sales and return on ad spend."),
    ))

    docs.append(chart(
        "mkt_roas_channel", 864, 210, 400, 214, 10000, "clusteredBarChart",
        proj(column("dim_campaign", "channel"), "Channel"), proj(measure("ROAS")),
        "Return on Ad Spend by Channel", subtitle="Attributed sales per € spent",
        alt="Bar chart of return on ad spend for each marketing channel."))

    # --- inventory -----------------------------------------------------------------------------
    category = column("dim_product", "category")
    docs.append(chart(
        "mkt_cover_category", 16, 440, 400, 264, 11000, "clusteredBarChart",
        proj(category, "Category"), proj(measure("Months of Cover")),
        "Months of Stock Cover by Category", subtitle="Latest month-end stock ÷ average monthly units sold",
        sort_dir="Ascending",
        alt="Bar chart of months of stock cover for each product category, lowest first."))

    month = column("dim_date", "Month Year")
    docs.append(chart(
        "mkt_oos_month", 432, 440, 400, 264, 12000, "clusteredColumnChart",
        proj(month, "Month"), proj(measure("Out-of-Stock Products")),
        "Out-of-Stock Products by Month", subtitle="Products with zero stock at month end",
        sort_field=month, sort_dir="Ascending",
        alt="Column chart of the number of products with zero stock at the end of each month."))

    docs.append(chart(
        "mkt_stock_value", 848, 440, 416, 264, 13000, "clusteredBarChart",
        proj(category, "Category"), proj(measure("Stock Value")),
        "Stock Value by Category", subtitle="Latest month-end stock at list price",
        label_units=1000.0, label_precision=0,
        alt="Bar chart of stock value at list price for each product category."))

    return [write(PAGE, d) for d in docs]


if __name__ == "__main__":
    for p in build():
        print(p.relative_to(PAGE.parent.parent.parent.parent))
