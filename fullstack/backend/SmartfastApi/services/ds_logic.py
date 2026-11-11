import math
from datetime import datetime
from dateutil.relativedelta import relativedelta
from utils.data_loader import load_all_data
from constants.index_map import INDEX_MAP
from utils.dynamic_filtering import dynamic_filtering
from utils.feature_engineering import (
    feature_engineering
)

from services.stock_analysis_service import (
    predict_stock_trend
)

from services.ihsg_service import (
    predict_ihsg
)

from utils.portfolio_models import (
    compare_all_models,
    run_selected_model
)

# ==========================
# OPTIONAL GENAI
# ==========================

try:
    from services.genai_service import (
        generate_analysis_summary
    )

    GENAI_AVAILABLE = True

except Exception:

    GENAI_AVAILABLE = False

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

def clean_nan(obj):
    """
    Recursively replace NaN
    to None for JSON response
    """

    if isinstance(
        obj,
        dict
    ):

        return {
            k:
            clean_nan(v)
            for k, v
            in obj.items()
        }

    elif isinstance(
        obj,
        list
    ):

        return [
            clean_nan(i)
            for i in obj
        ]

    elif isinstance(
        obj,
        float
    ):

        if math.isnan(obj):

            return None

        if math.isinf(obj):

            return None

        return obj

    return obj

def analyze_portfolio_logic(
    index_choice: str,
    start_date: str,
    end_date: str,
    investment_amount: float,
    model_choice: str = "ALL",
    gemini_api_key: str = None
):
    """
    Main logic analyze portfolio
    """

    # ==========================
    # VALIDASI PERIODE
    # ==========================

    start_dt = datetime.strptime(
        start_date,
        "%Y-%m-%d"
    )

    end_dt = datetime.strptime(
        end_date,
        "%Y-%m-%d"
    )

    # tanggal akhir > awal
    if end_dt <= start_dt:
        raise ValueError(
            "Tanggal akhir harus "
            "setelah tanggal mulai"
        )

    delta = relativedelta(
        end_dt,
        start_dt
    )

    total_months = (
        delta.years * 12
        + delta.months
    )

    # minimal 6 bulan (toleransi perbedaan jumlah hari akhir bulan 30 vs 31 hari)
    if total_months < 6 and (end_dt - start_dt).days < 175:
        raise ValueError(
            "Periode minimal "
            "6 bulan"
        )

    # maksimal 5 tahun
    if delta.years > 5 or (
        delta.years == 5
        and (
            delta.months > 0
            or delta.days > 5
        )
    ):
        raise ValueError(
            "Periode maksimal "
            "5 tahun"
        )

    # ==========================
    # LOAD DATA
    # ==========================

    data = load_all_data()

    price_matrix = data["price_matrix"]
    market_price = data["market_price"]
    bi_rate = data["bi_rate"]

    # ==========================
    # DYNAMIC FILTERING
    # ==========================

    filtered_result = dynamic_filtering(
        index_choice=index_choice,
        start_date=start_date,
        end_date=end_date,
        price_matrix=price_matrix,
        market_price=market_price,
        bi_rate_daily=bi_rate,
        index_map=INDEX_MAP
    )

    # ==========================
    # FEATURE ENGINEERING
    # ==========================

    feature_result = feature_engineering(
        filtered_price=filtered_result[
            "filtered_price"
        ],
        filtered_market=filtered_result[
            "filtered_market"
        ],
        filtered_bi_rate=filtered_result[
            "filtered_bi_rate"
        ]
    )

    # ==================================================
    # MODEL ALL
    # ==================================================

    if model_choice == "ALL":

        compare_result = compare_all_models(
            feature_result=feature_result,
            investment_amount=investment_amount
        )

        comparison = (
            compare_result[
                "comparison_df"
            ]
            .to_dict(
                orient="records"
            )
        )

        # ==========================
        # PREDICT IHSG
        # ==========================

        ihsg_result = predict_ihsg(gemini_api_key=gemini_api_key)

        market_trend = (
            ihsg_result[
                "market_trend"
            ]
        )

        portfolios = {}

        for item in comparison:

            portfolios[
                item[
                    "Model"
                ]
            ] = {

                "annual_return":
                    item[
                        "Annual Return"
                    ],

                "annual_risk":
                    item[
                        "Annual Risk"
                    ],

                "sharpe_ratio":
                    item[
                        "Sharpe Ratio"
                    ]
            }

        # ==========================
        # PICK BEST METHOD
        # ==========================

        if market_trend == "Bullish":

            best_method = max(
                portfolios.keys(),
                key=lambda x:
                portfolios[x][
                    "sharpe_ratio"
                ]
            )

        elif market_trend == "Bearish":

            best_method = min(
                portfolios.keys(),
                key=lambda x:
                portfolios[x][
                    "annual_risk"
                ]
            )

        else:

            max_sharpe = max(
                p["sharpe_ratio"]
                for p in (
                    portfolios
                    .values()
                )
            )

            min_risk = min(
                p["annual_risk"]
                for p in (
                    portfolios
                    .values()
                )
            )

            max_risk = max(
                p["annual_risk"]
                for p in (
                    portfolios
                    .values()
                )
            )

            scores = {}

            for name, p in (
                portfolios.items()
            ):

                sharpe_score = (
                    p[
                        "sharpe_ratio"
                    ]
                    /
                    max_sharpe
                    if max_sharpe > 0
                    else 0
                )

                risk_score = (
                    1
                    -
                    (
                        (
                            p[
                                "annual_risk"
                            ]
                            -
                            min_risk
                        )
                        /
                        (
                            max_risk
                            -
                            min_risk
                        )
                    )
                    if max_risk >
                    min_risk
                    else 1
                )

                scores[
                    name
                ] = (
                    0.6
                    * sharpe_score
                    +
                    0.4
                    * risk_score
                )

            best_method = max(
                scores.keys(),
                key=lambda x:
                scores[x]
            )

        # ==========================
        # RUN WINNER MODEL
        # ==========================

        result = run_selected_model(
            model_choice=best_method,
            feature_result=feature_result,
            investment_amount=investment_amount
        )

    else:

        result = run_selected_model(
            model_choice=model_choice,
            feature_result=feature_result,
            investment_amount=investment_amount
        )

        best_method = result[
            "method"
        ]

        ihsg_result = None
        comparison = None

    # ==========================
    # FILTER NON-ZERO WEIGHTS (ALLOW SHORT SELLING)
    # ==========================

    weights_df = result[
        "weights"
    ]

    weights_df = (
        weights_df[
            weights_df[
                "Weight"
            ].abs() > 0.0001
        ]
    )

    # ==========================
    # BUILD PORTFOLIO
    # ==========================

    portfolio = []

    for _, row in (
        weights_df.iterrows()
    ):
        ticker = row["Ticker"]

        stock_prediction = (
            predict_stock_trend(ticker)
        )

        # Get current price
        try:
            current_price = float(filtered_result["filtered_price"][ticker].dropna().iloc[-1])
        except Exception:
            current_price = 0.0

        # Calculate lot allocation (1 lot = 100 shares)
        if current_price > 0:
            shares = row["Allocation"] / current_price
            lot = round(shares / 100, 2)
            integer_lot = int(shares / 100)
        else:
            shares = 0.0
            lot = 0.0
            integer_lot = 0

        # Fetch metadata
        meta = TICKER_DETAILS.get(ticker, {"fullname": f"PT {ticker.split('.')[0]} Tbk", "sector": "Lainnya"})

        item = {

            "ticker":
                ticker,

            "fullname":
                meta["fullname"],

            "sector":
                meta["sector"],

            "current_price":
                round(current_price, 2) if current_price > 0 else None,

            "weight":
                round(
                    float(
                        row[
                            "Weight"
                        ]
                    ),
                    4
                ),

            "allocation":
                round(
                    float(
                        row[
                            "Allocation"
                        ]
                    ),
                    2
                ),

            "shares":
                round(shares, 2) if current_price > 0 else None,

            "lot":
                lot if current_price > 0 else None,

            "integer_lot":
                integer_lot if current_price > 0 else None,

            "trend":
                stock_prediction[
                    "trend"
                ],

            "confidence":
                stock_prediction[
                    "confidence"
                ],

            "recommendation":
                stock_prediction[
                    "recommendation"
                ]
        }

        # SIM/CAPM alpha beta
        if result[
            "method"
        ] in [
            "SIM",
            "CAPM"
        ]:

            if (
                "alpha"
                in row.index
            ):

                item[
                    "alpha"
                ] = round(
                    float(
                        row[
                            "alpha"
                        ]
                    ),
                    4
                )

            if (
                "beta"
                in row.index
            ):

                item[
                    "beta"
                ] = round(
                    float(
                        row[
                            "beta"
                        ]
                    ),
                    4
                )

        portfolio.append(
            item
        )

    # ==========================
    # DASHBOARD SUMMARY
    # ==========================

    selected_method_result = {

        "annual_return":
            round(
                float(
                    result[
                        "portfolio_annual_return"
                    ]
                ) * 100,
                2
            ),

        "annual_risk":
            round(
                float(
                    result[
                        "portfolio_annual_risk"
                    ]
                ) * 100,
                2
            ),

        "sharpe_ratio":
            round(
                float(
                    result[
                        "sharpe_ratio"
                    ]
                ),
                2
            ),

        "alpha":
            None,

        "beta":
            None
    }


    # ==========================
    # CLEAN NAN VALUE
    # ==========================

    for key in [
        "annual_return",
        "annual_risk",
        "sharpe_ratio"
    ]:

        value = selected_method_result[
            key
        ]

        if (
            isinstance(
                value,
                float
            )
            and
            math.isnan(
                value
            )
        ):

            selected_method_result[
                key
            ] = None

    # ==========================
    # ALPHA BETA SUMMARY
    # ==========================

    alpha_values = []
    beta_values = []

    if result["method"] in [
        "SIM",
        "CAPM"
    ]:

        for item in portfolio:

            if (
                "alpha"
                in item
            ):

                alpha_values.append(
                    item[
                        "alpha"
                    ]
                )

            if (
                "beta"
                in item
            ):

                beta_values.append(
                    item[
                        "beta"
                    ]
                )

    alpha_avg = (
        round(
            sum(alpha_values)
            /
            len(alpha_values),
            4
        )
        if alpha_values
        else None
    )

    beta_avg = (
        round(
            sum(beta_values)
            /
            len(beta_values),
            4
        )
        if beta_values
        else None
    )


    # ==========================
    # TREYNOR RATIO
    # ==========================

    risk_free_rate = float(feature_result["annual_risk_free_rate"] * 100)

    annual_return = round(
        float(
            result[
                "portfolio_annual_return"
            ]
        ) * 100,
        2
    )

    annual_risk = round(
        float(
            result[
                "portfolio_annual_risk"
            ]
        ) * 100,
        2
    )

    sharpe_ratio = round(
        float(
            result[
                "sharpe_ratio"
            ]
        ),
        2
    )

    if (
        beta_avg is not None
        and beta_avg != 0
    ):

        treynor_ratio = round(
            (
                annual_return
                -
                risk_free_rate
            )
            /
            beta_avg,
            4
        )

    else:

        treynor_ratio = None


    # ==========================
    # GENAI PORTFOLIO SUMMARY
    # ==========================
    ihsg_result = predict_ihsg(end_date=end_date, gemini_api_key=gemini_api_key)
    trend = ihsg_result["market_trend"]
    confidence = ihsg_result["confidence"]

    # Calculate variables for analysis summary
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    period_years = (end_dt - start_dt).days / 365.25
    historical_period = f"{start_date} s/d {end_date} ({period_years:.1f} tahun)"

    alloc_items = [
        f"{item['ticker'].replace('.JK', '')} ({item['weight']*100:.1f}%)" 
        for item in portfolio
    ]
    portfolio_allocation = ", ".join(alloc_items)

    detail_items = []
    for item in portfolio:
        detail_items.append(
            f"- {item['ticker'].replace('.JK', '')} ({item['fullname']}): Bobot {item['weight']*100:.1f}%, Sektor {item['sector']}, Tren {item['trend']}, Rekomendasi {item['recommendation']}"
        )
    stock_details = "\n".join(detail_items)

    market_condition = f"Pasar diprediksi {trend.upper()} ({'semangat naik' if trend == 'Bullish' else 'cenderung turun' if trend == 'Bearish' else 'stabil sideways'})"

    if GENAI_AVAILABLE:
        portfolio_summary = generate_analysis_summary(
            market_condition=market_condition,
            confidence=confidence,
            historical_period=historical_period,
            portfolio_allocation=portfolio_allocation,
            stock_details=stock_details,
            model_choice=model_choice,
            investment_amount=investment_amount,
            index_choice=index_choice,
            annual_return=annual_return,
            annual_risk=annual_risk,
            sharpe_ratio=sharpe_ratio,
            bi_rate=round(risk_free_rate, 3),
            alpha=alpha_avg,
            beta=beta_avg,
            gemini_api_key=gemini_api_key
        )
    else:
        portfolio_summary = f"Portofolio dioptimalkan menggunakan metode {result['method']} dengan Expected Return {annual_return}% dan Risiko {annual_risk}%."

    # ==========================
    # RESPONSE
    # ==========================

    response = {
        "portfolio": portfolio,
        "portfolio_summary": portfolio_summary
    }

    return clean_nan(response)
