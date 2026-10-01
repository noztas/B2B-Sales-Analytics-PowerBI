"""
Builds the Sales & Margin page (PBIR visual.json files).

Question the page answers: where does revenue come from, and how much of it do we keep?

Layout: 1280 x 720 canvas, 16 px outer margin and gutters.
  row 0  y=8    title + synced Year / Region / Segment slicers
  row 1  y=84   Gross Sales -> Discounts -> Net Sales -> Gross Margin -> Units (the revenue bridge)
  row 2  y=210  left:  category / subcategory matrix (y=210..520) + discount % by segment (y=536..704)
                right: margin % by category vs last year (y=210..450) + monthly margin trend (y=466..704)

Run from the repo root:  python tools/build_sales_margin.py
"""

import shutil
from pathlib import Path

from pbir import (MUTED, SERIES_1, color, column, container, header, kpi_cards, lit, measure, proj,
                  standard_slicers, visual, write)

PAGE = Path(__file__).resolve().parent.parent / "B2B_Sales_Analytics.Report/definition/pages/c390280d000907238b47"


def series_colors(current, previous):
    """Current period in series blue, comparison period in muted grey (emphasis, not a second category)."""
    return [
        {"properties": {"fill": color(SERIES_1)}, "selector": {"metadata": f"_measures.{current}"}},
        {"properties": {"fill": color(MUTED)}, "selector": {"metadata": f"_measures.{previous}"}},
    ]


def no_axis_titles(hide_value_axis=False):
    value = {"showAxisTitle": lit(False)}
    if hide_value_axis:
        value["show"] = lit(False)
    return {"categoryAxis": [{"properties": {"showAxisTitle": lit(False)}}],
            "valueAxis": [{"properties": value}]}


def build():
    visuals_dir = PAGE / "visuals"
    if visuals_dir.exists():
        shutil.rmtree(visuals_dir)

    docs = [header("sales", "Sales & Margin",
                   "Where revenue comes from and how much of it we keep · Net sales in EUR")]
    docs += standard_slicers("sales")

    # --- revenue bridge: gross -> discounts -> net -> margin ---------------------------------------
    docs += kpi_cards("sales", [
        ("Gross Sales", "Gross Sales", None, "Before discounts", 1000000.0, 1),
        ("Discount Amount", "Discounts", "KPI Note Discount", None, 1000000.0, 1),
        ("Net Sales", "Net Sales", "KPI Note Net Sales", None, 1000000.0, 1),
        ("Gross Margin", "Gross Margin", "KPI Note Margin Value", None, 1000000.0, 1),
        ("Units Sold", "Units Sold", "KPI Note Units", None, 1.0, None),
    ])

    # --- category / subcategory matrix --------------------------------------------------------
    docs.append(visual(
        "sales_matrix", 16, 210, 624, 310, 9000, "pivotTable",
        query_state={
            "Rows": {"projections": [proj(column("dim_product", "category"), "Category"),
                                     proj(column("dim_product", "subcategory"), "Subcategory")]},
            "Values": {"projections": [proj(measure("Net Sales")),
                                       proj(measure("Net Sales YoY %"), "Growth vs LY"),
                                       proj(measure("Gross Margin %")),
                                       proj(measure("Discount %"))]},
        },
        sort=[{"field": measure("Net Sales"), "direction": "Descending"}],
        objects={"values": [{"properties": {"fontSize": lit(12.0)}}],
                 "columnHeaders": [{"properties": {"fontSize": lit(12.0)}}],
                 "rowHeaders": [{"properties": {"fontSize": lit(12.0)}}]},
        vc_objects=container(title="Performance by Category",
                             subtitle="Expand a category (+) to see its subcategories",
                             alt_text="Matrix of net sales, growth, gross margin and discount rate by product "
                                      "category and subcategory."),
    ))

    # --- discount % by segment ----------------------------------------------------------------
    docs.append(visual(
        "sales_discount_segment", 16, 536, 624, 168, 10000, "clusteredBarChart",
        query_state={"Category": {"projections": [proj(column("dim_customer", "segment"), "Segment")]},
                     "Y": {"projections": [proj(measure("Discount %"))]}},
        sort=[{"field": measure("Discount %"), "direction": "Descending"}],
        objects={"dataPoint": [{"properties": {"fill": color(SERIES_1)}}],
                 "labels": [{"properties": {"show": lit(True)}}],
                 **no_axis_titles(hide_value_axis=True)},
        vc_objects=container(title="Discount Rate by Customer Segment",
                             alt_text="Bar chart of discounts as a share of gross sales for each customer segment."),
    ))

    # --- margin % by category, this year vs last year -------------------------------------------
    docs.append(visual(
        "sales_margin_category", 656, 210, 608, 240, 11000, "clusteredBarChart",
        query_state={"Category": {"projections": [proj(column("dim_product", "category"), "Category")]},
                     "Y": {"projections": [proj(measure("Gross Margin %"), "This year"),
                                           proj(measure("Gross Margin % PY"), "Last year")]}},
        sort=[{"field": measure("Gross Margin %"), "direction": "Descending"}],
        objects={"dataPoint": series_colors("Gross Margin %", "Gross Margin % PY"),
                 "labels": [{"properties": {"show": lit(True)}}],
                 **no_axis_titles(hide_value_axis=True)},
        vc_objects=container(title="Gross Margin % by Category",
                             subtitle="Blue = this year · Grey = same period last year",
                             alt_text="Bar chart comparing gross margin percentage by category with last year."),
    ))

    # --- monthly margin trend --------------------------------------------------------------------
    month = column("dim_date", "Month Year")
    docs.append(visual(
        "sales_margin_trend", 656, 466, 608, 238, 12000, "lineChart",
        query_state={"Category": {"projections": [proj(month, "Month")]},
                     "Y": {"projections": [proj(measure("Gross Margin %"), "This year"),
                                           proj(measure("Gross Margin % PY"), "Last year")]}},
        sort=[{"field": month, "direction": "Ascending"}],
        objects={"dataPoint": series_colors("Gross Margin %", "Gross Margin % PY"),
                 **no_axis_titles()},
        vc_objects=container(title="Gross Margin % by Month",
                             subtitle="Blue = this year · Grey = same month last year",
                             alt_text="Line chart of monthly gross margin percentage against the same month "
                                      "last year."),
    ))

    return [write(PAGE, d) for d in docs]


if __name__ == "__main__":
    for p in build():
        print(p.relative_to(PAGE.parent.parent.parent.parent))
