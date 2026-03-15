# -*- coding: utf-8 -*-
"""
MOSIP Master Data Import - ID Schema
Tables: identity_schema, dynamic_field, id_type, ui_spec
"""
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timezone
from pathlib import Path
import re, json

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

    # Step 1 — replace every float NaN with None across ALL columns
    # (covers del_dtimes, upd_dtimes, and any other nullable column)
    for col in df.columns:
        df[col] = df[col].apply(
            lambda v: None if (isinstance(v, float) and pd.isna(v)) else v
        )

    # Step 2 — cast boolean columns
    for col in ["is_active", "is_deleted", "add_props"]:
        if col in df.columns:
            df[col] = df[col].map(
                lambda v: True  if str(v).strip().upper() == "TRUE"
                     else False if str(v).strip().upper() == "FALSE"
                     else None  if str(v).strip().upper() in ("NONE", "NAN", "")
                     else v
            )

    # Step 3 — replace "now()" strings with real datetime in timestamp columns
    ts_cols = ["cr_dtimes", "upd_dtimes", "effective_from", "del_dtimes"]
    for col in ts_cols:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda v: now if (v is not None and str(v).strip().lower() == "now()") else v
            )
    return df

def bulk_insert(df, table):
    schema, tbl = table.split(".")
    cols = ", ".join(df.columns)
    placeholders = ", ".join([f":{c}" for c in df.columns])
    with engine.begin() as conn:
        conn.execute(
            text(f"INSERT INTO {schema}.{tbl} ({cols}) VALUES ({placeholders})"),
            df.to_dict(orient="records")
        )

def upsert(df, table, conflict):
    schema, tbl = table.split(".")
    cols = ", ".join(df.columns)
    placeholders = ", ".join([f":{c}" for c in df.columns])
    sql = text(
        f"INSERT INTO {schema}.{tbl} ({cols}) VALUES ({placeholders}) "
        f"ON CONFLICT {conflict}"
    )
    with engine.begin() as conn:
        conn.execute(sql, df.to_dict(orient="records"))

# ── 1. identity_schema ────────────────────────────────────────────────────
def import_identity_schema():
    df = pd.read_excel(XLSX_DIR / "identity_schema.xlsx", dtype=str)
    df = fix_types(df)
    df = add_audit(df)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE master.identity_schema CASCADE"))
    bulk_insert(df, "master.identity_schema")
    print(f"OK  identity_schema.xlsx                        -> master.identity_schema  ({len(df)} rows)")

# ── 2. dynamic_field ──────────────────────────────────────────────────────
def import_dynamic_field():
    df = pd.read_excel(XLSX_DIR / "dynamic_field.xlsx", dtype=str)
    df["value_json"] = df["value_json"].map(
        lambda v: re.sub(r",\s*}", "}", str(v).strip()) if pd.notna(v) else v
    )
    df = fix_types(df)
    df = add_audit(df)
    upsert(df, "master.dynamic_field", conflict="(id) DO NOTHING")
    print(f"OK  dynamic_field.xlsx                          -> master.dynamic_field  ({len(df)} rows)")

# ── 3. id_type ────────────────────────────────────────────────────────────
def import_id_type():
    df = pd.read_excel(XLSX_DIR / "id_type.xlsx", dtype=str)
    df = fix_types(df)
    df = add_audit(df)
    upsert(df, "master.id_type", conflict="(code, lang_code) DO NOTHING")
    print(f"OK  id_type.xlsx                                -> master.id_type  ({len(df)} rows)")

# ── 4. ui_spec ────────────────────────────────────────────────────────────
def import_ui_spec():
    df = pd.read_excel(XLSX_DIR / "ui_spec.xlsx", dtype=str)
    df = fix_types(df)
    df = add_audit(df)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM master.ui_spec WHERE domain = 'pre-registration'"))
        print("     (deleted existing pre-registration ui_spec)")
    upsert(
        df, "master.ui_spec",
        conflict="(domain, type, version, identity_schema_id) DO NOTHING"
    )
    print(f"OK  ui_spec.xlsx                                -> master.ui_spec  ({len(df)} rows)")
    with engine.begin() as conn:
        result = conn.execute(text(
            "SELECT json_spec FROM master.ui_spec WHERE domain = 'pre-registration' LIMIT 1"
        ))
        row = result.fetchone()
        if row:
            fields = json.loads(row[0]).get("identity", {}).get("identity", [])
            doc_fields = [f["id"] for f in fields if f.get("controlType") == "fileupload"]
            print(f"     fileupload fields: {doc_fields}")
        else:
            print("     WARNING: pre-registration ui_spec not found after insert!")

# ── Run ───────────────────────────────────────────────────────────────────
import_identity_schema()
import_dynamic_field()
import_id_type()
import_ui_spec()

print("\nVerifying counts...")
with engine.begin() as conn:
    result = conn.execute(text("""
        SELECT 'identity_schema' AS tbl, COUNT(*) FROM master.identity_schema
        UNION ALL SELECT 'dynamic_field'  , COUNT(*) FROM master.dynamic_field
        UNION ALL SELECT 'id_type'        , COUNT(*) FROM master.id_type
        UNION ALL SELECT 'ui_spec'        , COUNT(*) FROM master.ui_spec
    """))
    for row in result:
        print(f"   {row[0]:20s}  {row[1]} rows")
