"""Read-only dataset audit; writes detailed tables to audit_report.md."""
from __future__ import annotations
import argparse, json, os
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.vehicles import MODEL_FACTS, VEHICLES
from backend.ml.severity import SEVERITY_RULE_TABLE, combined_severity, detect_red_flag_faults
from backend.discount_rules import MULTI_FAULT_DISCOUNT_RATE

ROOT = Path(os.environ.get('SERVICEWISE_AUDIT_DATA_DIR', Path(__file__).resolve().parent))
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
    if 'headlight' in r.symptoms.lower() and 'dim' in r.symptoms.lower() and 'Battery/Electrical' not in detect_red_flag_faults(r.symptoms):
        dim = [s for f,s in pf.items() if f=='Battery/Electrical']
        if dim and dim[0] != 'low': bad('d dim lights severity',r.job_id,dim[0])

# c price parity; d reference bands by category/type (recorded, not adjudicated
# when the reference source has no prices for that segment).
part_map=STOCK.set_index('part_id').to_dict('index'); part_prices=defaultdict(dict)
for p in STOCK.itertuples(index=False): part_prices[(p.fault_category,p.part_name)][p.vehicle_type]=float(p.unit_price)
parity=0
for (cat,name), bytype in part_prices.items():
    if 'bike' in bytype and 'car' in bytype and bytype['bike']==bytype['car']: parity+=1
if parity: bad('c bike/car identical part prices','-',f'{parity} paired SKU prices identical')
medrows=[]
class_medians={}
for (cat,vtype), rows in SERVICE.assign(cost=pd.to_numeric(SERVICE.customer_charge)).groupby(['primary_fault','vehicle_type']):
    candidates=REF[(REF.fault_category==cat)&(REF.vehicle_type==vtype)&REF.availability.eq('estimated')&REF.price_basis.str.startswith('typical-job estimate',na=False)]
    lows=pd.to_numeric(candidates.price_min,errors='coerce').dropna(); highs=pd.to_numeric(candidates.price_max,errors='coerce').dropna()
    lo=float(lows.median()) if len(lows) else float('nan'); hi=float(highs.median()) if len(highs) else float('nan'); med=float(rows.cost.median())
    class_medians[(cat,vtype)] = med
    medrows.append((cat,vtype,len(rows),round(med,2),round(lo,2) if pd.notna(lo) else None,round(hi,2) if pd.notna(hi) else None))
    if not pd.notna(lo) or not pd.notna(hi): bad('c reference median','-',f'{cat}/{vtype}: missing explicit comparable reference range')
    elif not (.75*lo<=med<=1.25*hi): bad('c reference median','-',f'{cat}/{vtype}: median {med:.0f}, ref {lo:.0f}-{hi:.0f}')
DETAIL += ['## Median job charge vs reference range','| Category | Vehicle | n | Dataset median | Ref median low | Ref median high |','|---|---:|---:|---:|---:|---:|']
DETAIL += [f'| {c} | {v} | {n} | {m:.0f} | {lo if lo is not None else "n/a"} | {hi if hi is not None else "n/a"} |' for c,v,n,m,lo,hi in medrows]
DETAIL += ['', '## Bike-to-car median job charge','| Fault | Bike median | Car median | Ratio |','|---|---:|---:|---:|']
ratios=[]
for cat in ALL_CATS:
    bike=class_medians.get((cat,'bike')); car=class_medians.get((cat,'car'))
    if bike is not None and car:
        ratios.append(bike/car)
        DETAIL.append(f'| {cat} | {bike:.0f} | {car:.0f} | {bike/car:.2f} |')
if sum(.30<=ratio<=.60 for ratio in ratios)<6:
    bad('c bike/car job cost ratio','-',f'{sum(.30<=ratio<=.60 for ratio in ratios)} of {len(ratios)} categories within 0.30-0.60')

# f multi-fault discount expected 10% of line charge when >=2 faults.
for r in SERVICE.itertuples(index=False):
    if int(r.fault_count)>=2:
        expected=round((float(r.customer_charge)+float(r.discount))*MULTI_FAULT_DISCOUNT_RATE)
        if int(r.discount)!=expected: bad('f multi-fault discount',r.job_id,f'discount={r.discount}, required={expected}')

# g every categorical pair and dangerous coverage target.
all_pairs=list(combinations(ALL_CATS,2))
for p in all_pairs:
    if pairs[p]<25: bad('g pair coverage','-',f'{p[0]} + {p[1]}: {pairs[p]} < 25')
for p in DANGEROUS:
    if pairs[tuple(sorted(p))]<60: bad('g dangerous pair','-',f'{" + ".join(sorted(p))}: {pairs[tuple(sorted(p))]} < 60')

# h template diversity (full-symptom unique count proxy until template ids exist)
template_rows=[]
if 'symptom_template_id' not in SERVICE.columns and len(SERVICE):
    bad('h template diversity',SERVICE.iloc[0].job_id,'symptom_template_id column missing')
for r in SERVICE.itertuples(index=False):
    p=json.loads(r.per_fault_severity)
    t=json.loads(r.symptom_template_id) if 'symptom_template_id' in SERVICE.columns else {category:r.symptoms for category in p}
    for cat,sev in p.items(): template_rows.append((cat,sev,t.get(cat,'')))
template_counts=pd.DataFrame(template_rows,columns=['category','severity','template']).groupby(['category','severity']).template.nunique()
for (cat,sev), n in template_counts.items():
    if n<8: bad('h template diversity','-',f'{cat}/{sev}: {n} distinct symptom strings')
vague=SERVICE.symptoms.str.contains(r'\b(?:gaadi|nahi|problem|not working|engin\b|brke\b|battrey\b|hai|mein)\b|ho raha|ho rahi|aa rahi',case=False,regex=True)
vague_share=float(vague.mean())
if not .08<=vague_share<=.40: bad('h vague/typo/Hinglish share','-',f'{vague_share:.1%}; expected a mix of SMS/Hinglish/typos')

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
for cat, peak, base, threshold in [('Cooling System',[4,5,6],[12,1],1.4),('Battery/Electrical',[12,1,2],[4,5,6],1.1),('Starting System',[12,1,2],[4,5,6],1.1),('Tyres/Wheels',[7,8,9],[1,2,3],1.05),('Brake System',[7,8,9],[1,2,3],1.05)]:
    counts=season_table.loc[cat] if cat in season_table.index else pd.Series(dtype=float)
    jobs_by_month=SERVICE.assign(month=pd.to_datetime(SERVICE.service_date).dt.month).groupby('month').size()
    peak_share=float(counts.reindex(peak,fill_value=0).sum()/max(1,jobs_by_month.reindex(peak).sum()))
    base_share=float(counts.reindex(base,fill_value=0).sum()/max(1,jobs_by_month.reindex(base).sum()))
    ratio=peak_share/max(.0001,base_share)
    if ratio<threshold: bad('i seasonality','-',f'{cat}: peak/base {ratio:.2f} < {threshold}')
DETAIL += ['## Combined severity distribution by primary fault','| Fault | Severity | Jobs |','|---|---|---:|']
DETAIL += [f'| {cat} | {sev} | {int(n)} |' for (cat,sev),n in SERVICE.groupby(['primary_fault','severity']).size().items()]
pf_frame=pd.DataFrame(category_severity,columns=['fault','severity','job_id'])
DETAIL += ['', '## Per-fault severity distribution','| Fault | Severity | Fault instances |','|---|---|---:|']
DETAIL += [f'| {cat} | {sev} | {int(n)} |' for (cat,sev),n in pf_frame.groupby(['fault','severity']).size().items()]
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
stockout_trigger={(r.job_id,r.part_id):r.event_date for r in LEDGER[LEDGER.event_type.eq('stock_out')].itertuples(index=False)}
sale_trigger={(r.job_id,r.part_id):r.event_date for r in LEDGER[LEDGER.event_type.eq('sale')].itertuples(index=False)}
for r in LEDGER[LEDGER.event_type.eq('restock')].itertuples(index=False):
    trigger=stockout_trigger.get((r.job_id,r.part_id),sale_trigger.get((r.job_id,r.part_id)))
    if trigger:
        lead=int(part_map[r.part_id]['supplier_lead_time_days'])
        earliest=(pd.Timestamp(trigger)+pd.Timedelta(days=lead)).date().isoformat()
        if r.event_date<earliest: bad('j supplier lead time',r.event_id,f'{r.part_id}: {r.event_date} before {earliest}')
for r in STOCK.itertuples(index=False):
    if running[r.part_id]!=int(r.stock): bad('j snapshot reconciliation','-',f'{r.part_id}: ledger {running[r.part_id]} vs snapshot {r.stock}')
svc_month=SERVICE.assign(month=SERVICE.service_date.str.slice(0,7)).groupby('month').agg(jobs=('job_id','count'),revenue=('customer_charge','sum'),parts_cost=('parts_cost','sum'),labour_cost=('labour_cost','sum'),gross_margin=('gross_margin','sum')).reset_index()
for r in svc_month.itertuples(index=False):
    m=MONTHLY[MONTHLY.month==r.month]
    if not len(m) or any(abs(float(m.iloc[0][col])-float(getattr(r,col)))>.02 for col in ('jobs','revenue','parts_cost','labour_cost','gross_margin')): bad('j monthly reconciliation','-',r.month)
    if len(m):
        if not {'total_overheads','net_profit'}.issubset(m.columns):
            bad('j monthly reconciliation','-',r.month+' missing overhead/net columns')
        else:
            expected_net=float(r.gross_margin)-float(m.iloc[0]['total_overheads'])
            if abs(float(m.iloc[0]['net_profit'])-expected_net)>.02: bad('j monthly reconciliation','-',r.month+' net profit')

# Dataset v2 contract: size, grouped phrasing, explicit ambiguity, cost scope,
# comparable references and finance trend math.
if len(SERVICE) != 7000:
    bad('k job count', SERVICE.iloc[0].job_id if len(SERVICE) else '-', f'{len(SERVICE)} rows; expected 7000')
for col in ('phrasing_family_id','is_ambiguous','ambiguity_categories','estimated_cost_min','estimated_cost_max'):
    if col not in SERVICE.columns:
        bad('k v2 columns', SERVICE.iloc[0].job_id if len(SERVICE) else '-', f'missing {col}')
if 'phrasing_family_id' in SERVICE.columns and len(SERVICE):
    per_cat_unique=defaultdict(set); per_cat_vehicle=defaultdict(set); families=defaultdict(set)
    for r in SERVICE.itertuples(index=False):
        try:
            tids=json.loads(r.symptom_template_id)
            fams=json.loads(r.phrasing_family_id)
        except Exception:
            tids={}; fams={}
        for cat in str(r.faults).split(';'):
            per_cat_unique[cat].add(str(r.symptoms).strip().lower())
            per_cat_vehicle[(cat,r.vehicle_type)].add(str(r.symptoms).strip().lower())
            family=fams.get(cat,'')
            if family: families[cat].add(family.split(':')[-2] if ':' in family else family)
    for cat in ALL_CATS:
        if len(per_cat_unique[cat])<40: bad('k phrase diversity','-',f'{cat}: {len(per_cat_unique[cat])} unique phrasings < 40')
        for vtype in ('bike','car'):
            if len(per_cat_vehicle[(cat,vtype)])<40: bad('k class phrase diversity','-',f'{cat}/{vtype}: {len(per_cat_vehicle[(cat,vtype)])} < 40')
        if len(families[cat])<4: bad('k phrasing families','-',f'{cat}: only {len(families[cat])} style families')
else:
    bad('k phrasing families','-','phrasing_family_id missing or empty dataset')

if 'is_ambiguous' not in SERVICE.columns or 'ambiguity_categories' not in SERVICE.columns:
    bad('k ambiguity share','-','explicit ambiguity columns missing')
else:
    ambiguous_mask=SERVICE.is_ambiguous.astype(str).str.lower().isin(['true','1','yes'])
    ambiguity_share=float(ambiguous_mask.mean()) if len(SERVICE) else 0
    if not .08<=ambiguity_share<=.12:
        for job_id in SERVICE.loc[ambiguous_mask,'job_id'].head(3): bad('k ambiguity share',job_id,f'{ambiguity_share:.1%} outside 8%-12%')
    for r in SERVICE[ambiguous_mask].itertuples(index=False):
        try: candidates=json.loads(r.ambiguity_categories)
        except Exception: candidates=[]
        if int(r.fault_count)!=1 or r.primary_fault not in candidates or len(candidates)<2:
            bad('k ambiguity labels',r.job_id,'ambiguous row lacks a single true cause inside candidate set')

if {'estimated_cost_min','estimated_cost_max'}.issubset(SERVICE.columns):
    for r in SERVICE.itertuples(index=False):
        low,high=float(r.estimated_cost_min),float(r.estimated_cost_max)
        if low<=0 or high<low or high/low>1.5: bad('k estimate range',r.job_id,f'{low:g}..{high:g} exceeds 1.5x or is invalid')

for cat in ALL_CATS:
    bikes=class_medians.get((cat,'bike')); cars=class_medians.get((cat,'car'))
    if not bikes or not cars or cars<=0 or not .30<=bikes/cars<=.60:
        bad('k category cost ratio','-',f'{cat}: bike/car={bikes/cars:.3f}' if bikes and cars and cars else f'{cat}: missing bike or car median')
    for vtype in ('bike','car'):
        present=REF[(REF.fault_category==cat)&(REF.vehicle_type==vtype)&REF.availability.eq('estimated')&REF.price_basis.str.startswith('typical-job estimate',na=False)]
        if present.empty: bad('k reference completeness','-',f'missing estimated typical-job band: {cat}/{vtype}')
price_book_path=ROOT/'part_price_table.csv'
if not price_book_path.exists():
    bad('k explicit part price book','-','part_price_table.csv missing')
else:
    price_book=pd.read_csv(price_book_path,keep_default_na=False)
    if not 55<=len(price_book)<=70: bad('k explicit part price book','-',f'{len(price_book)} SKUs; expected approximately 60')
    for cat in ALL_CATS:
        for vtype in ('bike','car'):
            group=price_book[(price_book.fault_category==cat)&(price_book.vehicle_type==vtype)]
            if group.empty: bad('k explicit part price book','-',f'missing {cat}/{vtype} price rows')
    if {'price_basis','price_source','unit_price'}.issubset(price_book.columns):
        bad_rows=price_book[(pd.to_numeric(price_book.unit_price,errors='coerce')<=0)|~price_book.price_basis.isin(['estimate','catalogue/official listing'])]
        for pid in bad_rows.part_id.head(3): bad('k explicit part price book',pid,'invalid or unmarked price')

if {'is_ambiguous','symptoms'}.issubset(SERVICE.columns):
    ambiguity_share=float(SERVICE.is_ambiguous.astype(str).str.lower().isin(['true','1','yes']).mean())
    DETAIL += ['', '## Dataset v2 composition', '| Measure | Value |', '|---|---:|',
               f'| Jobs | {len(SERVICE)} |', f'| Ambiguous rows | {ambiguity_share:.1%} |',
               f'| Part-price SKUs | {len(pd.read_csv(ROOT / "part_price_table.csv")) if (ROOT / "part_price_table.csv").exists() else "missing"} |']

# Check severity-cost ordering from per-fault billed allocations. Only the
# explicitly required critical/high categories are constrained to be costlier.
severity_cost=[]
for r in SERVICE.itertuples(index=False):
    try: pc=json.loads(r.per_fault_cost); ps=json.loads(r.per_fault_severity)
    except Exception: continue
    for cat in set(str(r.faults).split(';')):
        if cat in ps and cat in pc: severity_cost.append((cat,r.vehicle_type,ps[cat],float(pc[cat]),r.job_id))
sevframe=pd.DataFrame(severity_cost,columns=['category','vehicle','severity','cost','job_id'])
for cat in ('Brake System','Cooling System','Fuel System'):
    for vtype in ('bike','car'):
        group=sevframe[(sevframe.category==cat)&(sevframe.vehicle==vtype)].groupby('severity').cost.median()
        for level in ('high','critical'):
            if 'low' not in group or level not in group or group[level] <= group['low']:
                bad('k severity cost monotonicity','-',f'{cat}/{vtype}: {level} median {group.get(level,float("nan")):.0f} <= low {group.get("low",float("nan")):.0f}')
parts_share=float(SERVICE.parts_cost.sum())/max(1,float(SERVICE.customer_charge.sum())) if len(SERVICE) else 0
if not .50<=parts_share<=.60: bad('k parts cost share','-',f'{parts_share:.1%}; target 50%-60%')

if {'revenue_mom_change_pct','jobs_mom_change_pct','trend'}.issubset(MONTHLY.columns):
    monthly_order=MONTHLY.sort_values('month').reset_index(drop=True)
    for idx,r in monthly_order.iterrows():
        if idx==0:
            if str(r.revenue_mom_change_pct).strip() not in ('','nan','NaN') or str(r.jobs_mom_change_pct).strip() not in ('','nan','NaN'):
                bad('k monthly trend','-',f'{r.month}: first-month change must be blank')
            continue
        prev=monthly_order.iloc[idx-1]
        rev=(float(r.revenue)/float(prev.revenue)-1)*100 if float(prev.revenue) else float('nan')
        jobs_pct=(float(r.jobs)/float(prev.jobs)-1)*100 if float(prev.jobs) else float('nan')
        want='growth' if rev>=5 else ('dip' if rev<=-5 else 'stable')
        if abs(float(r.revenue_mom_change_pct)-rev)>.02 or abs(float(r.jobs_mom_change_pct)-jobs_pct)>.02 or r.trend!=want:
            bad('k monthly trend','-',f'{r.month}: stored revenue/jobs pct or trend differs from raw totals')
else:
    bad('k monthly trend','-','revenue/jobs trend fields missing')
low_stock_count=int((pd.to_numeric(STOCK.stock)<=pd.to_numeric(STOCK.reorder_level)).sum()) if {'stock','reorder_level'}.issubset(STOCK.columns) else 0
stockout_periods=int((LEDGER.event_type=='stock_out').sum()) if 'event_type' in LEDGER.columns else 0
if low_stock_count<2: bad('k snapshot low stock','-',f'{low_stock_count} low/out-of-stock SKUs; expected a few (>=2)')
if stockout_periods<1: bad('k stockout periods','-','no stock_out ledger events')
DETAIL += ['', '## Cost medians by severity', '| Category | Vehicle | Low | Medium | High | Critical |', '|---|---|---:|---:|---:|---:|']
if len(sevframe):
    for (cat,vtype),g in sevframe.groupby(['category','vehicle']):
        vals=g.groupby('severity').cost.median()
        DETAIL.append(f'| {cat} | {vtype} | '+' | '.join(f'{vals.get(s,float("nan")):.0f}' if s in vals else '—' for s in LEVELS)+' |')
DETAIL += ['', '## Bike-to-car median ratios', '| Category | Bike median | Car median | Ratio |', '|---|---:|---:|---:|']
for cat in ALL_CATS:
    b=class_medians.get((cat,'bike'),float('nan')); c=class_medians.get((cat,'car'),float('nan'))
    DETAIL.append(f'| {cat} | {b:.0f} | {c:.0f} | {b/c:.2f} |' if pd.notna(b) and pd.notna(c) and c else f'| {cat} | n/a | n/a | n/a |')

REPORT=['# Dataset audit details','',f'Rows: {len(SERVICE)}; stock SKUs: {len(STOCK)}; ledger events: {len(LEDGER)}; vague/typo/Hinglish proxy share: {vague_share:.1%}.','']+DETAIL
(ROOT/'audit_report.md').write_text('\n'.join(REPORT)+'\n',encoding='utf-8')
parser=argparse.ArgumentParser(); parser.add_argument('--summary',action='store_true'); args=parser.parse_args()
print('| Check | Violations | 3 example job_ids |')
print('|---|---:|---|')
labels=['a catalogue','a age','a mileage','b compatibility','c bike/car identical part prices','c bike/car job cost ratio','c reference median','d combined severity','d oil change due severity','d dim lights severity','e primary fault','f multi-fault discount','g pair coverage','g dangerous pair','h template diversity','h vague/typo/Hinglish share','i job id order','i Sunday jobs','i holiday jobs','i seasonality','j opening stock','j negative stock','j negative ledger','j ledger balance','j supplier lead time','j snapshot reconciliation','j monthly reconciliation','k job count','k v2 columns','k phrase diversity','k class phrase diversity','k phrasing families','k ambiguity share','k ambiguity labels','k estimate range','k category cost ratio','k reference completeness','k explicit part price book','k severity cost monotonicity','k parts cost share','k monthly trend','k snapshot low stock','k stockout periods']
for label in labels:
    rows=CHECKS[label]; ids=', '.join(dict.fromkeys(x[0] for x in rows[:3])) or 'none'
    print(f'| {label} | {len(rows)} | {ids} |')
