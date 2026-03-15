# -*- coding: utf-8 -*-
"""
MOSIP Master Data Import - Location
Tables: loc_hierarchy_list, location, loc_holiday

Insert order respects FK chain:
  loc_hierarchy_list  <-- location  <-- loc_holiday
Truncate in reverse:
  loc_holiday, location, loc_hierarchy_list
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
    df = df.where(pd.notnull(df), None)
    for col in ["is_active", "is_deleted"]:
        if col in df.columns:
            df[col] = df[col].map(
                lambda v: True  if str(v).strip().upper() == "TRUE"
                     else False if str(v).strip().upper() == "FALSE"
                     else v
            )
    return df

def bulk_insert(conn, df, schema, tbl):
    cols = ", ".join(df.columns)
    placeholders = ", ".join([f":{c}" for c in df.columns])
    conn.execute(
        text(f"INSERT INTO {schema}.{tbl} ({cols}) VALUES ({placeholders})"),
        df.to_dict(orient="records")
    )

# ── Step 1: Truncate in reverse FK order ─────────────────────────────────
print("Truncating tables in reverse FK order...")
with engine.begin() as conn:
    conn.execute(text("TRUNCATE master.loc_holiday  RESTART IDENTITY CASCADE"))
    conn.execute(text("TRUNCATE master.location     RESTART IDENTITY CASCADE"))
    conn.execute(text("TRUNCATE master.loc_hierarchy_list RESTART IDENTITY CASCADE"))
print("OK  tables cleared")

# ── Step 2: loc_hierarchy_list ────────────────────────────────────────────
# PK: (hierarchy_level, hierarchy_level_name, lang_code)
df = pd.read_excel(XLSX_DIR / "loc_hierarchy_list.xlsx", dtype=str)
df = fix_types(df)
df = add_audit(df)
# Cast hierarchy_level to int (DB column is smallint)
df["hierarchy_level"] = df["hierarchy_level"].astype(int)
with engine.begin() as conn:
    bulk_insert(conn, df, "master", "loc_hierarchy_list")
print(f"OK  loc_hierarchy_list.xlsx                    -> master.loc_hierarchy_list  ({len(df)} rows)")

# ── Step 3: location ──────────────────────────────────────────────────────
# PK: (code, lang_code)
# FK: (hierarchy_level, hierarchy_level_name, lang_code) must match loc_hierarchy_list
df = pd.read_excel(XLSX_DIR / "location.xlsx", dtype=str)
df = fix_types(df)
df = add_audit(df)
df["hierarchy_level"] = df["hierarchy_level"].astype(int)
# parent_loc_code is NULL for root location
df["parent_loc_code"] = df["parent_loc_code"].where(pd.notnull(df["parent_loc_code"]), None)
with engine.begin() as conn:
    bulk_insert(conn, df, "master", "location")
print(f"OK  location.xlsx                              -> master.location  ({len(df)} rows)")

# ── Step 4: loc_holiday ───────────────────────────────────────────────────
# PK: (id, location_code, lang_code)
# FK: (location_code, lang_code) must exist in location
# holiday_date DB type is DATE — parse from string
df = pd.read_excel(XLSX_DIR / "loc_holiday.xlsx", dtype=str)
df = fix_types(df)
df = add_audit(df)
df["id"] = df["id"].astype(int)
df["holiday_date"] = pd.to_datetime(df["holiday_date"], dayfirst=False, errors="coerce").dt.date
# Verify all location_codes exist in location table
with engine.begin() as conn:
    result = conn.execute(text("SELECT DISTINCT code FROM master.location"))
    valid_codes = {row[0] for row in result}
holiday_codes = set(df["location_code"].unique())
missing = holiday_codes - valid_codes
if missing:
    print(f"  WARNING: location_codes in loc_holiday not in location table: {missing}")
    print(f"  Skipping {len(df[df['location_code'].isin(missing)])} rows")
    df = df[~df["location_code"].isin(missing)]
with engine.begin() as conn:
    bulk_insert(conn, df, "master", "loc_holiday")
print(f"OK  loc_holiday.xlsx                           -> master.loc_holiday  ({len(df)} rows)")

# ── Verify ────────────────────────────────────────────────────────────────
print("\nVerifying counts...")
with engine.begin() as conn:
    result = conn.execute(text("""
        SELECT 'loc_hierarchy_list' AS tbl, COUNT(*) FROM master.loc_hierarchy_list
        UNION ALL SELECT 'location'        , COUNT(*) FROM master.location
        UNION ALL SELECT 'loc_holiday'     , COUNT(*) FROM master.loc_holiday
    """))
    for row in result:
        print(f"   {row[0]:25s}  {row[1]} rows")
