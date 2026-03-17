"""
MOSIP Master Data Import - App Detail & App Role Priority
Usage: py import_08_app_detail_role_priority.py
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
                lambda x: None if (x is not None and isinstance(x, float) and np.isnan(x)) else x)
    return df

def read_xlsx(filename):
    df = pd.read_excel(f"{XLSX_DIR}\\{filename}")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return fix_types(df)

def get_role_list_columns(cur):
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema='master' AND table_name='role_list'
        ORDER BY ordinal_position
    """)
    return [r[0] for r in cur.fetchall()]

def import_app_detail():
    print("── app_detail ──")
    df = read_xlsx("app_detail.xlsx")
    print(f"  rows read: {len(df)}")
    with conn() as c:
        cur = c.cursor()
        cur.execute("DELETE FROM master.app_detail")
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO master.app_detail
                  (id, name, descr, lang_code, is_active,
                   cr_by, cr_dtimes, upd_by, upd_dtimes, is_deleted, del_dtimes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (row.get("id"), row.get("name"), row.get("descr"),
                  row.get("lang_code"),
                  True if row.get("is_active") is None else row.get("is_active"),
                  "superadmin", NOW, None, None, False, None))
        c.commit()
    print(f"  inserted: {len(df)}")

def ensure_role_list(cur, df):
    cols = get_role_list_columns(cur)
    print(f"  role_list columns: {cols}")
    roles = df[["role_code", "lang_code"]].drop_duplicates()
    for _, row in roles.iterrows():
        code = row.get("role_code")
        lang = row.get("lang_code")
        # Build insert dynamically based on actual columns
        insert_cols = ["code", "lang_code", "is_active", "cr_by", "cr_dtimes",
                       "upd_by", "upd_dtimes", "is_deleted", "del_dtimes"]
        values = [code, lang, True, "superadmin", NOW, None, None, False, None]
        # Add optional columns if they exist
        if "descr" in cols:
            insert_cols.insert(2, "descr")
            values.insert(2, code)
        placeholders = ", ".join(["%s"] * len(insert_cols))
        col_str = ", ".join(insert_cols)
        cur.execute(f"""
            INSERT INTO master.role_list ({col_str})
            VALUES ({placeholders})
            ON CONFLICT DO NOTHING
        """, values)
    print(f"  role_list: ensured {len(roles)} roles")

def import_app_role_priority():
    print("── app_role_priority ──")
    df = read_xlsx("app_role_priority.xlsx")
    print(f"  rows read: {len(df)}")
    with conn() as c:
        cur = c.cursor()
        ensure_role_list(cur, df)
        cur.execute("DELETE FROM master.app_role_priority")
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO master.app_role_priority
                  (app_id, process_id, role_code, priority, lang_code, is_active,
                   cr_by, cr_dtimes, upd_by, upd_dtimes, is_deleted, del_dtimes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (row.get("app_id"), row.get("process_id"), row.get("role_code"),
                  row.get("priority"), row.get("lang_code"),
                  True if row.get("is_active") is None else row.get("is_active"),
                  "superadmin", NOW, None, None, False, None))
        c.commit()
    print(f"  inserted: {len(df)}")

if __name__ == "__main__":
    import_app_detail()
    import_app_role_priority()
    print("Done.")
