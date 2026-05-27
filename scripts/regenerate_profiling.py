import os, csv, json
from datetime import datetime, timezone

root = os.path.dirname(os.path.dirname(__file__))
ss_dir = os.path.join(root, 'tmp_snapshots')
out_md = os.path.join(root, 'scripts', 'data_profiling.md')
out_json = os.path.join(root, 'scripts', 'data_profiling.json')
rows = []
for fn in sorted(os.listdir(ss_dir)):
    if not fn.lower().endswith('.csv'):
        continue
    path = os.path.join(ss_dir, fn)
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            header = []
        cols = len(header)
        count = 0
        pk_name = None
        for h in header:
            if h.lower().endswith('id'):
                pk_name = h
                break
        pk_values = set()
        if pk_name:
            idx = header.index(pk_name)
            for r in reader:
                count += 1
                if len(r) > idx:
                    pk_values.add(r[idx])
        else:
            for _ in reader:
                count += 1
        pk = pk_name if pk_name else ''
        pk_unique = None
        if pk_name and count>0:
            pk_unique = 100.0 * (len(pk_values) / count)
        rows.append({
            'table': os.path.splitext(fn)[0],
            'nr_records': count,
            'nr_columns': cols,
            'pk': pk,
            'pk_uniqueness': f"{pk_unique:.2f}%" if pk_unique is not None else ''
        })

meta = {'generated': datetime.now(timezone.utc).isoformat(), 'source_dir': 'tmp_snapshots'}
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump({'meta': meta, 'tables': rows}, f, indent=2)

lines = []
lines.append('# Table 1 — Summary of WWI database contents')
lines.append('')
lines.append(f"_Source snapshots dir: `tmp_snapshots/` · generated: {meta['generated']} UTC_")
lines.append('')
lines.append('| Event / object | Table | Nr. records | Nr. columns | PK | PK uniqueness |')
lines.append('|---|---|---:|---:|---|---:|')
for r in rows:
    display = r['table'].replace('_',' ')
    lines.append(f"| {display.title()} | `{r['table']}` | {r['nr_records']:,} | {r['nr_columns']} | `{r['pk']}` | {r['pk_uniqueness']} |")
with open(out_md, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print('Generated:', out_md, out_json)
