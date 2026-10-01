"""
Synthetic data generator for the B2B Sales Analytics Power BI project.

Produces data/raw_tables.xlsx with the same sheets, columns and deliberate
data-quality issues as the original course workbook, scaled up to a
realistic DACH (Germany / Austria / Switzerland) wholesale business:
Arka Großhandel GmbH, a fictional mid-sized distributor.

All companies, people, emails and phone numbers are fictional.
Emails use the reserved .example TLD.

Usage:
    python generator/generate_data.py            # default seed 2026
    python generator/generate_data.py --seed 7 --orders 30000
"""

import argparse
import hashlib
import math
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from openpyxl import Workbook

START = date(2025, 1, 1)
END = date(2026, 9, 28)

# ---------------------------------------------------------------- geography
REGIONS = {
    # region: (share of customers, country, cities)
    "Süd":        (0.26, "DE", ["München", "Stuttgart", "Nürnberg", "Augsburg", "Karlsruhe", "Regensburg"]),
    "West":       (0.24, "DE", ["Köln", "Düsseldorf", "Dortmund", "Essen", "Frankfurt am Main", "Bonn"]),
    "Nord":       (0.14, "DE", ["Hamburg", "Bremen", "Hannover", "Kiel"]),
    "Ost":        (0.12, "DE", ["Berlin", "Leipzig", "Dresden", "Magdeburg"]),
    "Österreich": (0.13, "AT", ["Wien", "Graz", "Linz", "Salzburg"]),
    "Schweiz":    (0.11, "CH", ["Zürich", "Basel", "Bern", "Genf"]),
}
PHONE_PREFIX = {"DE": "+49", "AT": "+43", "CH": "+41"}
REGIONAL_HEADS = {
    "Süd": "katharina.huber", "West": "jonas.becker", "Nord": "lena.petersen",
    "Ost": "felix.wagner", "Österreich": "florian.gruber", "Schweiz": "nina.meier",
}
ACCOUNT_MANAGERS = {
    "Süd": ["Thomas Maier", "Sabine Wolf"], "West": ["Markus Schmitz", "Julia Klein"],
    "Nord": ["Jan Hansen", "Anna Vogt"], "Ost": ["Sebastian Krüger", "Laura Richter"],
    "Österreich": ["Stefan Hofer", "Elisabeth Bauer"], "Schweiz": ["Lukas Keller", "Sarah Brunner"],
}

# ---------------------------------------------------------------- products
CATEGORIES = {
    # category: (subcategories, price range EUR, cost ratio, 2026 growth)
    "electronics": (["phones", "laptops", "audio"], (60, 1400), 0.78, 1.10),
    "apparel":     (["mens", "womens", "kids"], (8, 120), 0.52, 0.88),
    "home":        (["kitchen", "furniture", "decor"], (12, 650), 0.58, 0.98),
    "sports":      (["fitness", "outdoor", "team"], (10, 480), 0.60, 1.02),
    "beauty":      (["skincare", "makeup", "fragrance"], (5, 90), 0.45, 1.05),
    "industrial":  (["tools", "safety", "fasteners"], (5, 600), 0.63, 1.12),
}
CODE_PREFIX = {"electronics": "ELE", "apparel": "APP", "home": "HOM",
               "sports": "SPO", "beauty": "BEA", "industrial": "IND"}
BRANDS = ["Acme", "Globex", "Initech", "Umbra", "Stark", "Wayne", "Soylent", "Hooli", "Vanta", "Lumen",
          "Nordlicht", "Alpenwerk", "Rheinform", "Elbtal"]
SUPPLIERS = ["Rheintal Components GmbH", "Hanse Import KG", "Alpina Supply AG", "Bavaria Trade GmbH",
             "Westfalen Logistik GmbH", "Donau Distribution GmbH", "Sächsische Werke AG", "Helvetia Parts AG",
             "Nordsee Handel GmbH", "Schwarzwald Tools GmbH", "Main-Franken Textil GmbH", "Ruhr Industriebedarf KG",
             "Asia Pacific Sourcing Ltd", "EuroTech Distribution BV", "Iberia Goods SL"]
DESCRIPTIONS = [
    "Imported item, refer to the supplier datasheet for full specifications and warranty terms.",
    "One of the stronger sellers in its category, frequently bundled with accessories at checkout.",
    "Older catalog line being phased out, only limited stock remains in the central warehouse.",
    "Private-label product, produced to our specification by a certified partner factory.",
    "CE-certified, compliant with current EU product safety regulations.",
    "Bulk packaging available on request for orders above 50 units.",
    None,
]

# ---------------------------------------------------------------- customers
NAME_A = ["Alpen", "Rhein", "Nord", "Süd", "Hanse", "Donau", "Elb", "Main", "Isar", "Neckar", "Weser", "Spree",
          "Bavaria", "Westfalen", "Schwaben", "Franken", "Helvetia", "Tirol", "Harz", "Eifel", "Mosel", "Ruhr",
          "Boden", "Oder", "Havel", "Taunus", "Allgäu", "Sauerland", "Vogtland", "Lausitz", "Kärnten", "Steiermark",
          "Linden", "Eichen", "Birken", "Falken", "Adler", "Stern", "Sonnen", "Berg", "Tal", "Wald", "See", "Brücken",
          "Meridian", "Vertex", "Cascade", "Nova", "Quantum", "Pioneer", "Summit", "Momentum", "Horizon", "Catalyst"]
NAME_B = ["Handel", "Technik", "Bau", "Werk", "Service", "Logistik", "Vertrieb", "Systeme", "Industrie", "Bedarf",
          "Markt", "Versand", "Office", "Einrichtung", "Sport", "Mode", "Kosmetik", "Elektro", "Haus", "Gastro",
          "Solutions", "Trading", "Retail", "Supply", "Partners", "Distribution", "Group", "Commerce"]
LEGAL = {"DE": ["GmbH", "GmbH", "GmbH", "GmbH & Co. KG", "AG", "KG", "e.K."],
         "AT": ["GmbH", "GmbH", "AG", "KG", "OG"],
         "CH": ["AG", "AG", "GmbH", "SA"]}
SEGMENTS = [("Enterprise", 0.14), ("Mid-Market", 0.38), ("SMB", 0.48)]
SEGMENT_ORDER_WEIGHT = {"Enterprise": 4.5, "Mid-Market": 2.4, "SMB": 1.0}
CREDIT = {"Enterprise": [100000, 250000, 500000], "Mid-Market": [25000, 50000, 100000], "SMB": [5000, 10000, 25000]}
TERMS = {"Enterprise": [("Net 60", .45), ("Net 30", .45), ("Net 15", .10)],
         "Mid-Market": [("Net 30", .60), ("Net 15", .20), ("Net 60", .15), ("Prepaid", .05)],
         "SMB": [("Net 30", .40), ("Net 15", .25), ("Prepaid", .35)]}
TERM_DAYS = {"Prepaid": 0, "Net 15": 15, "Net 30": 30, "Net 60": 60}
FIRST = ["Lukas", "Leon", "Finn", "Paul", "Jonas", "Elias", "Felix", "Max", "Tobias", "Daniel", "Michael", "Andreas",
         "Stefan", "Christian", "Mehmet", "Luca", "Marco", "David", "Emma", "Mia", "Hannah", "Lea", "Sophie", "Lina",
         "Marie", "Laura", "Julia", "Anna", "Sarah", "Katrin", "Claudia", "Ayşe", "Elif", "Nora", "Clara", "Johanna"]
LAST = ["Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Wagner", "Becker", "Schulz", "Hoffmann",
        "Koch", "Richter", "Klein", "Wolf", "Schröder", "Neumann", "Schwarz", "Zimmermann", "Braun", "Hofmann",
        "Hartmann", "Lange", "Werner", "Krause", "Lehmann", "Köhler", "Maier", "Huber", "Gruber", "Keller",
        "Yılmaz", "Kaya", "Nowak", "Rossi", "Brunner", "Steiner"]
STREETS = ["Hauptstraße", "Bahnhofstraße", "Industriestraße", "Gewerbepark", "Am Hafen", "Lindenallee",
           "Schillerstraße", "Goethestraße", "Rheinweg", "Marktplatz", "Friedrichstraße", "Werkstraße",
           "Kirchgasse", "Mühlenweg", "Bergstraße", "Ringstraße", "Gartenstraße", "Poststraße"]

CHANNELS = [(10, .30), (20, .18), (30, .34), (40, .18)]   # Online Store, Retail Partner, Wholesale, Field Sale
NOTES = [
    (None, .62),
    ("Customer requested delivery before noon; confirm the slot by phone the day before.", .09),
    ("Fragile items on this order, add extra padding and mark the box clearly.", .08),
    ("Partial backorder is possible, keep the customer updated on remaining stock.", .08),
    ("VIP account, expedite handling and notify the account manager once it ships.", .07),
    ("Delivery to loading dock only, forklift available Mon-Fri 7-15.", .06),
]
MONTH_SEASON = {1: .85, 2: .95, 3: 1.06, 4: 1.00, 5: 1.00, 6: .97, 7: .90, 8: .78, 9: 1.05, 10: 1.10, 11: 1.22, 12: .88}

CAMPAIGNS = [
    # name, channel, start, end, budget
    ("Frühjahrsaktion 2025", "Email", "2025-03-03", "2025-03-31", 9000),
    ("LinkedIn Einkäufer Q2", "LinkedIn", "2025-04-07", "2025-05-18", 18000),
    ("Sommer Sale B2B", "Paid Search", "2025-06-16", "2025-07-13", 22000),
    ("Back to School", "Display", "2025-08-18", "2025-09-12", 9500),
    ("Messe Nachfass 2025", "Email", "2025-09-22", "2025-10-10", 6000),
    ("Industrie Woche", "LinkedIn", "2025-10-13", "2025-10-31", 14000),
    ("Black Friday B2B", "Paid Search", "2025-11-24", "2025-12-01", 30000),
    ("Jahresendspurt", "Email", "2025-12-01", "2025-12-19", 5000),
    ("Neujahr Räumungsverkauf", "Email", "2026-01-05", "2026-01-23", 7000),
    ("Frühjahrsaktion 2026", "Social", "2026-03-02", "2026-03-31", 12000),
    ("LinkedIn Einkäufer 2026", "LinkedIn", "2026-04-13", "2026-05-24", 20000),
    ("Sommer Sale B2B 2026", "Paid Search", "2026-06-15", "2026-07-12", 25000),
    ("Back to School 2026", "Display", "2026-08-17", "2026-09-11", 10000),
]
CTR = {"Email": (.02, .045), "LinkedIn": (.004, .009), "Paid Search": (.03, .06), "Display": (.001, .003),
       "Social": (.006, .012)}
CPC = {"Email": .25, "LinkedIn": 5.5, "Paid Search": 1.6, "Display": .9, "Social": 1.1}

HOLIDAYS = {(1, 1), (5, 1), (10, 3), (12, 24), (12, 25), (12, 26), (12, 31)}


def pick(rng, weighted):
    r, acc = rng.random(), 0.0
    for value, w in weighted:
        acc += w
        if r <= acc:
            return value
    return weighted[-1][0]


def md5(s):
    return hashlib.md5(str(s).encode()).hexdigest()


def add_business_days(d, n):
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5 and (d.month, d.day) not in HOLIDAYS:
            n -= 1
    return d


def poisson(rng, lam):
    if lam > 30:
        return max(0, round(rng.gauss(lam, math.sqrt(lam))))
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= L:
            return k
        k += 1


def slug(name):
    s = name.lower()
    for a, b in {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "ı": "i", "ş": "s", "&": "und", ".": ""}.items():
        s = s.replace(a, b)
    return "-".join(p for p in s.split() if p not in ("gmbh", "ag", "kg", "co", "und", "ek", "og", "sa"))


def email_part(s):
    return slug(s).replace("-", "")


def generate(seed, n_orders_target, n_customers):
    rng = random.Random(seed)

    # ------------------------------------------------------------ cities
    cities = [(c, r) for r, (_, _, cs) in REGIONS.items() for c in cs]
    country_of = {c: REGIONS[r][1] for c, r in cities}

    # ------------------------------------------------------------ products
    products = []   # dicts
    pid = 0
    for cat, (subs, (lo, hi), cost_ratio, growth) in CATEGORIES.items():
        for sub in subs:
            for _ in range(rng.randint(19, 26)):
                pid += 1
                price = round(math.exp(rng.uniform(math.log(lo), math.log(hi))), 2)
                products.append({
                    "code": f"{CODE_PREFIX[cat]}-{pid:03d}", "name": f"{sub.title()} M{pid:03d}",
                    "brand": rng.choice(BRANDS), "sub": sub.title(), "cat": cat, "price": price,
                    "supplier": rng.choice(SUPPLIERS), "desc": rng.choice(DESCRIPTIONS),
                    "cost_ratio": min(.92, max(.3, rng.gauss(cost_ratio, .06))), "growth": growth,
                    "pop": 1 / (rng.random() * 30 + 1) ** .9,   # long-tail popularity
                    "launch": START if rng.random() > .08 else START + timedelta(days=rng.randint(120, 540)),
                })
    by_cat = defaultdict(list)
    for p in products:
        by_cat[p["cat"]].append(p)

    # ------------------------------------------------------------ customers
    customers, used = [], set()
    region_weights = [(r, v[0]) for r, v in REGIONS.items()]
    for i in range(n_customers):
        region = pick(rng, region_weights)
        country = REGIONS[region][1]
        city = rng.choice(REGIONS[region][2])
        while True:
            name = f"{rng.choice(NAME_A)} {rng.choice(NAME_B)} {rng.choice(LEGAL[country])}"
            if name not in used:
                used.add(name)
                break
        seg = pick(rng, SEGMENTS)
        start = START - timedelta(days=1) if rng.random() < .8 else START + timedelta(days=rng.randint(30, 600))
        churn = END + timedelta(days=1) if rng.random() > .09 else START + timedelta(days=rng.randint(200, 620))
        payer = pick(rng, [("punctual", .62), ("skonto", .10), ("slow", .20), ("late", .08)])
        customers.append({
            "id": 1001 + i, "name": name, "seg": seg, "region": region, "country": country, "city": city,
            "am": rng.choice(ACCOUNT_MANAGERS[region]), "terms": pick(rng, TERMS[seg]),
            "credit": rng.choice(CREDIT[seg]), "start": start, "churn": churn, "payer": payer,
            "fav": rng.sample(list(CATEGORIES), rng.randint(1, 3)),
            "weight": SEGMENT_ORDER_WEIGHT[seg] * rng.lognormvariate(0, .45),
            "addr": i + 1,
        })

    # ------------------------------------------------------------ campaigns
    camp = []
    for name, ch, s, e, budget in CAMPAIGNS:
        s, e = date.fromisoformat(s), date.fromisoformat(e)
        cats = rng.sample(list(CATEGORIES), 2)
        promoted = rng.sample([p for c in cats for p in by_cat[c]], rng.randint(6, 12))
        camp.append({"name": name, "ch": ch, "s": s, "e": e, "budget": budget, "promoted": promoted})

    # ------------------------------------------------------------ orders
    days = [START + timedelta(d) for d in range((END - START).days + 1)]
    work_days = [d for d in days if d.weekday() < 5 and (d.month, d.day) not in HOLIDAYS]
    base_weight = {d: MONTH_SEASON[d.month] * (1.03 if d.year == 2026 else 1.0) for d in work_days}
    lam_per_unit = n_orders_target / sum(base_weight.values())

    orders, lines = [], []
    line_no = 0
    for d in days:
        if d.weekday() == 6 or (d.month, d.day) in HOLIDAYS:
            continue
        lam = lam_per_unit * (base_weight.get(d, 0) if d.weekday() < 5 else .04 * MONTH_SEASON[d.month])
        n = poisson(rng, lam)
        if not n:
            continue
        active = [c for c in customers if c["start"] <= d < c["churn"]]
        weights = [c["weight"] for c in active]
        live_camps = [c for c in camp if c["s"] <= d <= c["e"]]
        for c in rng.choices(active, weights=weights, k=n):
            oid = f"ORD{len(orders) + 1:05d}"
            ts = datetime(d.year, d.month, d.day, rng.randint(7, 17), rng.randint(0, 59), rng.randint(0, 59))
            n_lines = pick(rng, [(1, .22), (2, .28), (3, .22), (4, .14), (5, .08), (6, .06)])
            if c["seg"] == "Enterprise":
                n_lines += rng.randint(0, 3)
            chosen = set()
            order_total = 0.0
            for _ in range(n_lines):
                if live_camps and rng.random() < .10:
                    p = rng.choice(rng.choice(live_camps)["promoted"])
                else:
                    cat = rng.choice(c["fav"]) if rng.random() < .6 else rng.choice(list(CATEGORIES))
                    pool = [p for p in by_cat[cat] if p["launch"] <= d]
                    p = rng.choices(pool, weights=[x["pop"] for x in pool])[0]
                if p["code"] in chosen:
                    continue
                chosen.add(p["code"])
                promo = any(p in lc["promoted"] for lc in live_camps)
                base_qty = max(1, round(rng.lognormvariate(math.log(max(1.2, 32 / p["price"] ** .45)), .6)))
                qty = base_qty * {"Enterprise": 1.9, "Mid-Market": 1.3, "SMB": 1.0}[c["seg"]]
                if d.year == 2026:
                    qty *= p["growth"]      # category demand trend
                qty = max(1, int(qty) + (rng.random() < qty % 1))   # stochastic rounding keeps the trend
                unit_price = round(p["price"] * (1.025 if d.year == 2026 else 1.0) * rng.uniform(.98, 1.02), 2)
                disc = {"Enterprise": [.05, .10, .15], "Mid-Market": [0, .05, .10], "SMB": [0, 0, .05]}[c["seg"]]
                discount = rng.choice(disc)
                if promo:
                    discount = min(.15, discount + .05)
                line_total = round(qty * unit_price * (1 - discount), 2)
                order_total += line_total
                line_no += 1
                lines.append({"LineID": f"L{line_no:05d}", "OrderID": oid, "ProductName": p["name"],
                              "Quantity": qty, "UnitPrice": unit_price,
                              "UnitCost": round(p["price"] * p["cost_ratio"], 2),
                              "DiscountPct": discount, "LineTotal": line_total, "_p": p, "_d": d})
            ship_city = c["city"] if rng.random() < .75 else rng.choice(REGIONS[c["region"]][2])
            bill_city = c["city"] if rng.random() < .93 else rng.choice(REGIONS[c["region"]][2])
            orders.append({"OrderID": oid, "CustomerName": c["name"], "CustomerCity": c["city"],
                           "RegionName": c["region"], "ShipToCity": ship_city, "BillToCity": bill_city,
                           "OrderDate": ts, "OrderChannel": pick(rng, CHANNELS), "Priority":
                           "Express" if rng.random() < .24 else "Standard", "OrderTotal": round(order_total, 2),
                           "OrderNotes": pick(rng, NOTES), "_c": c, "_d": d})

    # ------------------------------------------------------------ order-to-cash
    shipments, invoices, invoice_lines, payments = [], [], [], []
    lines_by_order = defaultdict(list)
    for ln in lines:
        lines_by_order[ln["OrderID"]].append(ln)
    for o in orders:
        c, d = o["_c"], o["_d"]
        backorder = rng.random() < .07
        ship = add_business_days(d, (0 if o["Priority"] == "Express" else rng.randint(1, 2)) +
                                 (rng.randint(3, 8) if backorder else 0))
        mode = "Express" if o["Priority"] == "Express" else ("Freight" if o["OrderTotal"] > 6000 else "Parcel")
        transit = {"Express": 1, "Parcel": rng.randint(1, 3), "Freight": rng.randint(2, 5)}[mode]
        transit += {"DE": 0, "AT": rng.randint(0, 1), "CH": rng.randint(1, 3)}[c["country"]]   # CH customs
        deliv = add_business_days(ship, transit)
        if ship > END:
            o["Status"] = "Processing"
            continue
        o["Status"] = "Delivered" if deliv <= END else "Shipped"
        shipments.append({"OrderID": o["OrderID"], "ShipMode": mode, "ShipDate": ship,
                          "DeliveryDate": deliv if deliv <= END else None})
        if backorder and rng.random() < .6:     # split delivery -> duplicate OrderID in shipments
            ship2 = add_business_days(ship, rng.randint(2, 6))
            deliv2 = add_business_days(ship2, transit)
            if ship2 <= END:
                shipments.append({"OrderID": o["OrderID"], "ShipMode": mode, "ShipDate": ship2,
                                  "DeliveryDate": deliv2 if deliv2 <= END else None})
        inv_date = ship if c["terms"] != "Prepaid" else d
        inv_id = f"INV{len(invoices) + 1:05d}"
        invoices.append({"InvoiceID": inv_id, "OrderID": o["OrderID"], "CustomerName": c["name"],
                         "InvoiceDate": inv_date, "Amount": o["OrderTotal"]})
        for ln in lines_by_order[o["OrderID"]]:
            invoice_lines.append({"InvoiceLineID": f"IL{len(invoice_lines) + 1:05d}", "InvoiceID": inv_id,
                                  "ProductName": ln["ProductName"], "Amount": ln["LineTotal"]})
        due = inv_date + timedelta(days=TERM_DAYS[c["terms"]])
        if c["terms"] == "Prepaid":
            pay = d + timedelta(days=rng.randint(0, 1))
        else:
            delay = {"punctual": rng.randint(-4, 3), "skonto": -(TERM_DAYS[c["terms"]] - rng.randint(7, 10)),
                     "slow": rng.randint(4, 25), "late": rng.randint(20, 75)}[c["payer"]]
            pay = due + timedelta(days=delay)
        if pay <= END and rng.random() > .004:   # a few invoices are never paid
            payments.append({"PaymentID": f"PAY{len(payments) + 1:05d}", "InvoiceID": inv_id,
                             "CustomerName": c["name"], "PayDate": pay, "Amount": o["OrderTotal"]})
    shipments.sort(key=lambda s: (s["OrderID"], s["ShipDate"]))
    for i, s in enumerate(shipments, 1):
        s["ShipmentID"] = f"SHP{i:05d}"

    # ------------------------------------------------------------ targets (plan set before the year)
    actual_month = defaultdict(float)
    for ln in lines:
        actual_month[ln["_d"].strftime("%Y-%m")] += ln["LineTotal"]
    targets = []
    for m in sorted(actual_month):
        y, mo = int(m[:4]), int(m[5:])
        if y == 2025:
            plan = actual_month[m] * rng.uniform(.93, 1.07)
        else:
            plan = actual_month.get(f"2025-{mo:02d}", actual_month[m]) * rng.uniform(1.08, 1.14)
        if m == END.strftime("%Y-%m"):       # current month: full-month plan
            plan = actual_month.get(f"2025-{mo:02d}", 0) * 1.11
        targets.append((m, int(round(plan, -3))))

    # ------------------------------------------------------------ inventory (month-end stock, wide format)
    months = sorted({(d.year, d.month) for d in days})
    sold = defaultdict(int)
    for ln in lines:
        sold[(ln["_p"]["code"], ln["_d"].year, ln["_d"].month)] += ln["Quantity"]
    inventory = []
    for p in products:
        avg = max(5, sum(v for k, v in sold.items() if k[0] == p["code"]) / len(months))
        policy = rng.choice([1.0, 1.5, 2.0, 3.0])     # months of cover the buyer aims for
        target = avg * policy
        stock = round(target)
        row = [p["name"]]
        for y, mo in months:
            # order-up-to policy: refill to target plus expected demand; 12% of reorders are missed (supply gaps)
            reorder = round(max(0, target + avg - stock) * rng.uniform(.7, 1.15)) if rng.random() > .12 else 0
            stock = max(0, stock + reorder - sold[(p["code"], y, mo)])
            row.append(stock)
        inventory.append(row)

    return locals()


def write_workbook(g, path):
    rng = random.Random(1)
    wb = Workbook(write_only=True)

    def sheet(name, header, rows):
        ws = wb.create_sheet(name)
        ws.append(header)
        for r in rows:
            ws.append(list(r))

    sheet("Address", ["AddressID", "Street", "CityName"],
          [(c["addr"], f"{rng.choice(STREETS)} {rng.randint(1, 180)}", c["city"]) for c in g["customers"]])

    camp_rows = []
    for cp in g["camp"]:
        n_days = (cp["e"] - cp["s"]).days + 1
        daily = cp["budget"] * rng.uniform(.85, 1.02) / n_days
        for k in range(n_days):
            d = cp["s"] + timedelta(k)
            spend = round(daily * rng.uniform(.6, 1.4) * (.55 if d.weekday() >= 5 else 1), 2)
            clicks = max(1, round(spend / (CPC[cp["ch"]] * rng.uniform(.7, 1.3))))
            impressions = round(clicks / rng.uniform(*CTR[cp["ch"]]))
            camp_rows.append((cp["name"], cp["ch"], cp["s"].isoformat(), cp["e"].isoformat(), cp["budget"],
                              d.isoformat(), impressions, clicks, spend))
    sheet("CAMPAIGN_LOG", ["CampaignName", "Channel", "StartDate", "EndDate", "Budget", "Date",
                           "Impressions", "Clicks", "Spend"], camp_rows)

    cust_rows = [(c["id"], c["name"], c["seg"], c["addr"], c["am"], c["terms"], md5(c["id"]), f"SAP-{200000 + i}")
                 for i, c in enumerate(g["customers"])]
    cust_rows.insert(rng.randint(5, 50), (9999, "TEST ACCOUNT", "SMB", None, "TEST", "Prepaid", None, None))
    sheet("CUST_MASTER", ["CustomerID", "CustomerName", "Segment", "AddressID", "AccountManager",
                          "PaymentTerms", "hash_key", "source_id"], cust_rows)

    sheet("INVOICES", ["InvoiceID", "OrderID", "CustomerName", "InvoiceDate", "Amount"],
          [(i["InvoiceID"], i["OrderID"], i["CustomerName"], i["InvoiceDate"].isoformat(), i["Amount"])
           for i in g["invoices"]])

    def order_row(o, legacy):
        base = [o["OrderID"]] + ([f"LR-{o['OrderID']}"] if legacy else []) + [
            o["CustomerName"], o["CustomerCity"], o["RegionName"], o["ShipToCity"], o["BillToCity"],
            o["OrderDate"].strftime("%Y-%m-%d %H:%M:%S"), o["OrderChannel"], o["Status"], o["Priority"],
            o["OrderTotal"], o["OrderNotes"], None]
        return base + (["orders_export_2025.csv"] if legacy else [])

    common = ["CustomerName", "CustomerCity", "RegionName", "ShipToCity", "BillToCity", "OrderDate",
              "OrderChannel", "Status", "Priority", "OrderTotal", "OrderNotes", "GiftMessage"]
    sheet("ORDERS_2025", ["OrderID", "LegacyRef"] + common + ["SourceFile"],
          [order_row(o, True) for o in g["orders"] if o["_d"].year == 2025])
    sheet("ORDERS_2026", ["OrderID"] + common,
          [order_row(o, False) for o in g["orders"] if o["_d"].year == 2026])

    ship_rows = [(s["ShipmentID"], s["OrderID"], s["ShipMode"], s["ShipDate"].isoformat(),
                  s["DeliveryDate"].isoformat() if s["DeliveryDate"] else None) for s in g["shipments"]]
    sheet("Sheet1", ["ShipmentID", "OrderID", "ShipMode", "ShipDate", "DeliveryDate"], ship_rows)

    sheet("campaign_skus", ["CampaignName", "PromotedSKUs"],
          [(cp["name"], ", ".join(p["code"] for p in cp["promoted"])) for cp in g["camp"]])
    sheet("cities", ["CityName", "RegionName"], g["cities"])

    contacts = []
    for c in g["customers"]:
        domain = slug(c["name"]) + ".example"
        for k in range(pick(rng, [(1, .3), (2, .3), (3, .25), (4, .15)])):
            fn, ln = rng.choice(FIRST), rng.choice(LAST)
            contacts.append((c["id"], f"{fn} {ln}", f"{email_part(fn)}.{email_part(ln)}@{domain}",
                             "True" if k == 0 else "False"))
    sheet("customer_contacts", ["CustomerID", "ContactName", "Email", "IsPrimary"], contacts)

    sheet("dim_order", ["OrderID"], [(o["OrderID"],) for o in g["orders"]])

    fx = []
    for y, m in g["months"]:
        t = (y - 2025) * 12 + m
        for cur, base, drift in [("CHF", .94, -.002), ("USD", 1.07, .004), ("GBP", .84, .001)]:
            fx.append((cur, round(base + drift * t + rng.uniform(-.01, .01), 4), f"{y}-{m:02d}-01"))
    sheet("exchange_rates", ["Currency", "Rate", "Date"], fx)

    sheet("inventory", ["ProductName"] + [f"{y}-{m:02d}" for y, m in g["months"]], g["inventory"])
    sheet("invoice_lines", ["InvoiceLineID", "InvoiceID", "ProductName", "Amount"],
          [(i["InvoiceLineID"], i["InvoiceID"], i["ProductName"], i["Amount"]) for i in g["invoice_lines"]])
    sheet("order_line_items", ["LineID", "OrderID", "ProductName", "Quantity", "UnitPrice", "UnitCost",
                               "DiscountPct", "LineTotal"],
          [(l["LineID"], l["OrderID"], l["ProductName"], l["Quantity"], l["UnitPrice"], l["UnitCost"],
            l["DiscountPct"], l["LineTotal"]) for l in g["lines"]])
    sheet("payments", ["PaymentID", "InvoiceID", "CustomerName", "PayDate", "Amount"],
          [(p["PaymentID"], p["InvoiceID"], p["CustomerName"], p["PayDate"].isoformat(), p["Amount"])
           for p in g["payments"]])

    prod_rows = [(p["code"], p["name"], p["brand"], p["sub"], p["price"], p["supplier"], p["desc"],
                  md5(p["code"]), f"SAP-{100000 + i + 1}") for i, p in enumerate(g["products"])]
    for p in rng.sample(g["products"], 2):     # duplicate master-data rows without supplier
        prod_rows.insert(rng.randint(0, len(prod_rows)),
                         (p["code"], p["name"], None, p["sub"], p["price"], None, None, None, None))
    prod_rows.append(("TST-999", "TEST PRODUCT", "TEST", "TEST", 0, "TEST", None, None, None))
    sheet("products", ["ProductCode", "ProductName", "Brand", "SubcategoryName", "UnitPrice", "PrimarySupplier",
                       "ProductDescription", "hash_key", "source_id"], prod_rows)

    sheet("regions", ["RegionName"], [(r,) for r in REGIONS])
    sheet("sales_targets", ["Period", "TargetRevenue"], g["targets"])
    sheet("security", ["UserEmail", "Region"],
          [(f"{REGIONAL_HEADS[r]}@arka.example", r) for r in REGIONS])
    sheet("shipments", ["ShipmentID", "OrderID", "ShipMode", "ShipDate", "DeliveryDate"], ship_rows)
    sheet("subcategories", ["CategorySubcategory"], [(f"{cat}|{s}",) for cat, v in CATEGORIES.items() for s in v[0]])

    user_rows = []
    for c in g["customers"]:
        pre = PHONE_PREFIX[c["country"]]
        user_rows.append((str(c["id"]), c["credit"], f"{pre}-{rng.randint(30, 999)}-{rng.randint(100000, 9999999)}"))
    sheet("user_details", ["UserID", "CreditLimit", "Phone"], user_rows)

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--orders", type=int, default=24000, help="approximate number of orders")
    ap.add_argument("--customers", type=int, default=1200)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "data" / "raw_tables.xlsx"))
    args = ap.parse_args()

    g = generate(args.seed, args.orders, args.customers)
    write_workbook(g, Path(args.out))

    revenue = sum(l["LineTotal"] for l in g["lines"])
    print(f"customers {len(g['customers']):,}  products {len(g['products']):,}  orders {len(g['orders']):,}  "
          f"lines {len(g['lines']):,}  shipments {len(g['shipments']):,}  invoices {len(g['invoices']):,}  "
          f"payments {len(g['payments']):,}")
    print(f"net revenue EUR {revenue:,.0f}  ->  {args.out}")


if __name__ == "__main__":
    main()
