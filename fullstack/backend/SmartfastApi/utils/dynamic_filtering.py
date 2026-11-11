import pandas as pd
from dateutil.relativedelta import relativedelta


# ==========================================
# VALIDASI PERIODE
# ==========================================

def validate_period(start_date, end_date, min_months=6):

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # tanggal awal > akhir
    if start_date >= end_date:
        raise ValueError(
            "Tanggal awal harus lebih kecil dari tanggal akhir."
        )

    # minimal periode (toleransi 5 hari untuk perbedaan jumlah hari akhir bulan 30 vs 31 hari)
    minimum_end_date = start_date + relativedelta(months=min_months) - pd.Timedelta(days=5)

    if end_date < minimum_end_date:
        raise ValueError(
            f"Periode analisis minimal {min_months} bulan."
        )

    return start_date, end_date


# ==========================================
# DYNAMIC FILTERING
# ==========================================

def dynamic_filtering(
    index_choice,
    start_date,
    end_date,
    price_matrix,
    market_price,
    bi_rate_daily,
    index_map,
    min_months=6
):

    """
    Dynamic filtering berdasarkan:
    - pilihan index
    - periode
    - saham dengan data lengkap

    Output:
    - filtered_price
    - filtered_market
    - filtered_bi_rate
    - valid_tickers
    - removed_tickers
    - filtering_summary
    """

    # ======================================
    # VALIDASI INDEX
    # ======================================

    if index_choice not in index_map:

        raise ValueError(
            f"Index {index_choice} tidak tersedia."
        )

    # ======================================
    # VALIDASI PERIODE
    # ======================================

    start_date, end_date = validate_period(
        start_date,
        end_date,
        min_months=min_months
    )

    # ======================================
    # AMBIL TICKER INDEX
    # ======================================

    selected_tickers = index_map[index_choice]

    # ======================================
    # CEK TICKER TERSEDIA
    # ======================================

    available_tickers = [
        ticker
        for ticker in selected_tickers
        if ticker in price_matrix.columns
    ]

    unavailable_tickers = [
        ticker
        for ticker in selected_tickers
        if ticker not in price_matrix.columns
    ]

    if len(available_tickers) == 0:

        raise ValueError(
            "Tidak ada ticker tersedia."
        )

    # ======================================
    # FILTER PRICE MATRIX
    # ======================================

    filtered_price = price_matrix.loc[
        start_date:end_date,
        available_tickers
    ]

    if filtered_price.empty:

        raise ValueError(
            "Data harga kosong pada periode tersebut."
        )

    # ======================================
    # FILTER SAHAM LENGKAP
    # ======================================

    data_counts = filtered_price.count()

    max_count = data_counts.max()

    valid_tickers = data_counts[
        data_counts == max_count
    ].index.tolist()

    removed_tickers = data_counts[
        data_counts < max_count
    ].index.tolist()

    filtered_price = filtered_price[valid_tickers]

    # ======================================
    # FILTER MARKET
    # ======================================

    filtered_market = market_price.loc[
        start_date:end_date
    ]

    filtered_market = filtered_market.reindex(
        filtered_price.index
    )

    # ======================================
    # FILTER BI RATE
    # ======================================

    bi_rate_sorted = bi_rate_daily.sort_index()
    bi_rate_sorted = bi_rate_sorted[~bi_rate_sorted.index.duplicated(keep="last")]

    filtered_bi_rate = bi_rate_sorted.reindex(
        filtered_price.index,
        method="ffill"
    ).bfill()

    # ======================================
    # VALIDASI MISSING VALUE
    # ======================================

    if filtered_price.isnull().sum().sum() > 0:

        raise ValueError(
            "Masih ada missing value pada filtered_price."
        )

    if filtered_market.isnull().sum().sum() > 0:

        raise ValueError(
            "Masih ada missing value pada filtered_market."
        )

    if filtered_bi_rate.isnull().sum().sum() > 0:

        raise ValueError(
            "Masih ada missing value pada filtered_bi_rate."
        )

    # ======================================
    # RINGKASAN FILTERING
    # ======================================

    filtering_summary = {

        "index_choice": index_choice,

        "start_date": start_date,

        "end_date": end_date,

        "initial_ticker_count": len(selected_tickers),

        "available_ticker_count": len(available_tickers),

        "valid_ticker_count": len(valid_tickers),

        "removed_ticker_count": len(removed_tickers),

        "unavailable_tickers": unavailable_tickers,

        "removed_tickers_due_to_incomplete_data": removed_tickers,

        "trading_days_used": filtered_price.shape[0]
    }

    # ======================================
    # RETURN OUTPUT
    # ======================================

    return {

        "filtered_price": filtered_price,

        "filtered_market": filtered_market,

        "filtered_bi_rate": filtered_bi_rate,

        "valid_tickers": valid_tickers,

        "removed_tickers": removed_tickers,

        "filtering_summary": filtering_summary
    }
