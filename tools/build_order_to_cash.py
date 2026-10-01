"""
Builds the Order-to-Cash page (PBIR visual.json files).

Question the page answers: how fast do we ship, deliver and get paid - and how much money is overdue?

Layout: 1280 x 720 canvas, 16 px outer margin and gutters.
  row 0  y=8    title + synced Year / Region / Segment slicers
  row 1  y=84   Days to Ship | Days to Deliver | On-Time Delivery | Order-to-Cash Days | Overdue Receivables
  row 2  y=210  days per process step | on-time delivery by region | open receivables ageing
  row 3  y=440  days to get paid by payment month | on-time delivery by month

Run from the repo root:  python tools/build_order_to_cash.py
"""

import shutil
from pathlib import Path

from pbir import (SERIES_1, color, column, container, header, kpi_cards, lit, measure, proj, standard_slicers,
                  visual, write)

PAGE = Path(__file__).resolve().parent.parent / "B2B_Sales_Analytics.Report/definition/pages/7c7048b06420e33e4c0d"


def chart(name, x, y, w, h, z, visual_type, category, value, title, alt, subtitle=None, sort_field=None,
          sort_dir="Descending", fill=None, labels=True, hide_value_axis=True, label_units=None):
    objects = {"dataPoint": [fill or {"properties": {"fill": color(SERIES_1)}}],
               "categoryAxis": [{"properties": {"showAxisTitle": lit(False)}}],
               "valueAxis": [{"properties": {"showAxisTitle": lit(False),
                                             **({"show": lit(False)} if hide_value_axis else {})}}]}
    if labels:
        label = {"show": lit(True)}
        if label_units is not None:
            label["labelDisplayUnits"] = lit(label_units)
            label["labelPrecision"] = lit(0)
        objects["labels"] = [{"properties": label}]
    return visual(
        name, x, y, w, h, z, visual_type,
        query_state={"Category": {"projections": [category]}, "Y": {"projections": [value]}},
        sort=[{"field": sort_field or value["field"], "direction": sort_dir}],
        objects=objects,
        vc_objects=container(title=title, subtitle=subtitle, alt_text=alt),
    )


def build():
    visuals_dir = PAGE / "visuals"
    if visuals_dir.exists():
        shutil.rmtree(visuals_dir)

    docs = [header("o2c", "Order-to-Cash",
                   "How fast we ship, deliver and get paid · Receivables in EUR as of 28.09.2026")]
    docs += standard_slicers("o2c")
    docs += kpi_cards("o2c", [
        ("Avg Days to Ship", "Days to Ship", None, "Order → first shipment", 0.0, None),
        ("Avg Days to Deliver", "Days to Deliver", None, "Order → final delivery", 0.0, None),
        ("On-Time Delivery %", "On-Time Delivery", None, "Delivered within 7 days", 0.0, None),
        ("Avg Days Order to Cash", "Order-to-Cash Days", None, "Order → cash received", 0.0, None),
        ("Overdue Receivables As Of", "Overdue Receivables", "KPI Note Overdue", None, 1000.0, 0),
    ])

    step = column("process_step", "Step")
    docs.append(chart(
        "o2c_steps", 16, 210, 400, 214, 9000, "clusteredBarChart",
        proj(step, "Step"), proj(measure("Avg Days in Step"), "Average days"),
        "Where the Time Goes", subtitle="Average days per step · getting paid takes longest",
        sort_field=step, sort_dir="Ascending",
        alt="Bar chart of average days from order to shipment, shipment to delivery, and invoice to payment."))

    docs.append(chart(
        "o2c_otd_region", 432, 210, 400, 214, 10000, "clusteredBarChart",
        proj(column("dim_customer", "region"), "Region"), proj(measure("On-Time Delivery %")),
        "On-Time Delivery by Region", subtitle="Delivered within 7 days · lowest first",
        sort_dir="Ascending",
        alt="Bar chart of the on-time delivery rate for each region, lowest first."))

    bucket = column("receivable_ageing", "Bucket")
    docs.append(chart(
        "o2c_ageing", 848, 210, 416, 214, 11000, "clusteredColumnChart",
        proj(bucket, "Days overdue"), proj(measure("Receivables by Ageing"), "Open receivables"),
        "Open Receivables Ageing", subtitle="All unpaid invoices by days past due date",
        sort_field=bucket, sort_dir="Ascending", label_units=1000.0,
        fill={"properties": {"fill": {"solid": {"color": {"expr": measure("Ageing Color")}}}},
              "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}},
        alt="Column chart of open receivables split into not yet due, 1-30, 31-60, 61-90 and over 90 days "
            "overdue."))

    month = column("dim_date", "Month Year")
    docs.append(chart(
        "o2c_days_to_pay", 16, 440, 624, 264, 12000, "lineChart",
        proj(month, "Month"), proj(measure("Avg Days to Pay by Payment Date"), "Days to get paid"),
        "Days to Get Paid by Month", subtitle="Invoice → payment, by payment month",
        sort_field=month, sort_dir="Ascending", labels=False, hide_value_axis=False,
        alt="Line chart of average days from invoice to payment for each payment month."))

    docs.append(chart(
        "o2c_otd_month", 656, 440, 608, 264, 13000, "lineChart",
        proj(month, "Month"), proj(measure("On-Time Delivery %")),
        "On-Time Delivery by Month", subtitle="Delivered within 7 days, by order month",
        sort_field=month, sort_dir="Ascending", labels=False, hide_value_axis=False,
        alt="Line chart of the monthly on-time delivery rate."))

    return [write(PAGE, d) for d in docs]


if __name__ == "__main__":
    for p in build():
        print(p.relative_to(PAGE.parent.parent.parent.parent))
