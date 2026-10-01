"""
Small helpers for writing Power BI PBIR visual.json files.

Used by the page builder scripts in this folder. Each helper returns plain dicts
that follow the published PBIR JSON schemas (visualContainer 2.3.0).
"""

import json
import secrets
from pathlib import Path

VISUAL_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.3.0/schema.json"
MEASURES = "_measures"

INK = "#0B0B0B"
INK_2 = "#52514E"
MUTED = "#898781"
SERIES_1 = "#2A78D6"


def new_name():
    return secrets.token_hex(10)


def lit(value):
    """Literal expression: str -> 'text', bool -> true/false, int -> 12L, float -> 1.5D."""
    if isinstance(value, bool):
        v = "true" if value else "false"
    elif isinstance(value, int):
        v = f"{value}L"
    elif isinstance(value, float):
        v = f"{value}D"
    else:
        v = "'" + str(value).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": v}}}


def color(hex_):
    return {"solid": {"color": lit(hex_)}}


def column(table, name):
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


def measure(name, table=MEASURES):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


def proj(field, display=None):
    kind = "Column" if "Column" in field else "Measure"
    table = field[kind]["Expression"]["SourceRef"]["Entity"]
    prop = field[kind]["Property"]
    p = {"field": field, "queryRef": f"{table}.{prop}", "nativeQueryRef": prop}
    if display:
        p["displayName"] = display
    return p


def container(title=None, subtitle_measure=None, subtitle=None, show_border=True, show_background=True,
              alt_text=None, subtitle_size=9.0):
    o = {}
    if title:
        o["title"] = [{"properties": {"show": lit(True), "text": lit(title)}}]
    else:
        o["title"] = [{"properties": {"show": lit(False)}}]
    if subtitle_measure:
        o["subTitle"] = [{"properties": {"show": lit(True),
                                         "text": {"expr": measure(subtitle_measure)},
                                         "fontColor": color(INK_2), "fontSize": lit(10.0)}}]
    elif subtitle:
        o["subTitle"] = [{"properties": {"show": lit(True), "text": lit(subtitle),
                                         "fontColor": color(INK_2), "fontSize": lit(subtitle_size)}}]
    if not show_border:
        o["border"] = [{"properties": {"show": lit(False)}}]
    if not show_background:
        o["background"] = [{"properties": {"show": lit(False)}}]
    if alt_text:
        o["general"] = [{"properties": {"altText": lit(alt_text)}}]
    return o


def visual(name, x, y, w, h, z, visual_type, query_state=None, sort=None, objects=None, vc_objects=None,
           filters=None):
    v = {"visualType": visual_type}
    if query_state is not None:
        v["query"] = {"queryState": query_state}
        if sort:
            v["query"]["sortDefinition"] = {"sort": sort, "isDefaultSort": False}
    if objects:
        v["objects"] = objects
    if vc_objects:
        v["visualContainerObjects"] = vc_objects
    v["drillFilterOtherVisuals"] = True
    doc = {"$schema": VISUAL_SCHEMA, "name": name,
           "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z},
           "visual": v}
    if filters:
        doc["filterConfig"] = {"filters": filters}
    return doc


def top_n_filter(name, col_table, col_name, by_measure, n):
    """Visual-level Top N filter: keep the n values of a column with the highest measure value."""
    return {
        "name": name,
        "field": column(col_table, col_name),
        "type": "TopN",
        "filter": {
            "Version": 2,
            "From": [
                {"Name": "subquery", "Expression": {"Subquery": {"Query": {
                    "Version": 2,
                    "From": [{"Name": "d", "Entity": col_table, "Type": 0},
                             {"Name": "m", "Entity": MEASURES, "Type": 0}],
                    "Select": [{"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": col_name},
                                "Name": "field"}],
                    "OrderBy": [{"Direction": 2, "Expression": {"Measure": {
                        "Expression": {"SourceRef": {"Source": "m"}}, "Property": by_measure}}}],
                    "Top": n}}}, "Type": 2},
                {"Name": "d", "Entity": col_table, "Type": 0},
            ],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": col_name}}],
                "Table": {"SourceRef": {"Source": "subquery"}}}}}],
        },
    }


def visual_with_sync(doc, group):
    doc["visual"]["syncGroup"] = {"groupName": group, "fieldChanges": True, "filterChanges": True}
    return doc


# ---------------------------------------------------------------------------------------------
# Shared page furniture: every page uses the same header, synced slicers and KPI card style.
# ---------------------------------------------------------------------------------------------

def header(prefix, title, subtitle):
    return visual(
        f"{prefix}_title", 16, 8, 600, 70, 0, "textbox",
        objects={"general": [{"properties": {"paragraphs": [
            {"textRuns": [{"value": title,
                           "textStyle": {"fontSize": "20pt", "fontFamily": "Segoe UI Semibold", "color": INK}}]},
            {"textRuns": [{"value": subtitle, "textStyle": {"fontSize": "10pt", "color": INK_2}}]},
        ]}}]},
        vc_objects=container(show_border=False, show_background=False),
    )


def slicer(name, x, field, display, z, single=False, default=None):
    objects = {"data": [{"properties": {"mode": lit("Dropdown")}}],
               "header": [{"properties": {"fontSize": lit(10.0), "fontColor": color(INK_2)}}]}
    general = {}
    if single:
        objects["selection"] = [{"properties": {"strictSingleSelect": lit(True)}}]
    if default is not None:
        table, col = field["Column"]["Expression"]["SourceRef"]["Entity"], field["Column"]["Property"]
        general["filter"] = {"filter": {
            "Version": 2,
            "From": [{"Name": "d", "Entity": table, "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": col}}],
                "Values": [[lit(default)["expr"]]]}}}]}}
    if general:
        objects["general"] = [{"properties": general}]
    doc = visual(name, x, 8, 200, 68, z, "slicer",
                 query_state={"Values": {"projections": [proj(field, display)]}}, objects=objects)
    return visual_with_sync(doc, f"sync_{display.lower()}")


def standard_slicers(prefix):
    """Year (opens on 2026, can be cleared to All), Region, Segment - synced across all pages."""
    return [
        slicer(f"{prefix}_slicer_year", 632, column("dim_date", "year"), "Year", 1000, default=2026),
        slicer(f"{prefix}_slicer_region", 848, column("dim_customer", "region"), "Region", 2000),
        slicer(f"{prefix}_slicer_segment", 1064, column("dim_customer", "segment"), "Segment", 3000),
    ]


def kpi_cards(prefix, cards, y=84, h=110):
    """cards: list of (measure, title, note_measure or None, static_note or None, display_units, precision)."""
    docs = []
    for i, (m, title, note_measure, static_note, units, precision) in enumerate(cards):
        label = {"fontSize": lit(26.0), "color": color(INK), "labelDisplayUnits": lit(units)}
        if precision is not None:
            label["labelPrecision"] = lit(precision)
        docs.append(visual(
            f"{prefix}_kpi_{i + 1}", 16 + i * 252.8, y, 236.8, h, 4000 + i * 1000, "card",
            query_state={"Values": {"projections": [proj(measure(m))]}},
            objects={"labels": [{"properties": label}],
                     "categoryLabels": [{"properties": {"show": lit(False)}}]},
            vc_objects=container(title=title, subtitle_measure=note_measure, subtitle=static_note, subtitle_size=10.0),
        ))
    return docs


def write(page_dir, doc):
    d = Path(page_dir) / "visuals" / doc["name"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "visual.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return d / "visual.json"
