# -*- coding: utf-8 -*-
"""
MOSIP Master Data Import - Registration Centers
Tables: reg_center_type, registration_center, registration_center_h,
        reg_exceptional_holiday, reg_working_nonworking

FK insert order:
  reg_center_type
    -> registration_center
       -> registration_center_h
       -> reg_exceptional_holiday
       -> reg_working_nonworking
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
    # Replace ALL float NaN with None across every column
    for col in df.columns:
        df[col] = df[col].apply(
            lambda v: None if (isinstance(v, float) and pd.isna(v)) else v
        )
    # Boolean columns
    for col in ["is_active", "is_deleted", "is_working"]:
        if col in df.columns:
            df[col] = df[col].map(
                lambda v: True  if str(v).strip().upper() == "TRUE"
                     else False if str(v).strip().upper() == "FALSE"
                     else None  if str(v).strip().upper() in ("NONE", "NAN", "")
                     else v
            )
    # Timestamp columns — replace "now()" strings
    for col in ["cr_dtimes", "upd_dtimes", "eff_dtimes", "del_dtimes"]:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda v: now if (v is not None and str(v).strip().lower() == "now()") else v
            )
    return df

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

def truncate_and_insert(df, table):
    schema, tbl = table.split(".")
    cols = ", ".join(df.columns)
    placeholders = ", ".join([f":{c}" for c in df.columns])
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE master.{tbl} CASCADE"))
        conn.execute(
            text(f"INSERT INTO {schema}.{tbl} ({cols}) VALUES ({placeholders})"),
            df.to_dict(orient="records")
        )

# ── 1. reg_center_type ────────────────────────────────────────────────────
# PK likely (code, lang_code)
def import_reg_center_type():
    df = pd.read_excel(XLSX_DIR / "reg_center_type.xlsx", dtype=str)
    df = fix_types(df)
    df = add_audit(df)
    upsert(df, "master.reg_center_type", conflict="(code, lang_code) DO NOTHING")
    print(f"OK  reg_center_type.xlsx                        -> master.reg_center_type  ({len(df)} rows)")

# ── 2. registration_center ────────────────────────────────────────────────
# PK likely (id, lang_code)
# location_code FK must exist in master.location
# Numeric fields: latitude, longitude, number_of_kiosks need casting
def import_registration_center():
    df = pd.read_excel(XLSX_DIR / "registration_center.xlsx", dtype=str)
    df = fix_types(df)
    df = add_audit(df)
    # Cast numeric columns
    for col in ["latitude", "longitude", "number_of_kiosks"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    truncate_and_insert(df, "master.registration_center")
    print(f"OK  registration_center.xlsx                    -> master.registration_center  ({len(df)} rows)")

# ── 3. registration_center_h ──────────────────────────────────────────────
# Historical mirror of registration_center + eff_dtimes column
def import_registration_center_h():
    df = pd.read_excel(XLSX_DIR / "registration_center_h.xlsx", dtype=str)
    df = fix_types(df)
    df = add_audit(df)
    for col in ["latitude", "longitude", "number_of_kiosks"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    truncate_and_insert(df, "master.registration_center_h")
    print(f"OK  registration_center_h.xlsx                  -> master.registration_center_h  ({len(df)} rows)")

# ── 4. reg_exceptional_holiday ────────────────────────────────────────────
# hol_date is a date type — parse from string
def import_reg_exceptional_holiday():
    df = pd.read_excel(XLSX_DIR / "reg_exceptional_holiday.xlsx", dtype=str)
    df = fix_types(df)
    df = add_audit(df)
    df["hol_date"] = pd.to_datetime(df["hol_date"], dayfirst=False, errors="coerce").dt.date
    # Only insert rows whose regcntr_id exists in registration_center
    with engine.begin() as conn:
        result = conn.execute(text("SELECT DISTINCT id FROM master.registration_center"))
        valid_ids = {row[0] for row in result}
    missing = set(df["regcntr_id"].unique()) - valid_ids
    if missing:
        print(f"  SKIP {len(df[df['regcntr_id'].isin(missing)])} rows — regcntr_id not in registration_center: {missing}")
        df = df[~df["regcntr_id"].isin(missing)]
    truncate_and_insert(df, "master.reg_exceptional_holiday")
    print(f"OK  reg_exceptional_holiday.xlsx                -> master.reg_exceptional_holiday  ({len(df)} rows)")

# ── 5. reg_working_nonworking ─────────────────────────────────────────────
# day_code 101-107 = Sun-Sat
def import_reg_working_nonworking():
    df = pd.read_excel(XLSX_DIR / "reg_working_nonworking.xlsx", dtype=str)
    df = fix_types(df)
    df = add_audit(df)
    # Only insert rows whose regcntr_id exists in registration_center
    with engine.begin() as conn:
        result = conn.execute(text("SELECT DISTINCT id FROM master.registration_center"))
        valid_ids = {row[0] for row in result}
    missing = set(df["regcntr_id"].unique()) - valid_ids
    if missing:
        print(f"  SKIP rows — regcntr_id not in registration_center: {missing}")
        df = df[~df["regcntr_id"].isin(missing)]
    truncate_and_insert(df, "master.reg_working_nonworking")
    print(f"OK  reg_working_nonworking.xlsx                 -> master.reg_working_nonworking  ({len(df)} rows)")

# ── Run all in FK order ───────────────────────────────────────────────────
import_reg_center_type()
import_registration_center()
import_registration_center_h()
import_reg_exceptional_holiday()
import_reg_working_nonworking()

print("\nVerifying counts...")
with engine.begin() as conn:
    result = conn.execute(text("""
        SELECT 'reg_center_type'           AS tbl, COUNT(*) FROM master.reg_center_type
        UNION ALL SELECT 'registration_center'    , COUNT(*) FROM master.registration_center
        UNION ALL SELECT 'registration_center_h'  , COUNT(*) FROM master.registration_center_h
        UNION ALL SELECT 'reg_exceptional_holiday', COUNT(*) FROM master.reg_exceptional_holiday
        UNION ALL SELECT 'reg_working_nonworking' , COUNT(*) FROM master.reg_working_nonworking
    """))
    for row in result:
        print(f"   {row[0]:30s}  {row[1]} rows")

print("\nCenters available for postal code 10104 (Hay Riad):")
with engine.begin() as conn:
    result = conn.execute(text("""
        SELECT id, name, location_code, is_active
        FROM master.registration_center
        WHERE location_code = '10104' AND lang_code = 'eng'
    """))
    rows = result.fetchall()
    if rows:
        for r in rows:
            print(f"   id={r[0]}  name={r[1]}  loc={r[2]}  active={r[3]}")
    else:
        print("   WARNING: No center found for 10104 - check location_code in xlsx")
