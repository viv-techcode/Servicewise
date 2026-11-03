"""Build the standalone sourced regional repair-price reference CSV."""
from __future__ import annotations

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
REFERENCE = ROOT / "north_india_repair_price_reference.csv"
ACCESS_DATE = "2026-11-03"
STATES = ["Uttar Pradesh", "Delhi", "Haryana", "Punjab", "Rajasthan", "Uttarakhand", "Himachal Pradesh", "Jammu and Kashmir"]
CATEGORIES = ["Battery/Electrical", "Brake System", "Cooling System", "Engine", "Fuel System", "General Maintenance", "Starting System", "Suspension", "Transmission", "Tyres/Wheels"]

SOURCES = {
    "up_sewamitra": ("SewaMitra Uttar Pradesh (Ghazipur car repair menu)", "https://sewamitra.up.gov.in/car-repair-service-ghazipur", "Ghazipur, Uttar Pradesh", "Page date inconsistent: footer shows 2025-07-18; search snippet showed 2026-07-16; accessed 2026-10-28"),
    "jaipur_gaadimech": ("GaadiMech Jaipur car service price list", "https://www.gaadimech.com/car-service-price-jaipur", "Jaipur, Rajasthan", "Evidence date not stated; accessed 2026-10-28"),
    "delhi_apnamechanic": ("Apna Mechanic Delhi bike repair price list", "https://www.apnamechanic.com/bikes/delhi/", "Delhi, India", "Evidence date not stated; accessed 2026-10-28"),
    "exide_product": ("Exide EPIQ35L official product page", "https://www.exidecare.com/find-exide/products/exide-epiq/epiq35l", "India (national listing; regional checkout not specified)", "Evidence date not stated; accessed 2026-10-28"),
    "tyresnmore": ("Tyresnmore 185/65 R15 listings", "https://tyresnmore.com/all/tyre-size/185-65-r15.html", "India online listing; delivery location varies", "Live listing; accessed 2026-10-28"),
    "shree_autocare": ("Shree Auto Care labour rate chart", "https://shreeautocare.in/labour-rates/", "Location/state not stated on price page", "Evidence date not stated; accessed 2026-10-28"),
}

FIELDS = ["fault_category", "state_or_city", "state", "city", "vehicle_type", "vehicle_details", "repair_or_part", "parts_cost", "labour_cost", "total_cost", "price_min", "price_max", "price_basis", "availability", "source_name", "source_url", "source_location", "access_date", "evidence_date", "source_detail", "notes"]


def row(cat, state, city, vtype, details, job, parts=None, labour=None, total=None, low=None, high=None, basis="", source=None, detail="", notes=""):
    if source:
        name, url, location, evidence = SOURCES[source]
        availability = "priced"
    else:
        name, url, location, evidence = "", "", "", ""
        availability = "unavailable"
    return dict(fault_category=cat, state_or_city=city or state, state=state, city=city or "", vehicle_type=vtype or "", vehicle_details=details or "", repair_or_part=job or "", parts_cost=parts, labour_cost=labour, total_cost=total, price_min=low, price_max=high, price_basis=basis, availability=availability, source_name=name, source_url=url, source_location=location, access_date=ACCESS_DATE, evidence_date=evidence, source_detail=detail, notes=notes)


def create_reference():
    rows=[]
    # Evidence tied to a named city/state. These are quotes/list prices, not promises of a final bill.
    rows += [
        row("Brake System","Delhi","Delhi","bike","Above-180cc two-wheeler price table; model unspecified","Brake pad replacement (part + labour)",low=249,high=349,basis="published combined price range",source="delhi_apnamechanic",detail="₹249–₹349; source explicitly says part+labour; visiting fee/GST may be additional",notes="Offer/menu price. No separate parts/labour values published."),
        row("Brake System","Delhi","Delhi","bike","Above-180cc two-wheeler price table; model unspecified","Brake shoe replacement (part + labour)",low=199,high=249,basis="published combined price range",source="delhi_apnamechanic",detail="₹199–₹249; source explicitly says part+labour; visiting fee/GST may be additional",notes="Offer/menu price. No separate parts/labour values published."),
        row("Battery/Electrical","Rajasthan","Jaipur","car","Basic, premium and Amaron car battery options; make/model not specified","Car battery replacement menu",low=3499,high=5499,basis="menu alternatives; lower and upper listed options",source="jaipur_gaadimech",detail="Basic Battery ₹3,499; Premium ₹4,999; Amaron ₹5,499",notes="Indicative offer menu; exact battery specification and fitting inclusion are not detailed."),
        row("Brake System","Rajasthan","Jaipur","car","Vehicle segment and model to be confirmed","Brake service menu",low=1499,high=4499,basis="menu alternatives",source="jaipur_gaadimech",detail="Brake Pads ₹1,499; Disc Brake ₹2,999; Complete Brake ₹4,499",notes="Menu alternatives, not a model-specific quote; source says prices vary by model/requirements."),
        row("General Maintenance","Rajasthan","Jaipur","car","Hatchback example; other segments differ","Periodic service menu",low=1999,high=5499,basis="listed service tiers",source="jaipur_gaadimech",detail="Basic ₹1,999; Standard ₹3,499; Comprehensive ₹5,499",notes="Includes different scopes by tier; not interchangeable exact repair jobs."),
        row("General Maintenance","Uttar Pradesh","Ghazipur","car","Vehicle model/segment not specified","Car servicing (starting price)",total=1199,low=1199,basis="starting price",source="up_sewamitra",detail="Listed as starts from ₹1,199",notes="No upper bound or parts/labour breakdown; not used as a fixed training target."),
        row("Brake System","Uttar Pradesh","Ghazipur","car","Vehicle model/segment not specified","Car brake overhauling (starting price)",total=600,low=600,basis="starting price",source="up_sewamitra",detail="Listed as starts from ₹600",notes="No upper bound or parts/labour breakdown."),
        row("Suspension","Uttar Pradesh","Ghazipur","car","Vehicle model/segment not specified","Car suspension overhauling (starting price)",total=800,low=800,basis="starting price",source="up_sewamitra",detail="Listed as starts from ₹800",notes="No upper bound or parts/labour breakdown."),
        row("Transmission","Uttar Pradesh","Ghazipur","car","Vehicle model/segment not specified","Car clutch overhauling (starting price)",total=1000,low=1000,basis="starting price",source="up_sewamitra",detail="Listed as starts from ₹1,000",notes="No upper bound or parts/labour breakdown."),
        row("Engine","Uttar Pradesh","Ghazipur","car","Vehicle model/segment not specified","Car engine overhauling (starting price)",total=5000,low=5000,basis="starting price",source="up_sewamitra",detail="Listed as starts from ₹5,000",notes="No upper bound or parts/labour breakdown."),
        row("Tyres/Wheels","Uttar Pradesh","Ghazipur","car","Vehicle model/segment not specified","Puncture repair (starting price)",total=69,low=69,basis="starting price",source="up_sewamitra",detail="Listed as starts from ₹69",notes="No upper bound; repair scope unspecified."),
        row("Tyres/Wheels","Uttar Pradesh","Ghazipur","car","Vehicle model/segment not specified","Wheel alignment and balancing (starting price)",total=300,low=300,basis="starting price",source="up_sewamitra",detail="Listed as starts from ₹300",notes="No upper bound; repair scope unspecified."),
        row("Tyres/Wheels","Rajasthan","Jaipur","car","Vehicle model/segment not specified","Wheel alignment",total=499,low=499,basis="starting price",source="jaipur_gaadimech",detail="Listed as ₹499 onwards",notes="No upper bound or parts/labour breakdown."),
        row("Battery/Electrical","India (national)","","car","Exide EPIQ35L, 35Ah; model fitment varies","35Ah EPIQ car battery (part only)",parts=6041,basis="official product MRP",source="exide_product",detail="MRP ₹6,041 inclusive of taxes",notes="Parts price only; installation/labour and regional delivery are not specified. Not a regional repair total."),
        row("Tyres/Wheels","India (online)","","car","185/65 R15 passenger-car tyre; brand/model varies","One tyre (part only)",parts=5849,low=5849,high=10299,basis="online product price range",source="tyresnmore",detail="Published size range ₹5,849–₹10,299; individual products displayed from ₹5,849 upward",notes="Online product price, fitment/location terms vary; no separate fitting amount in the displayed range."),
    ]
    # Labour-only published chart. It gives vehicle groups but does not identify its location.
    for cat, job, lo, hi, detail in [
        ("Brake System","Front brake pad replacement labour",530,960,"Groups 01–03: ₹530, ₹780, ₹960; Group 04 is per man hour"),
        ("Cooling System","Radiator replacement labour",810,1850,"Groups 01–03: ₹810, ₹1,550, ₹1,850"),
        ("Cooling System","Thermostat replacement labour",560,990,"Groups 01–03: ₹560, ₹900, ₹990"),
        ("Engine","Petrol engine overhaul labour",12000,18000,"Groups 01–03: ₹12,000, ₹15,000, ₹18,000"),
        ("Fuel System","Fuel injector replacement labour",560,810,"Groups 01–03: ₹570, ₹560, ₹810"),
        ("Transmission","Clutch cable replacement labour",850,1550,"Groups 01–03: ₹850, ₹1,250, ₹1,550"),
        ("Battery/Electrical","AC inspection and gas filling labour/menu charge",2560,3440,"Groups 01–03: ₹2,560, ₹3,060, ₹3,440; electrical A/C service only"),
    ]:
        rows.append(row(cat,"Location not stated","","car","Car group chart; group definitions not published",job,labour=None,low=lo,high=hi,basis="published group price; labour/service classification as described",source="shree_autocare",detail=detail,notes="Location is not stated on source page; excluded from state-specific matching. Prices are listed in a labour rate chart; some line-item treatment may include service operations."))

    # Explicitly record all requested state/category gaps in the regional matrix.
    evidenced={(r['fault_category'],r['state']) for r in rows if r['availability']=='priced' and r['state'] in STATES}
    for state in STATES:
        for cat in CATEGORIES:
            if (cat,state) not in evidenced:
                rows.append(row(cat,state,"","","","",notes="No directly comparable, public, state-specific price located during this research pass. National or location-unstated evidence is kept separately and not substituted."))
    # Comparable full-job bands used by this synthetic demonstration data.
    # Published menu/SKU evidence is retained above; where it does not cover a
    # category/class, this separately labeled estimate is explicit and auditable.
    typical_bands = {
        "Battery/Electrical": {"bike": (500, 1500), "car": (1500, 4500)},
        "Brake System": {"bike": (800, 3000), "car": (2200, 7000)},
        "Cooling System": {"bike": (500, 2500), "car": (1600, 7000)},
        "Engine": {"bike": (1200, 6500), "car": (2800, 15000)},
        "Fuel System": {"bike": (500, 2500), "car": (1500, 7000)},
        "General Maintenance": {"bike": (700, 3000), "car": (2200, 9000)},
        "Starting System": {"bike": (500, 2500), "car": (1500, 7000)},
        "Suspension": {"bike": (1200, 7000), "car": (3000, 20000)},
        "Transmission": {"bike": (1200, 7000), "car": (4500, 26000)},
        "Tyres/Wheels": {"bike": (800, 7000), "car": (1800, 22000)},
    }
    for cat in CATEGORIES:
        for vtype in ("bike", "car"):
            low, high = typical_bands[cat][vtype]
            rows.append(dict(
                fault_category=cat, state_or_city="North India (estimate)", state="", city="",
                vehicle_type=vtype, vehicle_details="Typical mixed-scope jobs across budget/mid models",
                repair_or_part="Typical repair job (demonstration comparison band)",
                parts_cost=None, labour_cost=None, total_cost=None, price_min=low, price_max=high,
                price_basis="typical-job estimate; synthetic benchmark, not a quote",
                availability="estimated", source_name="estimate", source_url="",
                source_location="North India planning estimate", access_date=ACCESS_DATE,
                evidence_date="", source_detail="No comparable public job total for this category/class was located; bounded estimate based on current price book and typical labour scope.",
                notes="Use only as a transparent plausibility band for generated demo data; not a market survey or customer quote."))
    df=pd.DataFrame(rows,columns=FIELDS)
    df.to_csv(REFERENCE,index=False)
    return df


def main():
    ref = create_reference()
    bad_ranges = int(((ref.price_min.notna()) & (ref.price_max.notna()) & (ref.price_min > ref.price_max)).sum())
    bad_source = int(((ref.availability == 'priced') & (ref.source_url == '')).sum())
    regional = ref[(ref.availability == 'priced') & ref.state.isin(STATES)]
    print(f"reference_rows={len(ref)} regional_states={regional.state.nunique()} invalid_ranges={bad_ranges} priced_rows_missing_source={bad_source}")


if __name__ == '__main__':
    main()
