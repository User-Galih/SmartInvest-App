import keras
import tensorflow as tf
import joblib
import pandas as pd
import numpy as np
import zipfile
import json
import math
from datetime import datetime
from pathlib import Path
from dateutil.relativedelta import relativedelta
import os
from supabase import create_client, Client

from services.genai_service import (
    generate_market_summary,
    generate_recommendation_summary
)
from utils.data_loader import load_all_data
from constants.index_map import INDEX_MAP
from utils.dynamic_filtering import dynamic_filtering
from utils.feature_engineering import feature_engineering
from utils.portfolio_models import compare_all_models, run_selected_model
from services.stock_analysis_service import predict_stock_trend
from utils.portfolio_scoring import composite_portfolio_scoring

# Ambil kredensial lingkungan dari file .env backend (dengan fallback default)
DEFAULT_SUPABASE_URL = "https://alsduqrfszpqktliknfe.supabase.co"
DEFAULT_SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFsc2R1cXJmc3pwcWt0bGlrbmZlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTQ0MjA0ODAsImV4cCI6MjEwOTk5NjQ4MH0.jq_DxhB_Y24yZcesaLy7cu2FDkcJbB5qxjYOw1PmMcU"

SUPABASE_URL = os.getenv("SUPABASE_URL") or DEFAULT_SUPABASE_URL
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or DEFAULT_SUPABASE_KEY

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Peringatan: Gagal inisialisasi Supabase di ihsg_service: {e}")
    supabase: Client = None
# ==============================================================================
# TICKER METADATA MAPPING (LQ45 & IDX30 Stocks)
# ==============================================================================
TICKER_DETAILS = {
    "AADI.JK": {"fullname": "PT Adaro Andalan Indonesia Tbk", "sector": "Energy"},
    "ADMR.JK": {"fullname": "PT Adaro Minerals Indonesia Tbk", "sector": "Basic Materials"},
    "ADRO.JK": {"fullname": "PT Adaro Energy Indonesia Tbk", "sector": "Energy"},
    "AKRA.JK": {"fullname": "PT AKR Corporindo Tbk", "sector": "Energy"},
    "AMMN.JK": {"fullname": "PT Amman Mineral Internasional Tbk", "sector": "Basic Materials"},
    "AMRT.JK": {"fullname": "PT Sumber Alfaria Trijaya Tbk", "sector": "Consumer Cyclical"},
    "ANTM.JK": {"fullname": "PT Aneka Tambang Tbk", "sector": "Basic Materials"},
    "ARTO.JK": {"fullname": "PT Bank Jago Tbk", "sector": "Financial Services"},
    "ASII.JK": {"fullname": "PT Astra International Tbk", "sector": "Industrials"},
    "BBCA.JK": {"fullname": "PT Bank Central Asia Tbk", "sector": "Financial Services"},
    "BBNI.JK": {"fullname": "PT Bank Negara Indonesia (Persero) Tbk", "sector": "Financial Services"},
    "BBRI.JK": {"fullname": "PT Bank Rakyat Indonesia (Persero) Tbk", "sector": "Financial Services"},
    "BBTN.JK": {"fullname": "PT Bank Tabungan Negara (Persero) Tbk", "sector": "Financial Services"},
    "BMRI.JK": {"fullname": "PT Bank Mandiri (Persero) Tbk", "sector": "Financial Services"},
    "BRIS.JK": {"fullname": "PT Bank Syariah Indonesia Tbk", "sector": "Financial Services"},
    "BRPT.JK": {"fullname": "PT Barito Pacific Tbk", "sector": "Basic Materials"},
    "CPIN.JK": {"fullname": "PT Charoen Pokphand Indonesia Tbk", "sector": "Consumer Defensive"},
    "CTRA.JK": {"fullname": "PT Ciputra Development Tbk", "sector": "Real Estate"},
    "ESSA.JK": {"fullname": "PT Essa Industri Indonesia Tbk", "sector": "Basic Materials"},
    "EXCL.JK": {"fullname": "PT XL Axiata Tbk", "sector": "Communication Services"},
    "GOTO.JK": {"fullname": "PT GoTo Gojek Tokopedia Tbk", "sector": "Technology"},
    "ICBP.JK": {"fullname": "PT Indofood CBP Sukses Makmur Tbk", "sector": "Consumer Defensive"},
    "INCO.JK": {"fullname": "PT Vale Indonesia Tbk", "sector": "Basic Materials"},
    "INDF.JK": {"fullname": "PT Indofood Sukses Makmur Tbk", "sector": "Consumer Defensive"},
    "INKP.JK": {"fullname": "PT Indah Kiat Pulp & Paper Tbk", "sector": "Basic Materials"},
    "ISAT.JK": {"fullname": "PT Indosat Ooredoo Hutchison Tbk", "sector": "Communication Services"},
    "ITMG.JK": {"fullname": "PT Indo Tambangraya Megah Tbk", "sector": "Energy"},
    "JPFA.JK": {"fullname": "PT Japfa Comfeed Indonesia Tbk", "sector": "Consumer Defensive"},
    "JSMR.JK": {"fullname": "PT Jasa Marga (Persero) Tbk", "sector": "Industrials"},
    "KLBF.JK": {"fullname": "PT Kalbe Farma Tbk", "sector": "Healthcare"},
    "MAPA.JK": {"fullname": "PT Map Aktif Adiperkasa Tbk", "sector": "Consumer Cyclical"},
    "MAPI.JK": {"fullname": "PT Mitra Adiperkasa Tbk", "sector": "Consumer Cyclical"},
    "MBMA.JK": {"fullname": "PT Merdeka Battery Materials Tbk", "sector": "Basic Materials"},
    "MDKA.JK": {"fullname": "PT Merdeka Copper Gold Tbk", "sector": "Basic Materials"},
    "MEDC.JK": {"fullname": "PT Medco Energi Internasional Tbk", "sector": "Energy"},
    "PGAS.JK": {"fullname": "PT Perusahaan Gas Negara Tbk", "sector": "Utilities"},
    "PGEO.JK": {"fullname": "PT Pertamina Geothermal Energy Tbk", "sector": "Utilities"},
    "PTBA.JK": {"fullname": "PT Bukit Asam Tbk", "sector": "Energy"},
    "SIDO.JK": {"fullname": "PT Industri Jamu dan Farmasi Sido Muncul Tbk", "sector": "Consumer Defensive"},
    "SMGR.JK": {"fullname": "PT Semen Indonesia (Persero) Tbk", "sector": "Basic Materials"},
    "TLKM.JK": {"fullname": "PT Telkom Indonesia (Persero) Tbk", "sector": "Communication Services"},
    "TOWR.JK": {"fullname": "PT Sarana Menara Nusantara Tbk", "sector": "Communication Services"},
    "UNTR.JK": {"fullname": "PT United Tractors Tbk", "sector": "Industrials"},
    "UNVR.JK": {"fullname": "PT Unilever Indonesia Tbk", "sector": "Consumer Defensive"},
    "WIFI.JK": {"fullname": "PT Solusi Sinergi Digital Tbk", "sector": "Technology"}
}

# ==========================
# PATH
# ==========================
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "ihsg_best_model_3class.keras"
SCALER_PATH = BASE_DIR / "assets" / "ihsg_scaler_global.pkl"
DATA_PATH = BASE_DIR / "data" / "market_price_ihsg.csv"

# ==============================================================================
# SAFE LOAD MODEL FOR .keras FORMAT (ZIP CONFIG CLEANER VIA OFFICIAL API)
# ==============================================================================
def safe_load_ihsg_model(model_path):
    with zipfile.ZipFile(model_path, "r") as z:
        config_bytes = z.read("config.json")
        config_dict = json.loads(config_bytes.decode("utf-8"))

    def clean_config(node):
        if isinstance(node, dict):
            node.pop("quantization_config", None)
            node.pop("use_gate", None)
            node.pop("renorm", None)
            node.pop("renorm_clipping", None)
            node.pop("renorm_momentum", None)
            for k, v in list(node.items()):
                clean_config(v)
        elif isinstance(node, list):
            for item in node:
                clean_config(item)

    clean_config(config_dict)
    model = keras.saving.deserialize_keras_object(config_dict)
    model.load_weights(model_path)
    return model

# Load Model Execution
model = safe_load_ihsg_model(str(MODEL_PATH))
scaler = joblib.load(SCALER_PATH)
ihsg_data = pd.read_csv(DATA_PATH, index_col=0, parse_dates=True, engine="python")

def build_ihsg_features(df):
    df = df.copy()
    close_col = df.columns[0]

    df["Return"] = df[close_col].pct_change()
    df["MA20"] = df[close_col].rolling(20).mean()
    df["MA50"] = df[close_col].rolling(50).mean()
    df["Volatilitas"] = df["Return"].rolling(20).std()
    df["Volume_Log"] = 0
    df["RSI"] = 50
    df["MACD"] = df["MA20"] - df["MA50"]
    df["MA_Gap"] = (df["MA20"] - df["MA50"]) / (df["MA50"] + 1e-10)
    df["BB_Width"] = df["Return"].rolling(20).std()
    df["ROC5"] = df[close_col].pct_change(5)
    df["Trend_Strength"] = df["MA_Gap"].abs()

    return df.dropna()

def predict_ihsg(end_date=None, gemini_api_key=None):
    feature_cols = [
        "Return", "MA20", "MA50", "Volatilitas", "Volume_Log",
        "RSI", "MACD", "MA_Gap", "BB_Width", "ROC5", "Trend_Strength"
    ]
    time_steps = 15

    if end_date is not None:
        try:
            df_filtered = ihsg_data.loc[:end_date]
            if len(df_filtered) < 80:
                df_filtered = ihsg_data
        except Exception:
            df_filtered = ihsg_data
    else:
        df_filtered = ihsg_data

    df = build_ihsg_features(df_filtered)
    X_scaled = scaler.transform(df[feature_cols].values)
    X_pred = X_scaled[-time_steps:].reshape(1, time_steps, len(feature_cols))

    prediction = model.predict(X_pred, verbose=0)[0]
    idx = int(np.argmax(prediction))

    labels = ["Bearish", "Sideways", "Bullish"]
    trend = labels[idx]
    confidence = round(float(prediction[idx]), 4)

    if trend == "Bullish":
        recommended_method = "SIM"
        market_condition = "Pasar sedang bullish"
        reason = "SIM lebih optimal untuk momentum pasar naik."
    elif trend == "Bearish":
        recommended_method = "CAPM"
        market_condition = "Pasar sedang bearish"
        reason = "CAPM lebih cocok untuk defensif di kondisi pasar menurun."
    else:
        recommended_method = "MVEP"
        market_condition = "Pasar sideways"
        reason = "MVEP membantu optimasi risk-return saat pasar stabil."

    market_summary = generate_market_summary(
        market_trend=trend,
        confidence=confidence,
        market_condition=market_condition,
        recommended_method=recommended_method,
        reason=reason,
        gemini_api_key=gemini_api_key
    )

    return {
        "market_trend": trend,
        "confidence": confidence,
        "prediction_class": idx,
        "recommended_method": recommended_method,
        "market_condition": market_condition,
        "reason": reason,
        "market_summary": market_summary
    }

def clean_nan(obj):
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan(i) for i in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj

# ==============================================================================
# PIPELINE: PREDICT IHSG & PORTFOLIO ALLOCATION (⚡ REPAIRED SINKRONISASI TOTAL ⚡)
# ==============================================================================
def predict_ihsg_with_portfolio(
    index_choice: str,
    start_date: str,
    end_date: str,
    investment_amount: float,
    user_id: str = None, # ⚡ Argumen user_id untuk menerima kiriman data form React
    gemini_api_key: str = None
):
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    period_years = (end_dt - start_dt).days / 365.25

    # tanggal akhir harus > awal
    if end_dt <= start_dt:
        raise ValueError("Tanggal akhir harus setelah tanggal mulai")

    delta = relativedelta(end_dt, start_dt)
    total_months = (delta.years * 12 + delta.months)

    # minimal 6 bulan (toleransi perbedaan jumlah hari akhir bulan 30 vs 31 hari)
    if total_months < 6 and (end_dt - start_dt).days < 175:
        raise ValueError("Periode minimal 6 bulan")

    # maksimal 5 tahun
    if delta.years > 5 or (delta.years == 5 and (delta.months > 0 or delta.days > 5)):
        raise ValueError("Periode maksimal 5 tahun")

    # ==========================
    # 1. LOAD DATA
    # ==========================
    data = load_all_data()
    price_matrix = data["price_matrix"]
    market_price = data["market_price"]
    bi_rate = data["bi_rate"]

    # ==========================
    # 2. DYNAMIC FILTERING
    # ==========================
    filtered_result = dynamic_filtering(
        index_choice=index_choice.upper(),
        start_date=start_date,
        end_date=end_date,
        price_matrix=price_matrix,
        market_price=market_price,
        bi_rate_daily=bi_rate,
        index_map=INDEX_MAP
    )

    # ==========================
    # 3. FEATURE ENGINEERING
    # ==========================
    feature_result = feature_engineering(
        filtered_price=filtered_result["filtered_price"],
        filtered_market=filtered_result["filtered_market"],
        filtered_bi_rate=filtered_result["filtered_bi_rate"]
    )

    # ==========================
    # 4. PREDICT IHSG TREND
    # ==========================
    ihsg_res = predict_ihsg(end_date=end_date, gemini_api_key=gemini_api_key)
    market_trend = ihsg_res["market_trend"]
    confidence = ihsg_res["confidence"]
    prediction_class = ihsg_res["prediction_class"]

    # ==========================
    # 5. COMPARE MODELS
    # ==========================
    compare_result = compare_all_models(
        feature_result=feature_result,
        investment_amount=investment_amount
    )
    comparison = compare_result["comparison_df"].to_dict(orient="records")

    portfolios = {}
    for item in comparison:
        portfolios[item["Model"]] = {
            "annual_return": item["Annual Return"],
            "annual_risk": item["Annual Risk"],
            "sharpe_ratio": item["Sharpe Ratio"],
            "alpha": item["Alpha"] if item["Alpha"] is not None else 0.0,
            "beta": item["Beta"] if item["Beta"] is not None else 1.0
        }

    # ==========================
    # 6. PICK BEST METHOD BASED ON TREND
    # ==========================
    scores = {}
    max_sharpe = max(p["sharpe_ratio"] for p in portfolios.values())
    min_risk = min(p["annual_risk"] for p in portfolios.values())
    max_risk = max(p["annual_risk"] for p in portfolios.values())

    for name, p in portfolios.items():
        if market_trend == "Bullish":
            scores[name] = round(float(p["sharpe_ratio"]), 3)
        elif market_trend == "Bearish":
            scores[name] = round(float(p["annual_risk"]), 4)
        else:
            sh_score = p["sharpe_ratio"] / max_sharpe if max_sharpe > 0 else 0
            rk_score = 1 - ((p["annual_risk"] - min_risk) / (max_risk - min_risk)) if max_risk > min_risk else 1
            scores[name] = round(0.6 * sh_score + 0.4 * rk_score, 3)

    if market_trend == "Bullish":
        best_method = max(scores, key=scores.get)
        trend_label = "NAIK (Bullish)"
        selection_reason = f"IHSG diprediksi {trend_label} → Fokus Sharpe Ratio tertinggi: {best_method} dengan skor {scores[best_method]:.3f} (SIM: {scores.get('SIM', 0.0):.3f}, MVEP: {scores.get('MVEP', 0.0):.3f}, CAPM: {scores.get('CAPM', 0.0):.3f})"
    elif market_trend == "Bearish":
        best_method = min(scores, key=scores.get)
        trend_label = "TURUN (Bearish)"
        selection_reason = f"IHSG diprediksi {trend_label} → Fokus Risk / Volatilitas terendah: {best_method} dengan skor {scores[best_method]:.4f} (SIM: {scores.get('SIM', 0.0):.4f}, MVEP: {scores.get('MVEP', 0.0):.4f}, CAPM: {scores.get('CAPM', 0.0):.4f})"
    else:
        best_method = max(scores, key=scores.get)
        trend_label = "STABIL (Sideways)"
        selection_reason = f"IHSG diprediksi {trend_label} → Keseimbangan Sharpe Ratio & Risk (Hybrid): {best_method} dengan skor {scores[best_method]:.3f} (SIM: {scores.get('SIM', 0.0):.3f}, MVEP: {scores.get('MVEP', 0.0):.3f}, CAPM: {scores.get('CAPM', 0.0):.3f})"

    # ==========================
    # 7. RUN SELECTED WINNER MODEL
    # ==========================
    result = run_selected_model(
        model_choice=best_method,
        feature_result=feature_result,
        investment_amount=investment_amount
    )

    # ==========================
    # 8. FILTER NON-ZERO WEIGHTS
    # ==========================
    weights_df = result["weights"]
    weights_df = weights_df[weights_df["Weight"].abs() > 0.0001]

    # ==========================
    # 9. BUILD PORTFOLIO LIST
    # ==========================
    portfolio = []
    for _, row in weights_df.iterrows():
        ticker = row["Ticker"]
        stock_prediction = predict_stock_trend(ticker)

        try:
            current_price = float(filtered_result["filtered_price"][ticker].dropna().iloc[-1])
        except Exception:
            current_price = 0.0

        if current_price > 0:
            shares = row["Allocation"] / current_price
            lot = round(shares / 100, 2)
            integer_lot = int(shares / 100)
        else:
            shares = 0.0
            lot = 0.0
            integer_lot = 0

        meta = TICKER_DETAILS.get(ticker, {"fullname": f"PT {ticker.split('.')[0]} Tbk", "sector": "Lainnya"})

        item = {
            "ticker": ticker,
            "fullname": meta["fullname"],
            "sector": meta["sector"],
            "current_price": round(current_price, 2) if current_price > 0 else None,
            "weight": round(float(row["Weight"]), 4),
            "allocation": round(float(row["Allocation"]), 2),
            "shares": round(shares, 2) if current_price > 0 else None,
            "lot": lot if current_price > 0 else None,
            "integer_lot": integer_lot if current_price > 0 else None,
            "trend": stock_prediction["trend"],
            "confidence": stock_prediction["confidence"],
            "recommendation": stock_prediction["recommendation"]
        }
        if result["method"] in ["SIM", "CAPM"]:
            if "alpha" in row.index:
                item["alpha"] = round(float(row["alpha"]), 4)
            if "beta" in row.index:
                item["beta"] = round(float(row["beta"]), 4)
        portfolio.append(item)

    # ==========================
    # 10. SCORING & METHOD COMPARISON
    # ==========================
    method_comparison = []
    for name, p in portfolios.items():
        final_score = float(scores.get(name, 0.0))
        comp_beta = None
        comp_alpha = None
        if name == "SIM":
            sim_res = compare_result["SIM"]
            comp_beta = round(float(sim_res["weights"]["beta"].mean()), 2) if "beta" in sim_res["weights"].columns else 1.00
            comp_alpha = round(float(sim_res["weights"]["alpha"].mean()), 4) if "alpha" in sim_res["weights"].columns else -0.0005
        elif name == "CAPM":
            capm_res = compare_result["CAPM"]
            comp_beta = round(float(capm_res["weights"]["beta"].mean()), 2) if "beta" in capm_res["weights"].columns else 0.98
            comp_alpha = round(float(capm_res["weights"]["alpha"].mean()), 4) if "alpha" in capm_res["weights"].columns else -0.0103

        method_comparison.append({
            "method": name,
            "return": round(float(p["annual_return"]), 4),
            "risk": round(float(p["annual_risk"]), 4),
            "sharpe": round(float(p["sharpe_ratio"]), 3),
            "beta": comp_beta,
            "alpha": comp_alpha,
            "final_score": final_score,
            "is_best": name == best_method
        })

    # ==========================
    # 11. SUMMARY METRICS & INJECTION RATE
    # ==========================
    annual_return_pct = round(float(result["portfolio_annual_return"]) * 100, 2)
    annual_risk_pct = round(float(result["portfolio_annual_risk"]) * 100, 2)
    sharpe_ratio_val = round(float(result["sharpe_ratio"]), 3)

    alpha_values = [item["alpha"] for item in portfolio if "alpha" in item]
    beta_values = [item["beta"] for item in portfolio if "beta" in item]
    alpha_avg = round(sum(alpha_values) / len(alpha_values), 4) if alpha_values else None
    beta_avg = round(sum(beta_values) / len(beta_values), 4) if beta_values else None

    risk_free_rate_pct = float(feature_result["annual_risk_free_rate"] * 100)
    bi_rate_pct = round(risk_free_rate_pct, 3)

    if beta_avg is not None and beta_avg != 0:
        treynor_ratio = round((annual_return_pct - risk_free_rate_pct) / beta_avg, 4)
    else:
        treynor_ratio = None

    # ==========================
    # 12. GENAI INTERPRETATION
    # ==========================
    try:
        horizon_yr = round(period_years, 1)
        gain_ex = int(investment_amount * float(result["portfolio_annual_return"]))
        loss_ex = int(investment_amount * float(result["portfolio_annual_risk"]))
        
        alloc_items = [f"* {item['ticker'].replace('.JK', '')} ({item['weight']*100:.1f}%)" for item in portfolio]
        alloc_str = "\n".join(alloc_items)

        comparison_lines = []
        for m in method_comparison:
            best_tag = " [Metode Terbaik]" if m["is_best"] else ""
            comparison_lines.append(f"- Metode {m['method']}: Expected Return {m['return']*100:.1f}%, Risiko {m['risk']*100:.1f}%, Sharpe Ratio {m['sharpe']:.3f}{best_tag}")
        comparison_str = "\n".join(comparison_lines)

        market_trend_str = f"naik ({market_trend})" if market_trend == "Bullish" else f"turun ({market_trend})" if market_trend == "Bearish" else f"sideways ({market_trend})"

        ai_interpretation = generate_recommendation_summary(
            best_method=best_method,
            bi_rate=bi_rate_pct,
            market_trend_str=market_trend_str,
            confidence=confidence,
            horizon_yr=horizon_yr,
            ret_pct=annual_return_pct,
            risk_pct=annual_risk_pct,
            sharpe=sharpe_ratio_val,
            beta=beta_avg,
            gain_ex=gain_ex,
            loss_ex=loss_ex,
            alloc_str=alloc_str,
            comparison_str=comparison_str,
            investment_amount=int(investment_amount),
            index_choice=index_choice,
            gemini_api_key=gemini_api_key
        )
    except Exception as e:
        ai_interpretation = f"GenAI Error: {str(e)}"

    # ==========================
    # 13. CONSTRUCT OUTPUT JSON (⚡ RUMUS RUPIAH DI-SINKRONKAN ⚡)
    # ==========================
    trading_days = filtered_result["filtering_summary"]["trading_days_used"]
    portfolio_allocation = []
    for item in portfolio:
        portfolio_allocation.append({
            "ticker": item["ticker"],
            "fullname": item["fullname"],
            "sector": item["sector"],
            "current_price": item["current_price"],
            "weight": round(item["weight"], 3),
            "allocated_amount": int(item["allocation"]),
            "shares": item["shares"],
            "lot": item["lot"],
            "integer_lot": item["integer_lot"],
            "trend": item["trend"],
            "confidence": item["confidence"],
            "recommendation": item["recommendation"]
        })

    description_map = {"Bullish": "IHSG Diprediksi NAIK", "Bearish": "IHSG Diprediksi TURUN", "Sideways": "IHSG Diprediksi STABIL"}

    output = {
        "status": "success",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metadata": {
            "index_choice": index_choice.lower(),
            "start_date": start_date,
            "end_date": end_date,
            "data_points_days": trading_days,
            "bi_rate": bi_rate_pct
        },
        "ihsg_analysis": {
            "market_trend": market_trend,
            "confidence": round(confidence, 3),
            "prediction_class": prediction_class,
            "model_architecture": "BiLSTM + Attention",
            "description": description_map.get(market_trend, "IHSG Diprediksi STABIL")
        },
        "decision_engine": {
            "best_method": best_method,
            "selection_reason": selection_reason
        },
        "best_method_metrics": {
            "expected_return": round(float(result["portfolio_annual_return"]), 4),
            "annual_risk": round(float(result["portfolio_annual_risk"]), 4),
            "sharpe_ratio": sharpe_ratio_val,
            "beta": beta_avg,
            "alpha": alpha_avg,
            "treynor_ratio": treynor_ratio
        },
        "investment_simulation": {
            "initial_amount": int(investment_amount),
            # ⚡ RUMUS FIX: Kalikan murni modal dengan desimal riil dari dataframe/array bursa
            "potential_gain": int(investment_amount * float(result["portfolio_annual_return"])),
            "potential_loss": int(investment_amount * float(result["portfolio_annual_risk"]))
        },
        "portfolio_allocation": portfolio_allocation,
        "method_comparison": method_comparison,
        "ai_interpretation": ai_interpretation
    }

    # Sterilkan data dari nilai NaN / Infinity sebelum masuk ke database
    cleaned_output = clean_nan(output)

    # ==============================================================================
    # ⚡ AUTOSAVE BACKEND-DRIVEN KE SUPABASE (BERHASIL DIREKONSTRUKSI) ⚡
    # ==============================================================================
    if supabase is not None and user_id is not None:
        try:
            history_payload = {
                "user_id": user_id,
                "target_index": index_choice.upper(),
                "method": best_method,
                "capital": int(investment_amount),
                "expected_return": float(cleaned_output["best_method_metrics"]["expected_return"]),
                "risk": float(cleaned_output["best_method_metrics"]["annual_risk"]),
                "sharpe_ratio": float(cleaned_output["best_method_metrics"]["sharpe_ratio"]),
                "market_sentiment": market_trend,
                "bi_rate": float(cleaned_output["metadata"]["bi_rate"]),
                "start_date": start_date,
                "end_date": end_date,
                "ai_interpretation": cleaned_output["ai_interpretation"],
                "portfolio_allocation": cleaned_output  # Menyimpan bundle response JSONB utuh
            }
            supabase.table("investment_histories").insert(history_payload).execute()
            print("🎉 Sukses: Hasil kalkulasi portofolio berhasil disimpan otomatis ke database!")
        except Exception as db_err:
            print(f"⚠️ Peringatan: Gagal melakukan autosave ke Supabase: {str(db_err)}")

    return cleaned_output