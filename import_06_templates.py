# -*- coding: utf-8 -*-
"""
MOSIP Master Data Import - Templates
Tables: template_file_format, template_type, template
Both template_file_format and template_type FK on (code, lang_code).
Strategy: derive all needed (code, lang_code) rows from template.xlsx itself.
"""
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timezone
from pathlib import Path

XLSX_DIR = Path(r"C:\Users\olaghjibi\MOSIP\mosip-data-release-1.2.0\mosip_master\xlsx")
engine = create_engine("postgresql://masteruser:mosip123@localhost:5432/mosip_master")

def add_audit(df):
    now = datetime.now(timezone.utc)
    df = df.copy()
    if "cr_by"      not in df.columns: df["cr_by"]      = "superadmin"
    if "cr_dtimes"  not in df.columns: df["cr_dtimes"]  = now
    if "upd_by"     not in df.columns: df["upd_by"]     = None
    if "upd_dtimes" not in df.columns: df["upd_dtimes"] = None
    if "is_deleted" not in df.columns: df["is_deleted"] = False
    if "del_dtimes" not in df.columns: df["del_dtimes"] = None
    return df

def fix_types(df):
    now = datetime.now(timezone.utc)
    df = df.copy()
    for col in df.columns:
        df[col] = df[col].apply(
            lambda v: None if (isinstance(v, float) and pd.isna(v)) else v
        )
    for col in ["is_active", "is_deleted"]:
        if col in df.columns:
            df[col] = df[col].map(
                lambda v: True  if str(v).strip().upper() == "TRUE"
                     else False if str(v).strip().upper() == "FALSE"
                     else None  if str(v).strip().upper() in ("NONE","NAN","")
                     else v
            )
    for col in ["cr_dtimes", "upd_dtimes", "del_dtimes"]:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda v: now if (v is not None and str(v).strip().lower() == "now()") else v
            )
    return df

def truncate_insert(table, df):
    schema, tbl = table.split(".")
    cols = ", ".join(df.columns)
    placeholders = ", ".join([f":{c}" for c in df.columns])
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE master.{tbl} CASCADE"))
        conn.execute(
            text(f"INSERT INTO {schema}.{tbl} ({cols}) VALUES ({placeholders})"),
            df.to_dict(orient="records")
        )

def load(filename):
    df = pd.read_excel(XLSX_DIR / filename, dtype=str)
    return fix_types(add_audit(df))

def make_lookup_rows(df_source, code_col, lang_col, descr_col, descr_lookup):
    """Generate all (code, lang_code) rows needed by df_source,
    using descr_lookup dict for descriptions, falling back to code."""
    now = datetime.now(timezone.utc)
    needed = df_source[[code_col, lang_col]].dropna().drop_duplicates()
    rows = []
    for _, r in needed.iterrows():
        code = r[code_col]
        lang = r[lang_col]
        if not code or str(code).strip() in ("", "None", "nan"):
            continue
        rows.append({
            "lang_code": lang,
            "code": code,
            descr_col: descr_lookup.get(code, code),
            "is_active": True,
            "cr_by": "superadmin",
            "cr_dtimes": now,
            "upd_by": None,
            "upd_dtimes": None,
            "is_deleted": False,
            "del_dtimes": None,
        })
    return pd.DataFrame(rows).drop_duplicates(subset=["code", "lang_code"])

# ── Load template.xlsx first — it drives everything ───────────────────────
df_tmpl = load("template.xlsx")
# Drop rows with null template_typ_code or file_format_code
df_tmpl = df_tmpl[df_tmpl["template_typ_code"].notna()]
df_tmpl = df_tmpl[df_tmpl["template_typ_code"].str.strip().str.lower() != "none"]
df_tmpl = df_tmpl[df_tmpl["file_format_code"].notna()]

# ── 1. template_file_format ───────────────────────────────────────────────
# Build descr lookup from xlsx (eng rows)
df_ff_xlsx = load("template_file_format.xlsx")
ff_descr = df_ff_xlsx[df_ff_xlsx["lang_code"]=="eng"].set_index("code")["descr"].to_dict()
df_ff_final = make_lookup_rows(df_tmpl, "file_format_code", "lang_code", "descr", ff_descr)
truncate_insert("master.template_file_format", df_ff_final)
print(f"OK  template_file_format       -> master.template_file_format  ({len(df_ff_final)} rows)")

# ── 2. template_type ──────────────────────────────────────────────────────
# Build descr lookup from xlsx (eng rows)
df_tt_xlsx = load("template_type.xlsx")
df_tt_xlsx = df_tt_xlsx[df_tt_xlsx["code"].notna()]
tt_descr = df_tt_xlsx[df_tt_xlsx["lang_code"]=="eng"].set_index("code")["descr"].to_dict()
df_tt_final = make_lookup_rows(df_tmpl, "template_typ_code", "lang_code", "descr", tt_descr)
truncate_insert("master.template_type", df_tt_final)
print(f"OK  template_type              -> master.template_type          ({len(df_tt_final)} rows)")

# ── 3. template ───────────────────────────────────────────────────────────
truncate_insert("master.template", df_tmpl)
print(f"OK  template.xlsx              -> master.template               ({len(df_tmpl)} rows)")

# ── Verify ────────────────────────────────────────────────────────────────
print("\nVerifying counts...")
with engine.begin() as conn:
    result = conn.execute(text("""
        SELECT 'template_file_format' AS tbl, COUNT(*) FROM master.template_file_format
        UNION ALL SELECT 'template_type'     , COUNT(*) FROM master.template_type
        UNION ALL SELECT 'template'          , COUNT(*) FROM master.template
    """))
    for row in result:
        print(f"   {row[0]:25s}  {row[1]} rows")

print("\nConfirming key templates exist:")
with engine.begin() as conn:
    result = conn.execute(text("""
        SELECT id, name, template_typ_code, lang_code
        FROM master.template
        WHERE template_typ_code IN (
            'Onscreen-Acknowledgement',
            'otp-sms-template',
            'consent',
            'cancel-appointment'
        )
        ORDER BY template_typ_code, lang_code
    """))
    for r in result:
        print(f"   id={r[0]}  type={r[2]}  lang={r[3]}")
