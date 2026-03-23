# -*- coding: utf-8 -*-
"""
MOSIP Master Data Import — Documents
Tables: doc_category, doc_type, valid_document, applicant_valid_document
"""
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timezone
from pathlib import Path

XLSX_DIR = Path(r"C:\Users\olaghjibi\MOSIP\mosip-data-release-1.2.0\mosip_master\xlsx")
engine = create_engine("postgresql://masteruser:mosip123@localhost:5432/mosip_master")

files = {
    "doc_category.xlsx":             "master.doc_category",
    "doc_type.xlsx":                 "master.doc_type",
    "valid_document.xlsx":           "master.valid_document",
    "applicant_valid_document.xlsx": "master.applicant_valid_document",
}

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

def upsert(df, table):
    schema, tbl = table.split(".")
    cols = ", ".join(df.columns)
    placeholders = ", ".join([f":{c}" for c in df.columns])
    sql = text(f"INSERT INTO {schema}.{tbl} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING")
    with engine.begin() as conn:
        conn.execute(sql, df.to_dict(orient="records"))

for file, table in files.items():
    path = XLSX_DIR / file
    if not path.exists():
        print(f"SKIP {file} - not found at {path}")
        continue
    df = pd.read_excel(path, dtype=str)
    df = fix_types(df)
    df = add_audit(df)
    upsert(df, table)
    print(f"OK  {file:45s} -> {table}  ({len(df)} rows)")

print("\nVerifying counts...")
with engine.begin() as conn:
    result = conn.execute(text("""
        SELECT 'doc_category'              AS tbl, COUNT(*) FROM master.doc_category
        UNION ALL SELECT 'doc_type'             , COUNT(*) FROM master.doc_type
        UNION ALL SELECT 'valid_document'       , COUNT(*) FROM master.valid_document
        UNION ALL SELECT 'applicant_valid_doc'  , COUNT(*) FROM master.applicant_valid_document
    """))
    for row in result:
        print(f"   {row[0]:30s}  {row[1]} rows")
