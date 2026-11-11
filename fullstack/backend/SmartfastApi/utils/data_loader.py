import os
import pandas as pd
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

# Load file .env
load_dotenv()

DEFAULT_SUPABASE_URL = "https://alsduqrfszpqktliknfe.supabase.co"
DEFAULT_SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFsc2R1cXJmc3pwcWt0bGlrbmZlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTQ0MjA0ODAsImV4cCI6MjEwOTk5NjQ4MH0.jq_DxhB_Y24yZcesaLy7cu2FDkcJbB5qxjYOw1PmMcU"

SUPABASE_URL = os.getenv("SUPABASE_URL") or DEFAULT_SUPABASE_URL
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or DEFAULT_SUPABASE_KEY

# Inisialisasi client Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Peringatan gagal inisialisasi Supabase di data_loader: {e}")
    supabase = None

# Lokasi folder data untuk file lokal lainnya
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def load_price_matrix():
    """
    Load price_matrix_master.csv
    Data berbentuk:
    index = Date
    columns = ticker saham
    values = harga saham
    """
    price_matrix = pd.read_csv(
        DATA_DIR / "price_matrix_master.csv",
        index_col=0,
        parse_dates=True
    )
    price_matrix.index.name = "Date"
    return price_matrix


def load_market_price():
    """
    Load market_price_ihsg.csv
    Data IHSG untuk perhitungan market return, beta, SIM, dan CAPM.
    """
    market_price = pd.read_csv(
        DATA_DIR / "market_price_ihsg.csv",
        index_col=0,
        parse_dates=True
    )
    market_price.index.name = "Date"
    return market_price


def load_bi_rate_csv_fallback():
    """
    Load data BI Rate dari CSV lokal jika Supabase kosong atau gagal diakses.
    """
    csv_path = DATA_DIR / "bi_rate_daily.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        df = df.rename(columns={"Date": "Date", "BI_Rate": "BI-Rate"})
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        return df
    return pd.DataFrame(columns=["BI-Rate"], index=pd.DatetimeIndex([]))


def load_bi_rate():
    """
    Load data BI Rate langsung dari database Supabase sebagai risk-free rate,
    dengan fallback otomatis ke bi_rate_daily.csv.
    """
    try:
        if supabase is None:
            return load_bi_rate_csv_fallback()

        response = (
            supabase.table("bi_rates")
            .select("tanggal, rate")
            .order("tanggal", desc=False)
            .execute()
        )

        bi_rate = pd.DataFrame(response.data)

        if bi_rate.empty:
            print("Peringatan: Tabel bi_rates di Supabase kosong, menggunakan CSV fallback.")
            return load_bi_rate_csv_fallback()

        bi_rate = bi_rate.rename(columns={"tanggal": "Date", "rate": "BI-Rate"})
        bi_rate["Date"] = pd.to_datetime(bi_rate["Date"])
        bi_rate.set_index("Date", inplace=True)

        return bi_rate

    except Exception as e:
        print(f"Error saat mengambil BI Rate dari Supabase ({e}), menggunakan CSV fallback.")
        return load_bi_rate_csv_fallback()


def load_clean_master_stock_data():
    """
    Optional.
    Load clean_master_stock_data.csv untuk kebutuhan EDA atau debugging.
    """
    clean_stock_data = pd.read_csv(
        DATA_DIR / "clean_master_stock_data.csv",
        parse_dates=["Date"]
    )
    return clean_stock_data


def load_stock_completeness():
    """
    Optional.
    Load stock_completeness_master.csv untuk melihat kelengkapan data saham.
    """
    stock_completeness = pd.read_csv(
        DATA_DIR / "stock_completeness_master.csv"
    )
    return stock_completeness


def load_all_data():
    """
    Load seluruh data utama SmartInvest.
    """
    return {
        "price_matrix": load_price_matrix(),
        "market_price": load_market_price(),
        "bi_rate": load_bi_rate(),
        "clean_stock_data": load_clean_master_stock_data(),
        "stock_completeness": load_stock_completeness()
    }
