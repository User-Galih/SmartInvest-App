import os
from pathlib import Path
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from io import StringIO
from supabase import create_client

load_dotenv()

DEFAULT_SUPABASE_URL = "https://alsduqrfszpqktliknfe.supabase.co"
DEFAULT_SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFsc2R1cXJmc3pwcWt0bGlrbmZlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTQ0MjA0ODAsImV4cCI6MjEwOTk5NjQ4MH0.jq_DxhB_Y24yZcesaLy7cu2FDkcJbB5qxjYOw1PmMcU"

SUPABASE_URL = os.getenv("SUPABASE_URL") or DEFAULT_SUPABASE_URL
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or DEFAULT_SUPABASE_KEY

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Peringatan gagal inisialisasi Supabase di bi_rate_scraper: {e}")
    supabase = None

URL = "https://www.bi.go.id/id/statistik/indikator/BI-Rate.aspx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def get_hidden_fields(soup):
    fields = {}
    for field in ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"]:
        tag = soup.find("input", {"name": field})
        fields[field] = tag["value"] if tag else ""
    return fields


def scrape_all_bi_rate():
    session = requests.Session()
    session.headers.update(HEADERS)

    response = session.get(URL, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")

    all_data = []
    page = 1

    while True:
        print(f"Scraping halaman {page}")
        table = soup.find("table")
        if not table:
            break

        df = pd.read_html(StringIO(str(table)))[0]
        all_data.append(df)

        next_page = page + 1
        link = soup.find("a", string=str(next_page))
        if not link:
            print("Pagination selesai")
            break

        href = link.get("href")
        event_target = href.split("'")[1]
        hidden = get_hidden_fields(soup)

        payload = {
            "__EVENTTARGET": event_target,
            "__EVENTARGUMENT": "",
            **hidden,
        }

        response = session.post(URL, data=payload, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        page += 1

    if not all_data:
        return pd.DataFrame()

    final_df = pd.concat(all_data, ignore_index=True)
    return final_df


def seed_bi_rate_from_csv_if_empty():
    if supabase is None:
        return
    try:
        check = supabase.table("bi_rates").select("tanggal").limit(1).execute()
        if check.data:
            return
        csv_path = Path(__file__).resolve().parent.parent / "data" / "bi_rate_daily.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            rows = [
                {"tanggal": str(r["Date"]), "rate": round(float(r["BI_Rate"]) * 100, 4)}
                for _, r in df.iterrows()
            ]
            for i in range(0, len(rows), 500):
                supabase.table("bi_rates").upsert(rows[i : i + 500]).execute()
            print(f"Seeded {len(rows)} rows into bi_rates from CSV fallback.")
    except Exception as e:
        print(f"Gagal seed BI Rate dari CSV: {e}")


def save_bi_rate_to_supabase():
    if supabase is None:
        print("Supabase belum terkonfigurasi, melewati update BI Rate.")
        return

    seed_bi_rate_from_csv_if_empty()

    try:
        print("Mengambil data BI Rate...")
        df = scrape_all_bi_rate()
        if df.empty or "Tanggal" not in df.columns or "BI-Rate" not in df.columns:
            print("Data BI Rate dari website kosong atau format berubah, menggunakan data yang ada.")
            return

        df = df[["Tanggal", "BI-Rate"]]
        df.columns = ["tanggal", "rate"]

        bulan_map = {
            "Januari": "January",
            "Februari": "February",
            "Maret": "March",
            "April": "April",
            "Mei": "May",
            "Juni": "June",
            "Juli": "July",
            "Agustus": "August",
            "September": "September",
            "Oktober": "October",
            "November": "November",
            "Desember": "December",
        }

        for indo, eng in bulan_map.items():
            df["tanggal"] = df["tanggal"].str.replace(indo, eng, regex=False)

        df["tanggal"] = pd.to_datetime(df["tanggal"], dayfirst=True)
        df["rate"] = (
            df["rate"]
            .astype(str)
            .str.replace("%", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False)
            .astype(float)
        )

        rows = [
            {
                "tanggal": row["tanggal"].strftime("%Y-%m-%d"),
                "rate": float(row["rate"]),
            }
            for _, row in df.iterrows()
        ]
        if rows:
            supabase.table("bi_rates").upsert(rows).execute()
        print(f"Update BI Rate selesai ({len(rows)} baris diproses)")
    except Exception as e:
        print(f"Peringatan gagal scrape BI Rate (menggunakan fallback database/CSV): {e}")
