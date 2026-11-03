"""Read-only dataset audit; writes detailed tables to audit_report.md."""
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import pandas as pd
from backend.vehicles import MODEL_FACTS, VEHICLES
from backend.ml.severity import SEVERITY_RULE_TABLE, combined_severity

ROOT = Path(__file__).resolve().parent
SERVICE = pd.read_csv(ROOT / 'service_records.csv', keep_default_na=False)
STOCK = pd.read_csv(ROOT / 'inventory_stock.csv', keep_default_na=False)
LEDGER = pd.read_csv(ROOT / 'inventory_log.csv', keep_default_na=False)
MONTHLY = pd.read_csv(ROOT / 'monthly_summary.csv', keep_default_na=False)
REF = pd.read_csv(ROOT / 'north_india_repair_price_reference.csv', keep_default_na=False)
CHECKS: dict[str, list[tuple[str, str]]] = defaultdict(list)
DETAIL: list[str] = []
def bad(check, job, detail): CHECKS[check].append((str(job), str(detail)))
LEVELS = SEVERITY_RULE_TABLE['levels']
CATALOGUE = {(t,b,m) for t, brands in VEHICLES.items() for b, models in brands.items() for m in models}
DANGEROUS = [set(x) for x in SEVERITY_RULE_TABLE['dangerous_combinations']]
ALL_CATS = sorted(SEVERITY_RULE_TABLE['category_baseline'])

# a/b: vehicle plausibility and class-specific wording
for r in SERVICE.itertuples(index=False):
    facts = MODEL_FACTS.get(r.model)
    if (r.vehicle_type,r.brand,r.model) not in CATALOGUE: bad('a catalogue',r.job_id,'unsupported vehicle')
    if facts:
        if int(r.age) > 2026-facts['launch_year']: bad('a age',r.job_id,f'{r.model}, age={r.age}, max={2026-facts["launch_year"]}')
        annual=float(r.km_driven)/max(1,int(r.age)); lo,hi=(3000,12000) if r.vehicle_type=='bike' else (5000,18000); cap=120000 if r.vehicle_type=='bike' else 250000
        if not lo<=annual<=hi or int(r.km_driven)>cap: bad('a mileage',r.job_id,f'{annual:.0f} km/yr, total={r.km_driven}')
        s=r.symptoms.lower(); impossible=[]
        if facts['body']=='scooter' and any(w in s for w in ('chain','clutch','gear')): impossible.append('chain/clutch/gear on CVT scooter')
        if r.vehicle_type=='car' and 'riding' in s: impossible.append('riding on car')
        if r.vehicle_type=='bike' and 'driving' in s: impossible.append('driving on bike')
        if facts['cooling']=='air' and any(w in s for w in ('coolant','radiator')): impossible.append('coolant/radiator on air-cooled model')
        if impossible: bad('b compatibility',r.job_id,'; '.join(impossible))

# Fault/severity statistics, pairs, primary, symptom template proxies.
pairs=Counter(); severity_rows=[]; month_category=[]; category_severity=[]
faults_by_job={}; per_fault_by_job={}
for r in SERVICE.itertuples(index=False):
    faults=r.faults.split(';'); faults_by_job[r.job_id]=faults
    pf=json.loads(r.per_fault_severity); per_fault_by_job[r.job_id]=pf
    for pair in combinations(sorted(set(faults)),2): pairs[pair]+=1
    ranked=sorted(faults,key=lambda f:(LEVELS.index(pf[f]),float(json.loads(r.per_fault_cost).get(f,0))),reverse=True)
    if ranked and r.primary_fault!=ranked[0]: bad('e primary fault',r.job_id,f'primary={r.primary_fault}, expected={ranked[0]}')
    expected=combined_severity(faults,pf)
    if r.severity!=expected: bad('d combined severity',r.job_id,f'{r.severity} vs {expected}')
    category_severity.extend((f,pf[f],r.job_id) for f in faults)
    month_category.extend((r.service_date[:7],r.service_date[5:7],f) for f in faults)
    severity_rows.append((r.primary_fault,r.severity))
    if not any(phrase in r.symptoms.lower() for phrase in ('dim', 'oil and filter are due')) and r.primary_fault=='General Maintenance' and 'oil change' in r.symptoms.lower() and r.severity!='low': bad('d oil change due severity',r.job_id,r.severity)
    if 'headlights dim' in r.symptoms.lower() and r.severity!='low': bad('d dim lights severity',r.job_id,r.severity)

# c price parity; d reference bands by category/type (recorded, not adjudicated
# when the reference source has no prices for that segment).
part_map=STOCK.set_index('part_id').to_dict('index'); part_prices=defaultdict(dict)
for p in STOCK.itertuples(index=False): part_prices[(p.fault_category,p.part_name)][p.vehicle_type]=float(p.unit_price)
parity=0
for (cat,name), bytype in part_prices.items():
    if 'bike' in bytype and 'car' in bytype and bytype['bike']==bytype['car']: parity+=1
if parity: bad('c bike/car identical part prices','-',f'{parity} paired SKU prices identical')
medrows=[]
for (cat,vtype), rows in SERVICE.assign(cost=pd.to_numeric(SERVICE.customer_charge)).groupby(['primary_fault','vehicle_type']):
    candidates=REF[(REF.fault_category==cat)&(REF.vehicle_type==vtype)&REF.availability.eq('priced')]
    lows=pd.to_numeric(candidates.price_min,errors='coerce').dropna(); highs=pd.to_numeric(candidates.price_max,errors='coerce').dropna()
    lo=float(lows.median()) if len(lows) else float('nan'); hi=float(highs.median()) if len(highs) else float('nan'); med=float(rows.cost.median())
    medrows.append((cat,vtype,len(rows),round(med,2),round(lo,2) if pd.notna(lo) else None,round(hi,2) if pd.notna(hi) else None))
    if pd.notna(lo) and pd.notna(hi) and not (.75*lo<=med<=1.25*hi): bad('c reference median','-',f'{cat}/{vtype}: median {med:.0f}, ref {lo:.0f}-{hi:.0f}')
DETAIL += ['## Median job charge vs reference range','| Category | Vehicle | n | Dataset median | Ref median low | Ref median high |','|---|---:|---:|---:|---:|---:|']
DETAIL += [f'| {c} | {v} | {n} | {m:.0f} | {lo if lo is not None else "n/a"} | {hi if hi is not None else "n/a"} |' for c,v,n,m,lo,hi in medrows]

# f multi-fault discount expected 10% of line charge when >=2 faults.
DISCOUNT_RATE=.10
for r in SERVICE.itertuples(index=False):
    expected=round((float(r.customer_charge)+float(r.discount))*DISCOUNT_RATE) if int(r.fault_count)>=2 else 0
    if int(r.discount)!=expected: bad('f multi-fault discount',r.job_id,f'discount={r.discount}, required={expected}')

# g every categorical pair and dangerous coverage target.
all_pairs=list(combinations(ALL_CATS,2))
for p in all_pairs:
    if pairs[p]<25: bad('g pair coverage','-',f'{p[0]} + {p[1]}: {pairs[p]} < 25')
for p in DANGEROUS:
    if pairs[tuple(sorted(p))]<60: bad('g dangerous pair','-',f'{" + ".join(sorted(p))}: {pairs[tuple(sorted(p))]} < 60')

# h template diversity (full-symptom unique count proxy until template ids exist)
for (cat,sev), rows in SERVICE.groupby(['primary_fault','severity']):
    n=rows.symptoms.nunique()
    if n<8: bad('h template diversity','-',f'{cat}/{sev}: {n} distinct symptom strings')
vague=SERVICE.symptoms.str.contains(r'\b(gaadi|nahi|problem|issue|not working|noise)\b|typo|brke|battrey|engin\b',case=False,regex=True)
vague_share=float(vague.mean())
if not .04<=vague_share<=.13: bad('h vague/typo/Hinglish share','-',f'{vague_share:.1%}; target approximately 8%')

# i chronology, Sundays/Indian festival dates, seasonality and demand trend.
timestamps=pd.to_datetime(SERVICE.service_date+' '+SERVICE.service_time)
if SERVICE.job_id.tolist()!=SERVICE.assign(_ts=timestamps).sort_values(['_ts','job_id']).job_id.tolist(): bad('i job id order','-','IDs are not chronological')
for idx,r in SERVICE.iterrows():
    if pd.Timestamp(r.service_date).dayofweek==6: bad('i Sunday jobs',r.job_id,r.service_date)
# Common national/major North India holidays in the span; audited fixed dates.
holidays={'2025-01-26','2025-03-14','2025-08-15','2025-10-02','2025-10-20','2025-10-21','2025-11-05','2026-01-26','2026-03-04','2026-08-15','2026-10-02','2026-10-20'}
for r in SERVICE.itertuples(index=False):
    if r.service_date in holidays: bad('i holiday jobs',r.job_id,r.service_date)
month_fault=SERVICE.assign(month=pd.to_datetime(SERVICE.service_date).dt.month).explode('faults') if False else None
season=SERVICE.assign(month=pd.to_datetime(SERVICE.service_date).dt.month, fault=SERVICE.faults.str.split(';')).explode('fault')
season_table=season.groupby(['fault','month']).size().unstack(fill_value=0)
for cat, peak, base, threshold in [('Cooling System',[4,5,6],[12,1],1.4),('Battery/Electrical',[12,1,2],[4,5,6],1.0),('Starting System',[12,1,2],[4,5,6],1.0),('Tyres/Wheels',[7,8,9],[1,2,3],1.0),('Brake System',[7,8,9],[1,2,3],1.0)]:
    counts=season_table.loc[cat] if cat in season_table.index else pd.Series(dtype=float)
    ratio=float(counts.reindex(peak,fill_value=0).mean()/max(.01,counts.reindex(base,fill_value=0).mean()))
    if ratio<threshold: bad('i seasonality','-',f'{cat}: peak/base {ratio:.2f} < {threshold}')
DETAIL += ['## Severity distribution by primary fault','| Fault | Severity | Jobs |','|---|---|---:|']
DETAIL += [f'| {cat} | {sev} | {int(n)} |' for (cat,sev),n in SERVICE.groupby(['primary_fault','severity']).size().items()]
DETAIL += ['', '## Fault category by service month','| Fault | '+ ' | '.join(str(i) for i in range(1,13))+' |','|---|'+'---:|'*12]
DETAIL += [f'| {cat} | '+' | '.join(str(int(season_table.loc[cat].get(i,0))) for i in range(1,13))+' |' for cat in season_table.index]

# j opening stock, negative inventory, ledger vs snapshot and monthly reconciliation.
for p in STOCK.itertuples(index=False):
    if int(p.opening_stock)<int(p.reorder_level): bad('j opening stock','-',f'{p.part_id}: {p.opening_stock} < {p.reorder_level}')
    if int(p.stock)<0: bad('j negative stock','-',f'{p.part_id}: {p.stock}')
running=Counter()
for r in LEDGER.sort_values(['event_date','event_time','event_id']).itertuples(index=False):
    running[r.part_id]+=int(r.quantity_change)
    if running[r.part_id]<0: bad('j negative ledger',r.event_id,f'{r.part_id} balance {running[r.part_id]}')
    if running[r.part_id]!=int(r.stock_after): bad('j ledger balance',r.event_id,f'{r.part_id}: calculated {running[r.part_id]}, stored {r.stock_after}')
for r in STOCK.itertuples(index=False):
    if running[r.part_id]!=int(r.stock): bad('j snapshot reconciliation','-',f'{r.part_id}: ledger {running[r.part_id]} vs snapshot {r.stock}')
svc_month=SERVICE.assign(month=SERVICE.service_date.str.slice(0,7)).groupby('month').agg(jobs=('job_id','count'),revenue=('customer_charge','sum'),parts_cost=('parts_cost','sum'),labour_cost=('labour_cost','sum'),gross_margin=('gross_margin','sum')).reset_index()
for r in svc_month.itertuples(index=False):
    m=MONTHLY[MONTHLY.month==r.month]
    if not len(m) or any(abs(float(m.iloc[0][col])-float(getattr(r,col)))>.02 for col in ('jobs','revenue','parts_cost','labour_cost','gross_margin')): bad('j monthly reconciliation','-',r.month)

REPORT=['# Dataset audit details','',f'Rows: {len(SERVICE)}; stock SKUs: {len(STOCK)}; ledger events: {len(LEDGER)}; vague/typo/Hinglish proxy share: {vague_share:.1%}.','']+DETAIL
(ROOT/'audit_report.md').write_text('\n'.join(REPORT)+'\n',encoding='utf-8')
parser=argparse.ArgumentParser(); parser.add_argument('--summary',action='store_true'); args=parser.parse_args()
print('| Check | Violations | 3 example job_ids |')
print('|---|---:|---|')
labels=['a catalogue','a age','a mileage','b compatibility','c bike/car identical part prices','c reference median','d combined severity','d oil change due severity','d dim lights severity','e primary fault','f multi-fault discount','g pair coverage','g dangerous pair','h template diversity','h vague/typo/Hinglish share','i job id order','i Sunday jobs','i holiday jobs','i seasonality','j opening stock','j negative stock','j negative ledger','j ledger balance','j snapshot reconciliation','j monthly reconciliation']
for label in labels:
    rows=CHECKS[label]; ids=', '.join(dict.fromkeys(x[0] for x in rows[:3])) or 'none'
    print(f'| {label} | {len(rows)} | {ids} |')
