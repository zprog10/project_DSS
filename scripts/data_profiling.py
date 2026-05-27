"""Data profiling for the WWI operational source.

Produces the contents of Table 1 (Summary of WWI database contents) of the P01 report.
Run with VPN ON. Outputs:
- scripts/data_profiling.json (machine-readable)
- scripts/data_profiling.md   (markdown table ready to paste in the report)

Usage:  python scripts/data_profiling.py
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)

SRC_HOST = os.getenv("SRC_HOST")
SRC_PORT = int(os.getenv("SRC_PORT", 5432))
SRC_DB = os.getenv("SRC_DB")
SRC_USER = os.getenv("SRC_USER")
SRC_PASSWORD = os.getenv("SRC_PASSWORD")

if not all([SRC_HOST, SRC_DB, SRC_USER, SRC_PASSWORD]):
    raise SystemExit("Missing SRC_* env vars in .env")


def make_engine():
    return create_engine(URL.create(
        "postgresql+psycopg2",
        username=SRC_USER, password=SRC_PASSWORD,
        host=SRC_HOST, port=SRC_PORT, database=SRC_DB,
    ))


# Logical grouping of source tables → which business event/object they represent.
# Used to render Table 1 in the report.
EVENT_OBJECT_MAP = {
    "people":               ("Employees and contacts", "object"),
    "customers":            ("Customers",              "object"),
    "customercategories":   ("Customer categories",    "object"),
    "buyinggroups":         ("Buying groups",          "object"),
    "stockitems":           ("Products / stock items", "object"),
    "stockgroups":          ("Stock groups",           "object"),
    "colors":               ("Colors",                 "object"),
    "packagetypes":         ("Package types",          "object"),
    "specialdeals":         ("Special deals",          "object"),
    "countries":            ("Countries",              "object"),
    "stateprovinces":       ("State provinces",        "object"),
    "cities":               ("Cities",                 "object"),
    "deliverymethods":      ("Delivery methods",       "object"),
    "paymentmethods":       ("Payment methods",        "object"),
    "transactiontypes":     ("Transaction types",      "object"),
    "orders":               ("Customer orders",        "event"),
    "orderlines":           ("Order lines",            "event"),
    "invoices":             ("Customer invoices",      "event"),
    "invoicelines":         ("Invoice lines",          "event"),
    "customertransactions": ("Customer transactions",  "event"),
}


def profile():
    engine = make_engine()
    started = datetime.now(timezone.utc).isoformat()
    out = {"generated_at_utc": started, "source_db": SRC_DB, "tables": []}

    with engine.connect() as conn:
        tables = [
            r[0] for r in conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_type='BASE TABLE' "
                "ORDER BY table_name"
            )).all()
        ]

        for t in tables:
            entry = {"table": t, "category": EVENT_OBJECT_MAP.get(t, (t.title(), "object"))[0],
                     "kind": EVENT_OBJECT_MAP.get(t, (t.title(), "object"))[1]}
            try:
                cols = conn.execute(text(
                    "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name=:t ORDER BY ordinal_position"
                ), {"t": t}).all()
                entry["columns"] = [{"name": c[0], "type": c[1], "nullable": c[2]} for c in cols]

                row_count = conn.execute(text(f'SELECT COUNT(*) FROM public."{t}"')).scalar()
                entry["row_count"] = int(row_count or 0)

                # Null percentage and distinct count for the first column (typically the PK)
                if cols:
                    pk = cols[0][0]
                    nulls = conn.execute(text(f'SELECT COUNT(*) FROM public."{t}" WHERE "{pk}" IS NULL')).scalar()
                    distinct = conn.execute(text(f'SELECT COUNT(DISTINCT "{pk}") FROM public."{t}"')).scalar()
                    entry["pk_column"] = pk
                    entry["pk_null_count"] = int(nulls or 0)
                    entry["pk_distinct_count"] = int(distinct or 0)
                    entry["pk_uniqueness_pct"] = (100.0 * (distinct or 0) / row_count) if row_count else None
            except Exception as e:
                entry["error"] = str(e)
            out["tables"].append(entry)

    out_json = ROOT / "scripts" / "data_profiling.json"
    out_json.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")

    # Markdown table — Table 1 of the report
    lines = [
        "# Table 1 — Summary of WWI database contents",
        "",
        f"_Source database: `{SRC_DB}` · generated: {started} UTC_",
        "",
        "| Event / object | Table | Nr. records | Nr. columns | PK | PK uniqueness |",
        "|---|---|---:|---:|---|---:|",
    ]
    for e in out["tables"]:
        if "error" in e:
            lines.append(f"| {e['category']} | `{e['table']}` | ERROR: {e['error']} | | | |")
            continue
        uniq = f"{e['pk_uniqueness_pct']:.2f}%" if e.get("pk_uniqueness_pct") is not None else "—"
        lines.append(
            f"| {e['category']} | `{e['table']}` | {e['row_count']:,} | {len(e['columns'])} | "
            f"`{e.get('pk_column','—')}` | {uniq} |"
        )
    out_md = ROOT / "scripts" / "data_profiling.md"
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {out_json.relative_to(ROOT)}")
    print(f"Wrote {out_md.relative_to(ROOT)}")
    print(f"Profiled {len(out['tables'])} tables.")


if __name__ == "__main__":
    profile()
