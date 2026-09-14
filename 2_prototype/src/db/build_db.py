# -*- coding: utf-8 -*-
"""SQLite 정형 DB 및 별칭 테이블 구축 스크립트"""
import os
import csv
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
CSV_PATH = os.path.join(DATA_DIR, "ETF_DATA.CSV")
DB_PATH = os.path.join(DATA_DIR, "etf_spec.db")

ALIAS_MAP = {
    "360200": ["s&p500", "sp500", "에스앤피", "스앤피", "스엔피", "미국s&p500", "360200"],
    "367380": ["나스닥100", "나스닥", "nasdaq", "스닥", "나스닥백", "367380"],
    "402970": ["배당다우존스", "schd", "슈드", "미국배당", "월배당", "402970"],
    "411060": ["금현물", "금", "krx금현물", "골드", "금현믈", "411060"],
    "453850": ["미국30년", "미국국채", "장기채", "30년국채", "국채30년", "453850"],
    "465580": ["빅테크top7", "빅테크7", "m7", "top7", "빅테크", "465580"],
    "105190": ["ace 200", "코스피200", "kospi200", "200", "105190"],
    "446770": ["글로벌반도체", "반도체top4", "반도체4", "반도체", "446770"],
    "487340": ["머니마켓", "mmf", "파킹형", "단기자금", "487340"],
    "356540": ["종합채권", "회사채", "채권", "국내채권", "356540"]
}

def build_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("DROP TABLE IF EXISTS etf_spec")
    cur.execute("DROP TABLE IF EXISTS etf_alias")
    
    cur.execute("""
        CREATE TABLE etf_spec (
            ticker TEXT PRIMARY KEY,
            name TEXT,
            category TEXT,
            underlying_index TEXT,
            ter REAL,
            management_fee REAL,
            distribution_cycle TEXT,
            aum TEXT
        )
    """)
    
    cur.execute("""
        CREATE TABLE etf_alias (
            alias TEXT PRIMARY KEY,
            ticker TEXT
        )
    """)
    
    with open(CSV_PATH, "r", encoding="euc-kr") as f:
        reader = csv.DictReader(f)
        for r in reader:
            ticker = r["ticker"].strip()
            name = r["name"].strip()
            category = r["category"].strip() or ("단기자금" if "머니마켓" in name else "국내채권")
            idx = r["underlying_index"].strip()
            ter = float(r["ter(연간)"].replace("%", "").strip() or 0.0)
            mgmt = float(r["management_fee"].replace("%", "").strip() or 0.0)
            cycle = r["distribution_cycle"].strip()
            aum = r["aum"].strip()
            
            cur.execute("INSERT INTO etf_spec VALUES (?,?,?,?,?,?,?,?)",
                        (ticker, name, category, idx, ter, mgmt, cycle, aum))
            
            aliases = ALIAS_MAP.get(ticker, [])
            aliases.extend([name.lower(), name.replace("ACE ", "").lower()])
            for a in set(aliases):
                if a:
                    cur.execute("INSERT OR IGNORE INTO etf_alias VALUES (?,?)", (a, ticker))
                    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    build_db()
