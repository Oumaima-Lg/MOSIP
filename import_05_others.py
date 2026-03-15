# -*- coding: utf-8 -*-
"""
MOSIP Master Data Import - Others
Tables (in FK-safe order):
  status_type, status_list,
  daysofweek_list, module_detail, process_list,
  blocklisted_words, title,
  zone, zone_user, zone_user_h
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
    # Replace ALL float NaN with None
    for col in df.columns:
        df[col] = df[col].apply(
            lambda v: None if (isinstance(v, float) and pd.isna(v)) else v
        )
    # Boolean columns
    for col in ["is_active", "is_deleted", "is_global_working"]:
        if col in df.columns:
            df[col] = df[col].map(
                lambda v: True  if str(v).strip().upper() == "TRUE"
                     else False if str(v).strip().upper() == "FALSE"
                     else None  if str(v).strip().upper() in ("NONE", "NAN", "")
                     else v
            )
    # Timestamp columns
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

def truncate_insert(df, table):
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

# â”€â”€ 1. status_type  (no FK deps) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
df = load("status_type.xlsx")
upsert(df, "master.status_type", "(code, lang_code) DO NOTHING")
print(f"OK  status_type.xlsx                            -> master.status_type          ({len(df)} rows)")

# â”€â”€ 2. status_list  (FK -> status_type.code) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
df = load("status_list.xlsx")
upsert(df, "master.status_list", "(code, lang_code) DO NOTHING")
print(f"OK  status_list.xlsx                            -> master.status_list          ({len(df)} rows)")

# â”€â”€ 3. daysofweek_list  (no FK deps) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
df = load("daysofweek_list.xlsx")
# day_seq is integer
df["day_seq"] = pd.to_numeric(df["day_seq"], errors="coerce").astype("Int64")
upsert(df, "master.daysofweek_list", "(code, lang_code) DO NOTHING")
print(f"OK  daysofweek_list.xlsx                        -> master.daysofweek_list      ({len(df)} rows)")

# â”€â”€ 4. module_detail  (no FK deps) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
df = load("module_detail.xlsx")
upsert(df, "master.module_detail", "(id, lang_code) DO NOTHING")
print(f"OK  module_detail.xlsx                          -> master.module_detail        ({len(df)} rows)")

# â”€â”€ 5. process_list  (no FK deps) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
df = load("process_list.xlsx")
upsert(df, "master.process_list", "(id, lang_code) DO NOTHING")
print(f"OK  process_list.xlsx                           -> master.process_list         ({len(df)} rows)")

# â”€â”€ 6. blocklisted_words  (no FK deps) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Table may be named blocklisted_words or blacklisted_words â€” try both
df = load("blacklisted_words.xlsx")
try:
    upsert(df, "master.blocklisted_words", "(word, lang_code) DO NOTHING")
    print(f"OK  blacklisted_words.xlsx                      -> master.blocklisted_words    ({len(df)} rows)")
except Exception:
    upsert(df, "master.blacklisted_words", "(word, lang_code) DO NOTHING")
    print(f"OK  blacklisted_words.xlsx                      -> master.blacklisted_words    ({len(df)} rows)")

# â”€â”€ 7. title  (no FK deps) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
df = load("title.xlsx")
upsert(df, "master.title", "(code, lang_code) DO NOTHING")
print(f"OK  title.xlsx                                  -> master.title                ({len(df)} rows)")

# â”€â”€ 8. zone  (self-referencing FK: parent_zone_code -> zone.code) â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Must insert root (level 0) before children â€” sort by hierarchy_level
df = load("zone.xlsx")
df["hierarchy_level"] = pd.to_numeric(df["hierarchy_level"], errors="coerce").astype("Int64")
df = df.sort_values("hierarchy_level").reset_index(drop=True)
# TRUNCATE + insert in level order to satisfy self-FK
truncate_insert(df, "master.zone")
print(f"OK  zone.xlsx                                   -> master.zone                 ({len(df)} rows)")

# â”€â”€ 9. zone_user  (FK -> zone.code) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
df = load("zone_user.xlsx")
upsert(df, "master.zone_user", "(usr_id) DO NOTHING")
print(f"OK  zone_user.xlsx                              -> master.zone_user            ({len(df)} rows)")

# â”€â”€ 10. zone_user_h  (historical, FK -> zone.code) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
df = load("zone_user_h.xlsx")
upsert(df, "master.zone_user_h", "(zone_code, usr_id, eff_dtimes) DO NOTHING")
print(f"OK  zone_user_h.xlsx                            -> master.zone_user_h          ({len(df)} rows)")

# â”€â”€ Verify â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\nVerifying counts...")
with engine.begin() as conn:
    result = conn.execute(text("""
        SELECT 'status_type'       AS tbl, COUNT(*) FROM master.status_type
        UNION ALL SELECT 'status_list'     , COUNT(*) FROM master.status_list
        UNION ALL SELECT 'daysofweek_list' , COUNT(*) FROM master.daysofweek_list
        UNION ALL SELECT 'module_detail'   , COUNT(*) FROM master.module_detail
        UNION ALL SELECT 'process_list'    , COUNT(*) FROM master.process_list
        UNION ALL SELECT 'title'           , COUNT(*) FROM master.title
        UNION ALL SELECT 'zone'            , COUNT(*) FROM master.zone
        UNION ALL SELECT 'zone_user'       , COUNT(*) FROM master.zone_user
        UNION ALL SELECT 'zone_user_h'     , COUNT(*) FROM master.zone_user_h
    """))
    for row in result:
        print(f"   {row[0]:25s}  {row[1]} rows")

