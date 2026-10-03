"""Build sourced regional price references and enrich applicable dataset rows.

Prices are transcribed from public offers/tables, never extrapolated to states
or vehicle classes not named by a source. Run from the project root.
"""
from __future__ import annotations

from pathlib import Path
import json
import re
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "service_records_balanced_3000.csv"
REFERENCE = ROOT / "north_india_repair_price_reference.csv"
REPORT = ROOT / "north_india_price_validation_report.md"
ACCESS_DATE = "2026-10-28"
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
    df=pd.DataFrame(rows,columns=FIELDS)
    df.to_csv(REFERENCE,index=False)
    return df


def enrich_dataset(ref):
    df=pd.read_csv(DATASET)
    # Add reference metadata without fabricating component splits. Only comparable,
    # location-specific price ranges for matching vehicle type are applied.
    for column in ('reference_price_min', 'reference_price_max', 'price_reference_url'):
        if column not in df:
            df[column] = pd.NA if column != 'price_reference_url' else ''
    df['price_reference_url'] = df['price_reference_url'].astype(object)
    applied=0
    direct=ref[(ref.availability=='priced') & ref.state.isin(STATES) & ref.price_min.notna() & ref.price_max.notna() & ref.vehicle_type.ne('')]
    for idx,r in df.iterrows():
        try:
            existing_fault_costs=json.loads(str(r.get('fault_costs', '{}')))
        except (TypeError, json.JSONDecodeError):
            existing_fault_costs={}
        if r.primary_fault not in existing_fault_costs:
            continue
        matches=direct[(direct.fault_category==r.primary_fault)&(direct.state==r.state)&(direct.vehicle_type==r.vehicle_type)]
        if matches.empty:
            continue
        # Match detailed scope where source-specific job language is represented.
        chosen=None
        for _,candidate in matches.iterrows():
            job=candidate.repair_or_part.lower()
            replaced=str(r.get('parts_replaced','')).lower()
            if candidate.fault_category=='Brake System' and r.vehicle_type=='bike' and ('brake' in replaced or 'brake' in str(r.symptoms).lower()):
                cc=re.search(r'\b(\d{3,4})\b',str(r.get('vehicle_model','')))
                if cc and int(cc.group(1))>180: chosen=candidate; break
            if candidate.city=='Jaipur' and candidate.fault_category in ('Battery/Electrical','General Maintenance','Brake System'):
                if candidate.fault_category=='Battery/Electrical' and ('battery' in replaced or 'battery' in str(r.symptoms).lower()): chosen=candidate; break
                if candidate.fault_category=='General Maintenance' and ('service' in replaced or 'service' in str(r.symptoms).lower()): chosen=candidate; break
                if candidate.fault_category=='Brake System' and ('brake' in replaced or 'brake' in str(r.symptoms).lower()): chosen=candidate; break
        if chosen is None:
            continue
        low,high=float(chosen.price_min),float(chosen.price_max)
        midpoint=round((low+high)/2)
        df.at[idx,'reference_price_min']=low
        df.at[idx,'reference_price_max']=high
        df.at[idx,'price_reference_url']=chosen.source_url
        df.at[idx,'actual_repair_cost']=midpoint
        fault_costs=json.loads(str(r.get('fault_costs') or '{}'))
        fault_costs[r.primary_fault]=midpoint
        df.at[idx,'fault_costs']=json.dumps(fault_costs,ensure_ascii=False,sort_keys=True)
        df.at[idx,'total_repair_cost']=int(round(sum(float(value) for value in fault_costs.values())*(0.9 if len(fault_costs)>1 else 1.0)))
        # No split when the cited offer gives only a combined total range.
        df.at[idx,'parts_cost']=pd.NA
        df.at[idx,'labour_cost']=pd.NA
        applied+=1
    # Check no fault category/row changed or removed.
    assert len(df)==3000
    assert df.primary_fault.value_counts().eq(300).all()
    df.to_csv(DATASET,index=False)
    return df,applied


def main():
    ref=create_reference()
    df,applied=enrich_dataset(ref)
    bad_ranges=int(((ref.price_min.notna()) & (ref.price_max.notna()) & (ref.price_min>ref.price_max)).sum())
    bad_source=int(((ref.availability=='priced') & (ref.source_url=='')).sum())
    bad_components=int(((df.parts_cost.notna() & df.labour_cost.notna()) & (df.parts_cost+df.labour_cost!=df.actual_repair_cost)).sum())
    regional=ref[(ref.availability=='priced') & ref.state.isin(STATES)]
    coverage=regional.groupby('state').fault_category.nunique().to_dict()
    report=[
        "# North India repair-price reference and validation", "",
        f"Research/access date: {ACCESS_DATE}.",
        "Prices are public menu/list prices transcribed from the cited pages. They are not workshop invoices or guaranteed final quotes. ‘From’ entries are lower bounds, not complete ranges.", "",
        "## Regional evidence coverage", "",
        f"- Regional evidence rows (named target state/city): {len(regional)}; states with at least one priced category: {', '.join(sorted(coverage)) or 'none'}.",
        f"- Target state/category matrix: {len(STATES)*len(CATEGORIES)} combinations; directly priced combinations: {len({(r.fault_category,r.state) for _,r in regional.iterrows()})}; remaining combinations explicitly marked unavailable in the CSV.",
        "- Evidence is concentrated in Delhi (two-wheeler brake pad/shoe menu), Ghazipur, Uttar Pradesh (starting prices for car brake, suspension, clutch, engine, service and tyre jobs), and Jaipur, Rajasthan (car battery, brake and maintenance menu prices). No state-specific comparable prices were verified in this pass for Haryana, Punjab, Uttarakhand, Himachal Pradesh, or Jammu and Kashmir.",
        "- National/unspecified sources are retained as separate reference rows: Exide 35Ah battery MRP (part only), 185/65 R15 tyre listings (part only), and a location-unstated labour chart. These are not treated as state-specific evidence.", "",
        "## Dataset integration", "",
        f"- Prepared dataset rows: {len(df)}; primary category counts: exactly 300 each across all 10 categories.",
        f"- Rows matched to a comparable, state-specific published total range: {applied}.",
        "- For matched rows, the primary-fault cost target is the cited range midpoint and the range plus source URL are stored in `reference_price_min`, `reference_price_max`, and `price_reference_url`. Multi-fault combined totals are recalculated from the per-fault target map and the shared-visit rule. Since sources give combined totals, parts/labour are blank rather than fabricated.",
        "- All unmatched records retain their prior per-fault costs; no state multiplier or price extrapolation was applied. Parts and labour remain separately populated only where both component amounts are available and sum to the primary-fault target.",
        "- Original CSV remains unchanged. The multilabel classifier artifact and source CSV were not touched.", "",
        "## Checks", "",
        f"- Invalid price ranges (min > max): {bad_ranges}.",
        f"- Priced rows missing source URL: {bad_source}.",
        f"- Component-sum mismatches against primary-fault targets where both parts/labour exist: {bad_components}.",
        f"- Duplicate matrix state/category pairs in the explicit regional coverage map: {int(regional.duplicated(['state','fault_category']).sum())}.",
        "- Data quality caveat: public service-menu scopes and vehicle specifications are not fully comparable. Starting prices do not establish upper bounds, and listed menu services may have different inclusions. The reference CSV preserves these qualifications row by row.", "",
        "## Files", "",
        "- `north_india_repair_price_reference.csv` — sourced offers, parts/labour-only evidence, and explicit unavailable matrix rows.",
        "- `service_records_balanced_3000.csv` — enriched in place while retaining 3,000 rows and 300 per primary category.",
        "- `north_india_price_validation_report.md` — coverage and validation report.",
        "- `build_price_reference.py` — reproducible build/integration script.", "",
        "## Sources", "",
    ]
    for key,(name,url,location,evidence) in SOURCES.items():
        report.append(f"- [{name}]({url}) — {location}; {evidence}.")
    REPORT.write_text("\n".join(report),encoding='utf-8')
    print(f"reference_rows={len(ref)} dataset_rows={len(df)} applied_ranges={applied} invalid_ranges={bad_ranges} bad_source={bad_source} component_mismatches={bad_components}")

if __name__=='__main__':
    main()
