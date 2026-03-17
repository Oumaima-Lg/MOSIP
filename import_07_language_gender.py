"""
MOSIP Master Data Import - Language & Gender
Deletes old data before inserting from xlsx files.

Place language.xlsx and gender.xlsx in:
  C:\\Users\\olaghjibi\\MOSIP\\mosip-data-release-1.2.0\\mosip_master\\xlsx\\

Usage:
  py import_07_language_gender.py
"""

import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime

DB = dict(host="localhost", port=5432, dbname="mosip_master",
          user="masteruser", password="mosip123")

XLSX_DIR = r"C:\Users\olaghjibi\MOSIP\mosip-data-release-1.2.0\mosip_master\xlsx"
NOW = datetime.utcnow()


def conn():
    return psycopg2.connect(**DB)


def fix_types(df):
    for col in df.columns:
        df[col] = df[col].where(df[col].notna(), other=None)
        if df[col].dtype == float:
            df[col] = df[col].apply(
                lambda x: None if (x is not None and isinstance(x, float) and np.isnan(x)) else x
            )
    return df


def read_xlsx(filename):
    df = pd.read_excel(f"{XLSX_DIR}\\{filename}")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return fix_types(df)


# ── language ──────────────────────────────────────────────────────────────────
def import_language():
    print("── language ──")
    df = read_xlsx("language.xlsx")
    print(f"  rows read: {len(df)}, columns: {list(df.columns)}")

    with conn() as c:
        cur = c.cursor()
        cur.execute("DELETE FROM master.language")
        count = 0
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO master.language
                  (code, name, family, native_name, is_active,
                   cr_by, cr_dtimes, upd_by, upd_dtimes, is_deleted, del_dtimes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (code) DO UPDATE SET
                  name          = EXCLUDED.name,
                  family        = EXCLUDED.family,
                  native_name   = EXCLUDED.native_name,
                  is_active     = EXCLUDED.is_active,
                  upd_by        = %s,
                  upd_dtimes    = %s
            """, (
                row.get("code"),
                row.get("name"),
                row.get("family"),
                row.get("native_name"),
                True if row.get("is_active") is None else row.get("is_active"),
                "superadmin", NOW, None, None, False, None,
                "superadmin", NOW
            ))
            count += 1
        c.commit()
    print(f"  inserted/updated: {count}")


# ── gender ────────────────────────────────────────────────────────────────────
def import_gender():
    print("── gender ──")
    df = read_xlsx("gender.xlsx")
    print(f"  rows read: {len(df)}, columns: {list(df.columns)}")

    with conn() as c:
        cur = c.cursor()
        cur.execute("DELETE FROM master.gender")
        count = 0
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO master.gender
                  (code, lang_code, name, is_active,
                   cr_by, cr_dtimes, upd_by, upd_dtimes, is_deleted, del_dtimes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (code, lang_code) DO UPDATE SET
                  name       = EXCLUDED.name,
                  is_active  = EXCLUDED.is_active,
                  upd_by     = %s,
                  upd_dtimes = %s
            """, (
                row.get("code"),
                row.get("lang_code"),
                row.get("name"),
                True if row.get("is_active") is None else row.get("is_active"),
                "superadmin", NOW, None, None, False, None,
                "superadmin", NOW
            ))
            count += 1
        c.commit()
    print(f"  inserted/updated: {count}")


if __name__ == "__main__":
    import_language()
    import_gender()
    print("Done.")
