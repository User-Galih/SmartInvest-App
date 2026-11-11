import os
import re

# Model prioritas sesuai generasi terbaru Google AI Studio
PREFERRED_MODELS = [
    os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
    "gemini-4-argon",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]


def _call_gemini(prompt: str, custom_api_key: str = None, key_env_var: str = "GEMINI_API_KEY") -> str | None:
    """
    Memanggil Gemini API menggunakan SDK google-genai terbaru (dengan fallback ke google.generativeai)
    dan mencoba daftar model prioritas secara berurutan.
    Mengembalikan None jika tidak ada API Key atau seluruh model gagal.
    """
    key = (
        custom_api_key
        or os.getenv(key_env_var)
        or os.getenv("GEMINI_API_KEY_ANALYSIS")
        or os.getenv("GEMINI_API_KEY_IHSG")
        or os.getenv("GEMINI_API_KEY")
    )
    if not key or not key.strip():
        return None

    key = key.strip()

    # 1. Gunakan SDK resmi terbaru: google-genai
    try:
        from google import genai as new_genai

        client = new_genai.Client(api_key=key)
        seen = set()
        for model_name in PREFERRED_MODELS:
            if not model_name or model_name in seen:
                continue
            seen.add(model_name)
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if response and getattr(response, "text", None):
                    return response.text.strip()
            except Exception as err:
                print(f"[genai_service] google-genai gagal pada model {model_name}: {err}")
                continue
    except ImportError:
        pass
    except Exception as e:
        print(f"[genai_service] Inisialisasi google-genai gagal: {e}")

    # 2. Fallback ke SDK legacy jika google-genai belum terinstal di environment
    try:
        import google.generativeai as legacy_genai

        legacy_genai.configure(api_key=key)
        seen = set()
        for model_name in PREFERRED_MODELS:
            if not model_name or model_name in seen:
                continue
            seen.add(model_name)
            try:
                model = legacy_genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if response and getattr(response, "text", None):
                    return response.text.strip()
            except Exception as err:
                print(f"[genai_service] google.generativeai gagal pada model {model_name}: {err}")
                continue
    except Exception as e:
        print(f"[genai_service] Fallback legacy SDK gagal: {e}")

    return None


def _parse_top_tickers_from_alloc(alloc_str: str):
    """Mengekstrak daftar (ticker, weight_pct) dari string alokasi untuk narasi dinamis."""
    if not alloc_str:
        return []
    matches = re.findall(r"([A-Z]{4})\s*\((-?\d+(?:\.\d+)?)%\)", alloc_str)
    parsed = [(t, float(w)) for t, w in matches]
    parsed.sort(key=lambda x: abs(x[1]), reverse=True)
    return parsed


# ==============================================================================
# 1. MARKET SUMMARY (DIPANGGIL OLEH ENDPOINT PREDICT-IHSG)
# ==============================================================================
def generate_market_summary(
    market_trend,
    confidence,
    market_condition,
    recommended_method,
    reason,
    gemini_api_key: str = None,
):
    prompt = f"""Kamu adalah analis kuantitatif dan penasihat investasi pasar modal Indonesia di SmartInvest AI.
Berdasarkan hasil model prediksi BiLSTM + Attention terhadap pergerakan Indeks Harga Saham Gabungan (IHSG):
- Arah Tren IHSG: {market_trend} ({market_condition})
- Tingkat Keyakinan Model: {confidence:.2%}
- Metode Optimasi Portofolio yang Direkomendasikan: {recommended_method}
- Rasionalisasi Kuantitatif: {reason}

Tugasmu:
1. Awali dengan judul: 📈 SmartInvest AI Market Insight
2. Berikan analisis ringkas, tajam, dan spesifik mengenai kondisi pasar {market_trend} saat ini serta apa arti tingkat keyakinan {confidence:.2%} bagi pengambilan keputusan investor.
3. Jelaskan secara logis mengapa metode {recommended_method} menjadi pendekatan paling tepat untuk merespons kondisi tersebut.
4. Berikan 2-3 langkah taktis yang relevan dengan kondisi {market_trend}.
5. Gunakan Bahasa Indonesia yang profesional, mengalir alami, edukatif, dan mudah dipahami (maksimal 180 kata). Hindari kata-kata slang/alay seperti "gokil", "gercep", atau "anti-boncos".
"""
    ai_text = _call_gemini(prompt, custom_api_key=gemini_api_key, key_env_var="GEMINI_API_KEY_IHSG")
    if ai_text:
        return ai_text

    return (
        f"📈 SmartInvest AI Market Insight\n\n"
        f"Model BiLSTM + Attention mendeteksi pergerakan IHSG berada pada fase **{market_trend}** ({market_condition}) "
        f"dengan tingkat keyakinan statistik sebesar **{confidence:.2%}**. Dalam kondisi ini, metode **{recommended_method}** "
        f"direkomendasikan karena {reason.lower()} Disarankan untuk menjaga disiplin alokasi bobot aset dan menyesuaikan eksposur risiko secara berkala."
    )


# ==============================================================================
# 2. RECOMMENDATION SUMMARY (DIREKTUR OLEH REKOMENDASI PAGE)
# ==============================================================================
def generate_recommendation_summary(
    best_method,
    bi_rate,
    market_trend_str,
    confidence,
    horizon_yr,
    ret_pct,
    risk_pct,
    sharpe,
    beta,
    gain_ex,
    loss_ex,
    alloc_str,
    comparison_str,
    investment_amount=10000000,
    index_choice="LQ45",
    gemini_api_key: str = None,
):
    has_short = "-" in alloc_str
    index_upper = index_choice.upper() if index_choice else "LQ45"
    if index_upper == "LQ45":
        index_desc = "LQ45 (45 saham dengan likuiditas tertinggi dan kapitalisasi pasar besar di BEI)"
    elif index_upper in ["IDX30", "IDX 30"]:
        index_desc = "IDX30 (30 saham unggulan berfundamental inti di Bursa Efek Indonesia)"
    else:
        index_desc = index_upper

    beta_str = f"{beta:.2f}" if beta is not None else "N/A"
    spread_vs_bi = ret_pct - float(bi_rate)

    prompt = f"""Kamu adalah Senior Quantitative Portfolio Advisor di SmartInvest.
Tugasmu adalah menulis analisis rekomendasi portofolio saham yang **benar-benar spesifik, analitis, dan mendalam** berdasarkan angka dan komposisi saham riil di bawah ini.

ATURAN GAYA BAHASA (SANGAT PENTING):
- JANGAN gunakan kata-kata slang/template klise seperti "gokil", "gercep", "anti-boncos", "cuan melimpah", "Wah, senang banget deh", atau "Hasilnya mantap banget!".
- Tulis analisis layaknya penasihat keuangan profesional yang ramah, cerdas, variatif, dan langsung membahas saham-saham spesifik serta angka metrik yang muncul di data.
- Setiap paragraf harus mengupas data aktual di bawah ini (sebutkan langsung nama-nama ticker saham dengan bobot terbesar di {alloc_str}, bandingkan langsung angka return/risiko/Sharpe antar metode di {comparison_str}, dan hitung selisih return terhadap BI Rate {bi_rate}%).

DATA KUANTITATIF AKTUAL:
- Modal Investasi: Rp {investment_amount:,.0f}
- Indeks Universe: {index_desc}
- Horizon Data Historis: {horizon_yr} tahun
- Suku Bunga Acuan (BI Rate): {bi_rate}%
- Proyeksi Tren Makro IHSG: {market_trend_str} (Confidence: {confidence:.1%})
- Metode Optimasi Terpilih: {best_method}
- Expected Return Portofolio: {ret_pct:.2f}% per tahun (selisih {spread_vs_bi:+.2f}% di atas BI Rate)
- Risiko Tahunan (Volatilitas): {risk_pct:.2f}% per tahun
- Sharpe Ratio: {sharpe:.3f}
- Beta Portofolio: {beta_str}
- Simulasi Nominal (1 Tahun): Potensi pertumbuhan +Rp{gain_ex:,} | Potensi fluktuasi risiko -Rp{loss_ex:,}
- Komposisi Bobot Saham Terpilih:
{alloc_str}
- Perbandingan Ketiga Metode (MVEP vs SIM vs CAPM):
{comparison_str}

STRUKTUR OUTPUT WAJIB (Ikuti header bagian di bawah ini secara persis agar komponen visual aplikasi dapat mem-parsing tiap bagian dengan benar):

👋 Hallo Sobat SmartInvest!

[Tulis 4 paragraf analisis mendalam yang Masing-Masing terdiri dari 4-6 kalimat analitis dan mengalir alami:
- Paragraf 1: Evaluasi konteks makro & pemilihan metode. Bahas mengapa pada tren IHSG yang cenderung {market_trend_str} dengan BI Rate {bi_rate}%, algoritma {best_method} unggul dibandingkan dua metode lainnya pada universe {index_upper} selama rentang historis {horizon_yr} tahun untuk modal Rp {investment_amount:,.0f}.
- Paragraf 2: Bedah komposisi saham aktual. Sebutkan secara spesifik emiten-emiten dengan alokasi bobot terbesar dari daftar komposisi di atas, jelaskan peran saham-saham utama tersebut dalam membentuk keseimbangan return dan volatilitas portofolio.
- Paragraf 3: Bedah perbandingan kuantitatif antar metode ({comparison_str}). Jelaskan secara objektif perbandingan Expected Return, Risiko, dan Sharpe Ratio antara MVEP, SIM, dan CAPM pada hasil perhitungan ini, serta mengapa {best_method} menjadi pemenang secara matematis.
- Paragraf 4: Evaluasi profil risiko-imbal hasil ({ret_pct:.2f}% return vs {risk_pct:.2f}% risiko, Sharpe {sharpe:.3f}, Beta {beta_str}). {"Karena terdapat posisi bobot negatif (short selling) pada portofolio ini, jelaskan secara objektif mekanisme short selling pada saham terkait serta konsekuensi risiko asimetrisnya." if has_short else "Jelaskan bagaimana seluruh posisi long (beli) pada saham-saham tersebut memberikan eksposur pertumbuhan yang terukur terhadap pasar."}]

━━━━━━━━━━━━━━━━━━
📊 DATA PENTING
━━━━━━━━━━━━━━━━━━
💰 Expected Return: {ret_pct:.1f}% per tahun

📉 Risiko: {risk_pct:.1f}% per tahun

🎯 Sharpe Ratio: {sharpe:.3f}

💸 Simulasi:
potensi untung +Rp{gain_ex:,}
potensi turun -Rp{loss_ex:,}

━━━━━━━━━━━━━━━━━━
🎯 ISTILAH INVESTASI
━━━━━━━━━━━━━━━━━━
* **Return**: [Jelaskan arti Expected Return {ret_pct:.1f}% per tahun secara spesifik dibandingkan BI Rate {bi_rate}% dan simulasi +Rp{gain_ex:,}]
* **Risk (Risiko)**: [Jelaskan arti volatilitas tahunan {risk_pct:.1f}% dan potensi deviasi nilai -Rp{loss_ex:,} pada modal Rp {investment_amount:,.0f}]
* **Sharpe Ratio**: [Jelaskan arti nilai Sharpe Ratio {sharpe:.3f} pada portofolio {best_method} ini dengan acuan risk-free rate {bi_rate}%]
* **Alpha**: [Jelaskan arti Alpha portofolio dalam mengukur nilai tambah pemilihan saham {index_upper} terhadap rata-rata pasar]
* **Beta**: [Jelaskan arti Beta = {beta_str} terhadap sensitivitas IHSG {"serta pengaruh posisi short selling pada sensitivitas tersebut" if has_short else "dan karakter defensif/agresif portofolio ini"}]
* **Treynor Ratio**: [Jelaskan peran Treynor Ratio dalam mengukur excess return per unit risiko sistematis (Beta)]

━━━━━━━━━━━━━━━━━━
🏦 ALOKASI PORTOFOLIO
━━━━━━━━━━━━━━━━━━
Komposisi alokasi saham pilihan hasil optimasi {best_method}:
{alloc_str}
Dengan modal awal sebesar Rp{investment_amount:,.0f}, proyeksi potensi imbal hasil tahunan berada di kisaran +Rp{gain_ex:,} dengan batas toleransi risiko tahunan sekitar -Rp{loss_ex:,}.

━━━━━━━━━━━━━━━━━━
📌 PERBANDINGAN METODE LAIN
━━━━━━━━━━━━━━━━━━
Perbandingan skor metode optimasi portofolio Anda:
{comparison_str}

━━━━━━━━━━━━━━━━━━
💡 Beberapa tips yang harus Kamu lakukan:
━━━━━━━━━━━━━━━━━━
👉 [Tulis 1 strategi konkret terkait pengelolaan bobot saham dominan yang ada di portofolio ini]
👉 [Tulis 1 strategi konkret terkait jadwal evaluasi/rebalancing menghadapi tren IHSG {market_trend_str} dan BI Rate {bi_rate}%]
👉 [Tulis 1 strategi manajemen risiko/batas toleransi kerugian untuk modal Rp {investment_amount:,.0f} {"khususnya pengawasan ketat posisi short selling" if has_short else "secara bertahap"}]

⚠️ Ini bukan jaminan keuntungan, hanya proyeksi berdasarkan data historis pasar.
"""

    ai_text = _call_gemini(prompt, custom_api_key=gemini_api_key, key_env_var="GEMINI_API_KEY_ANALYSIS")
    if ai_text:
        return ai_text

    # Dynamic data-driven fallback (tanpa kata-kata alay/template kaku) jika API Key belum disetel
    top_tickers = _parse_top_tickers_from_alloc(alloc_str)
    top_names = ", ".join([f"{t} ({w:.1f}%)" for t, w in top_tickers[:3]]) if top_tickers else "saham-saham berfundamental utama"

    short_note = (
        f"Terdapat posisi bobot negatif (short selling) dalam hasil optimasi ini untuk memanfaatkan koreksi harga pada emiten tertentu sekaligus menjadi penyeimbang (hedging) terhadap fluktuasi pasar."
        if has_short
        else f"Seluruh alokasi ditempatkan pada posisi beli (long position) dengan fokus pada emiten berlikuiditas tinggi di indeks {index_upper}."
    )

    return f"""👋 Hallo Sobat SmartInvest!

Berdasarkan simulasi kuantitatif pada modal investasi sebesar Rp {investment_amount:,.0f} menggunakan data historis selama {horizon_yr} tahun terakhir dan acuan suku bunga BI Rate {bi_rate}%, algoritma **{best_method}** terpilih sebagai metode paling optimal untuk merespons kondisi IHSG yang sedang bergerak **{market_trend_str}**. Pemilihan kandidat saham difokuskan pada indeks **{index_desc}** guna menjaga standar likuiditas dan kualitas fundamental portofolio.

Dalam struktur alokasi yang terbentuk, bobot portofolio dipimpin oleh **{top_names}** yang memiliki rasio imbal hasil terhadap risiko paling efisien selama periode pengamatan. Dengan proyeksi Expected Return tahunan sebesar **{ret_pct:.1f}%** (memberikan premi imbal hasil sebesar **{spread_vs_bi:+.1f}%** di atas BI Rate {bi_rate}%) dan volatilitas tahunan sebesar **{risk_pct:.1f}%**, portofolio ini mencatatkan Sharpe Ratio sebesar **{sharpe:.3f}**.

Pemilihan metode **{best_method}** didasarkan pada evaluasi objektif terhadap perbandingan metrik ketiga model optimasi (MVEP, SIM, dan CAPM). Pada kondisi pasar **{market_trend_str}**, pendekatan {best_method} memberikan keseimbangan paling rasional antara pencapaian target pertumbuhan modal (+Rp{gain_ex:,}) dan pengendalian batas risiko (-Rp{loss_ex:,}).

{short_note} Tingkat sensitivitas portofolio terhadap pergerakan pasar tercermin pada nilai Beta sebesar **{beta_str}**, yang menjadi indikator penting bagi Anda dalam memantau respons portofolio terhadap dinamika makroekonomi domestik.

━━━━━━━━━━━━━━━━━━
📊 DATA PENTING
━━━━━━━━━━━━━━━━━━
💰 Expected Return: {ret_pct:.1f}% per tahun

📉 Risiko: {risk_pct:.1f}% per tahun

🎯 Sharpe Ratio: {sharpe:.3f}

💸 Simulasi:
potensi untung +Rp{gain_ex:,}
potensi turun -Rp{loss_ex:,}

━━━━━━━━━━━━━━━━━━
🎯 ISTILAH INVESTASI
━━━━━━━━━━━━━━━━━━
* **Return**: Proyeksi tingkat pengembalian tahunan sebesar {ret_pct:.1f}% (setara +Rp{gain_ex:,} dari modal Rp {investment_amount:,.0f}) berdasarkan rata-rata kinerja historis saham terpilih.
* **Risk (Risiko)**: Standar deviasi atau volatilitas tahunan sebesar {risk_pct:.1f}% (setara rentang fluktuasi ±Rp{loss_ex:,}) yang menggambarkan tingkat simpangan harga historis.
* **Sharpe Ratio**: Rasio efisiensi risiko sebesar {sharpe:.3f} setelah memperhitungkan beban suku bunga bebas risiko (BI Rate {bi_rate}%). Semakin tinggi nilai ini, semakin optimal kompensasi imbal hasil per unit risiko.
* **Alpha**: Ukuran kelebihan imbal hasil (excess return) portofolio dibandingkan imbal hasil ekspektasi pasar pada tingkat risiko sistematis yang sama.
* **Beta**: Tingkat kepekaan portofolio terhadap pergerakan IHSG (Beta = {beta_str}). Nilai di bawah 1 menunjukkan fluktuasi yang lebih teredam dibanding indeks pasar.
* **Treynor Ratio**: Pengukur efisiensi kelebihan return portofolio di atas BI Rate dibagi dengan risiko sistematis (Beta).

━━━━━━━━━━━━━━━━━━
🏦 ALOKASI PORTOFOLIO
━━━━━━━━━━━━━━━━━━
Komposisi alokasi saham pilihan Anda adalah:
{alloc_str}
Dengan modal awal sebesar Rp{investment_amount:,.0f}, potensi keuntungan tahunan diperkirakan mencapai +Rp{gain_ex:,} dengan potensi risiko fluktuasi sekitar -Rp{loss_ex:,}.

━━━━━━━━━━━━━━━━━━
📌 PERBANDINGAN METODE LAIN
━━━━━━━━━━━━━━━━━━
Perbandingan skor metode optimasi portofolio Anda:
{comparison_str}

━━━━━━━━━━━━━━━━━━
💡 Beberapa tips yang harus Kamu lakukan:
━━━━━━━━━━━━━━━━━━
👉 Pantau secara berkala kinerja emiten berbobat terbesar ({top_names}) dan pastikan fundamentalnya tetap selaras dengan tren sektoral.
👉 Lakukan evaluasi ulang (rebalancing) setiap 3 hingga 6 bulan untuk menyesuaikan bobot portofolio terhadap perubahan BI Rate ({bi_rate}%) dan arah tren IHSG.
👉 Terapkan batas toleransi risiko secara disiplin sesuai profil modal kerja Rp {investment_amount:,.0f} dan hindari keputusan emosional saat terjadi fluktuasi harian.

⚠️ Ini bukan jaminan keuntungan, hanya proyeksi berdasarkan data historis pasar."""


# ==============================================================================
# 3. PORTFOLIO INTERPRETATION / ANALYSIS (DIREKTUR OLEH ANALYSIS PAGE)
# ==============================================================================
def generate_analysis_summary(
    market_condition,
    confidence,
    historical_period,
    portfolio_allocation,
    stock_details,
    model_choice="CAPM",
    investment_amount=10000000,
    index_choice="LQ45",
    annual_return=None,
    annual_risk=None,
    sharpe_ratio=None,
    bi_rate=None,
    alpha=None,
    beta=None,
    gemini_api_key: str = None,
):
    has_short = "-" in portfolio_allocation
    index_upper = index_choice.upper() if index_choice else "LQ45"

    if index_upper == "LQ45":
        index_desc = "LQ45"
        index_full_desc = "indeks 45 emiten paling likuid dengan kapitalisasi pasar terbesar di Bursa Efek Indonesia (BEI)"
    elif index_upper in ["IDX30", "IDX 30"]:
        index_desc = "IDX30"
        index_full_desc = "indeks 30 saham blue-chip utama dengan seleksi fundamental dan likuiditas terketat di BEI"
    else:
        index_desc = index_upper
        index_full_desc = f"indeks {index_upper} di Bursa Efek Indonesia"

    if model_choice == "SIM":
        model_desc = "Single Index Model (SIM), yang mengoptimalkan rasio excess return terhadap beta pasar (cut-off rate C*) untuk menangkap momentum pertumbuhan saham terhadap IHSG"
    elif model_choice == "MVEP":
        model_desc = "Minimum Variance Efficient Portfolio (MVEP), yang meminimalkan varians total portofolio melalui matriks kovarians antar-saham untuk meredam volatilitas"
    elif model_choice == "CAPM":
        model_desc = "Capital Asset Pricing Model (CAPM), yang mengevaluasi keseimbangan imbal hasil terhadap risiko sistematis (Beta) dan suku bunga bebas risiko (BI Rate)"
    else:
        model_desc = f"algoritma optimasi kuantitatif {model_choice}"

    metrics_context = ""
    if annual_return is not None and annual_risk is not None and sharpe_ratio is not None:
        metrics_context = (
            f"\nMetrik Kuantitatif Hasil Perhitungan:\n"
            f"- Expected Return Tahunan: {annual_return:.2f}%\n"
            f"- Risiko / Volatilitas Tahunan: {annual_risk:.2f}%\n"
            f"- Sharpe Ratio: {sharpe_ratio:.3f}\n"
            f"- BI Rate Acuan: {bi_rate if bi_rate is not None else 'N/A'}%\n"
            f"- Alpha Rata-rata: {alpha if alpha is not None else 'N/A'}\n"
            f"- Beta Rata-rata: {beta if beta is not None else 'N/A'}\n"
        )

    prompt = f"""Kamu adalah Senior Quantitative Portfolio Analyst di SmartInvest.
Tugasmu adalah menyusun laporan analisis struktur portofolio yang **100% spesifik, objektif, mendalam, dan langsung membedah emiten serta angka aktual** di bawah ini.

ATURAN GAYA BAHASA (WAJIB DIPATUHI):
- JANGAN PERNAH menggunakan kata-kata slang/klise seperti "gokil", "gercep", "anti-boncos", "cuan melimpah", "Wah, seru banget nih!", atau "Hasilnya mantap banget!".
- Jangan menyalin kalimat template. Buat analisis yang benar-benar merujuk pada nama-nama saham, persentase bobot, sektor industri, dan status tren teknikal (Bullish/Bearish/Sideways) yang tertulis di DATA PORTOFOLIO.
- DILARANG menyebutkan prediksi arah IHSG atau confidence score IHSG di halaman ini (fokus murni pada bedah portofolio, metode {model_choice}, dan saham-saham penyusunnya).

DATA PORTOFOLIO AKTUAL:
- Metode Optimasi: {model_choice} ({model_desc})
- Indeks Universe: {index_desc} ({index_full_desc})
- Modal Kerja Investasi: Rp {investment_amount:,.0f}
- Rentang Data Historis: {historical_period}{metrics_context}
- Ringkasan Bobot Saham: {portfolio_allocation}
- Rincian Emiten, Sektor, dan Tren Teknikal:
{stock_details}

STRUKTUR OUTPUT WAJIB (Pertahankan header bagian dan tanda pemisah di bawah ini secara persis agar parser visual aplikasi berfungsi sempurna):

👋 Hallo Sobat SmartInvest!

[Tulis 4 paragraf pembuka yang kaya analisis, profesional, dan spesifik (masing-masing 4-6 kalimat):
- Paragraf 1: Konteks optimasi portofolio. Jelaskan bagaimana modal Rp {investment_amount:,.0f} dialokasikan menggunakan model {model_choice} pada universe {index_desc} berdasarkan data historis periode {historical_period}{f", menghasilkan proyeksi return tahunan {annual_return:.2f}% dengan tingkat risiko {annual_risk:.2f}% dan Sharpe Ratio {sharpe_ratio:.3f}" if annual_return is not None else ""}.
- Paragraf 2: Bedah komposisi saham teratas secara langsung. Sebutkan nama-nama saham dengan bobot terbesar dari daftar ({portfolio_allocation}), sektor industrinya, serta bagaimana sinyal tren teknikal masing-masing saham tersebut berkontribusi terhadap portofolio.
- Paragraf 3: Kupas cara kerja matematis metode {model_choice} pada portofolio ini. Jelaskan bagaimana {model_choice} menyeleksi dan memberi bobot pada emiten-emiten di atas (mengapa saham tertentu mendapat porsi dominan sedangkan yang lain lebih kecil).
- Paragraf 4: Evaluasi struktur eksposur dan manajemen risiko. {"Karena terdapat bobot negatif (short selling) pada portofolio ini, jelaskan secara jernih saham mana yang di-short, bagaimana mekanisme short selling bekerja sebagai lindung nilai/taktis, serta risiko asimetrisnya." if has_short else f"Jelaskan bagaimana kombinasi posisi long (beli) lintas sektor pada indeks {index_desc} ini menjaga ketahanan modal Rp {investment_amount:,.0f} terhadap rotasi sektoral."}]

━━━━━━━━━━━━━━━━━━
📊 KOMPOSISI PORTOFOLIO
━━━━━━━━━━━━━━━━━━
Portofolio Anda saat ini dialokasikan pada saham-saham pilihan sebagai berikut:
{portfolio_allocation}

Detail saham yang menyusun portofolio Anda beserta sektor dan status tren teknikalnya:
{stock_details}

━━━━━━━━━━━━━━━━━━
🛡️ ANALISIS FINANSIAL
━━━━━━━━━━━━━━━━━━
* **Analisis Alokasi & Dominasi Bobot**: [Tulis minimal 4 kalimat analitis yang secara spesifik membahas saham-saham dengan bobot terbesar di {portfolio_allocation}, mengapa model {model_choice} memberikan porsi tersebut, dan dampaknya terhadap stabilitas modal Rp {investment_amount:,.0f}.]
* **Diversifikasi Sektor & Risiko Konsentrasi**: [Tulis minimal 4 kalimat analitis yang menyebutkan sektor-sektor aktual yang muncul di daftar rincian saham di atas (misal Financial Services, Energy, Basic Materials, Consumer, dsb.) serta bagaimana korelasi antar sektor tersebut meredam risiko konsentrasi.]
* **Strategi Posisi & Karakter Portofolio**: [Tulis minimal 4 kalimat analitis mengenai karakter risiko portofolio ini dan sinyal teknikal saham-sahamnya (BUY/HOLD/AVOID). {"Uraikan juga implikasi praktis dari posisi short selling (bobot negatif) yang ada pada portofolio ini." if has_short else "Jelaskan bagaimana strategi posisi beli (long-only) pada saham-saham di atas mendukung pertumbuhan modal jangka menengah-panjang."}]

━━━━━━━━━━━━━━━━━━
💡 Strategi yang Bisa Dipertimbangkan
━━━━━━━━━━━━━━━━━━
👉 [Tulis 1 rekomendasi tindakan spesifik terkait saham berbobat terbesar atau sinyal BUY/HOLD/AVOID yang ada pada tabel di atas]
👉 [Tulis 1 rekomendasi tindakan spesifik terkait pengelolaan diversifikasi sektor dan pemantauan volatilitas pada periode mendatang]
👉 [Tulis 1 rekomendasi tindakan spesifik terkait disiplin eksekusi dan jadwal evaluasi ulang (rebalancing) untuk modal Rp {investment_amount:,.0f}]

⚠️ Analisis ini merupakan proyeksi berdasarkan data historis dan bukan jaminan keuntungan investasi.
"""

    ai_text = _call_gemini(prompt, custom_api_key=gemini_api_key, key_env_var="GEMINI_API_KEY_ANALYSIS")
    if ai_text:
        return ai_text

    # Dynamic data-driven fallback (tanpa kata-kata template klise) jika API Key belum disetel
    top_tickers = _parse_top_tickers_from_alloc(portfolio_allocation)
    top_summary = ", ".join([f"{t} ({w:.1f}%)" for t, w in top_tickers[:4]]) if top_tickers else portfolio_allocation

    sectors_found = sorted(list(set(re.findall(r"Sektor\s+([^,]+),", stock_details))))
    sectors_str = ", ".join(sectors_found) if sectors_found else "berbagai sektor utama BEI"

    metrics_sentence = (
        f"Hasil optimasi mencatatkan proyeksi Expected Return tahunan sebesar {annual_return:.2f}% dengan tingkat volatilitas tahunan {annual_risk:.2f}% dan Sharpe Ratio {sharpe_ratio:.3f}."
        if annual_return is not None and annual_risk is not None and sharpe_ratio is not None
        else "Hasil optimasi dirancang untuk menyeimbangkan potensi imbal hasil terhadap eksposur volatilitas historis."
    )

    short_bullet = (
        f"* **Strategi Posisi & Karakter Portofolio**: Struktur portofolio ini melibatkan kombinasi posisi beli (long) dan posisi bobot negatif (**short selling**) pada emiten tertentu. Strategi ini secara matematis bertujuan memanfaatkan koreksi harga pada saham berkinerja lemah sekaligus membiayai eksposur pada saham berfundamental kuat, namun menuntut pengawasan manajemen risiko dan batas stop-loss yang ketat."
        if has_short
        else f"* **Strategi Posisi & Karakter Portofolio**: Seluruh alokasi portofolio menggunakan strategi posisi beli (**long position**) pada saham-saham anggota indeks {index_desc}. Karakter portofolio ini bertumpu pada pertumbuhan nilai intrinsik dan pembagian dividen emiten berkapitalisasi besar dengan manajemen risiko yang terukur."
    )

    return f"""👋 Hallo Sobat SmartInvest!

Analisis kuantitatif ini memetakan alokasi modal investasi sebesar Rp {investment_amount:,.0f} menggunakan algoritma **{model_choice}** pada universe indeks **{index_desc}** ({index_full_desc}) selama rentang historis **{historical_period}**. {metrics_sentence}

Berdasarkan matriks bobot yang terbentuk, alokasi dana terfokus pada **{top_summary}**. Pemilihan proporsi ini mencerminkan kontribusi masing-masing emiten dalam mengoptimalkan efisiensi portofolio selama periode pengamatan, dengan mempertimbangkan pergerakan harga historis dan sinyal teknikal terkini dari tiap saham.

Secara metodologis, penerapan **{model_desc}** bekerja dengan mengevaluasi hubungan statistik antar-aset di dalam indeks {index_desc}. Emiten yang memiliki konsistensi kinerja dan kovarians risiko yang saling menyeimbangkan memperoleh porsi alokasi yang lebih besar guna menjaga ketahanan portofolio secara agregat.

Distribusi aset pada portofolio ini mencakup sektor **{sectors_str}**, sehingga fluktuasi spesifik pada satu industri dapat diredam oleh kinerja sektor lainnya. Struktur ini memberikan landasan kuantitatif yang terukur bagi pengelolaan modal investasi Anda.

━━━━━━━━━━━━━━━━━━
📊 KOMPOSISI PORTOFOLIO
━━━━━━━━━━━━━━━━━━
Portofolio Anda saat ini dialokasikan pada saham-saham pilihan sebagai berikut:
{portfolio_allocation}

Detail saham yang menyusun portofolio Anda beserta sektor dan status tren teknikalnya:
{stock_details}

━━━━━━━━━━━━━━━━━━
🛡️ ANALISIS FINANSIAL
━━━━━━━━━━━━━━━━━━
* **Analisis Alokasi & Dominasi Bobot**: Perhitungan model {model_choice} menempatkan bobot utama pada {top_summary} karena profil efisiensi historisnya yang unggul selama periode {historical_period}. Konsentrasi terukur pada emiten-emiten berlikuiditas tinggi ini berfungsi sebagai penggerak utama imbal hasil sekaligus menjaga stabilitas nilai portofolio senilai Rp {investment_amount:,.0f}.
* **Diversifikasi Sektor & Risiko Konsentrasi**: Alokasi dana tersebar lintas sektor ({sectors_str}) di dalam indeks {index_desc}. Penyebaran sektoral ini menurunkan risiko spesifik emiten (unsystematic risk) dan menjaga agar koreksi pada satu sektor industri tidak menggerus keseluruhan modal kerja secara drastis.
{short_bullet}

━━━━━━━━━━━━━━━━━━
💡 Strategi yang Bisa Dipertimbangkan
━━━━━━━━━━━━━━━━━━
👉 Perhatikan sinyal tren teknikal dan rekomendasi (BUY/HOLD/AVOID) pada emiten berbobat terbesar ({top_summary}) sebelum mengeksekusi pembelian penuh.
👉 Pertahankan disiplin proporsi lintas sektor ({sectors_str}) dan hindari menambah beban berlebih pada satu saham tunggal di luar bobot optimalnya.
👉 Lakukan evaluasi berkala setiap kuartal untuk menyelaraskan ulang (rebalancing) bobot portofolio dengan perkembangan fundamental terbaru emiten {index_desc}.

⚠️ Analisis ini merupakan proyeksi berdasarkan data historis dan bukan jaminan keuntungan investasi."""
