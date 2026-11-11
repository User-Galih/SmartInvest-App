import { useState } from "react";

export default function AnalysisPage({
  analysisCompleted,
  result,
  metaForm,
  setIsAnalysisModalOpen,
  isArchiveMode = false,
}) {
  // Memecah objek dual API hasil kiriman state global App.jsx atau arsip Supabase
  const pData = result?.portfolio_data;
  const iData = result?.ihsg_data;

  // Helper format persen pintar (mencegah perkalian ganda jika data dari database)
  const fmtPersen = (val) => {
    if (val == null) return "N/A";
    if (Math.abs(val) > 1) return Number(val).toFixed(2) + "%";
    return (val * 100).toFixed(2) + "%";
  };

  const fmtRupiah = (val) =>
    val != null ? "Rp " + Number(val).toLocaleString("id-ID") : "Rp 0";

  // Helper: Parse GenAI text menjadi komponen visual premium
  const renderGenAISections = (text) => {
    if (!text) return null;

    const lines = text.split("\n").map((l) => l.trim());

    const paragraphs = [];
    const tips = [];
    const analysisBullets = [];
    const disclaimer = [];

    let currentCategory = "intro";

    lines.forEach((line) => {
      if (line.startsWith("👋") || line.toLowerCase().includes("hallo sobat")) {
        paragraphs.push(line);
        return;
      }
      if (line.includes("━━━━━━━━━━━━━━━━━━")) {
        return;
      }
      if (
        line.includes("KOMPOSISI PORTOFOLIO") ||
        line.includes("DATA PORTOFOLIO")
      ) {
        currentCategory = "stocks"; // Skip rendering teks mentah alokasi karena sudah ada tabel native
        return;
      }
      if (line.includes("ANALISIS FINANSIAL") || line.includes("🛡️")) {
        currentCategory = "analysis";
        return;
      }
      if (
        line.includes("Strategi yang Bisa Dipertimbangkan") ||
        line.includes("Rencana Aksi & Strategi") ||
        line.includes("💡")
      ) {
        currentCategory = "tips";
        return;
      }
      if (
        line.startsWith("⚠️") ||
        line.includes("proyeksi berdasarkan") ||
        line.includes("jaminan keuntungan") ||
        line.includes("Analisis ini merupakan proyeksi")
      ) {
        disclaimer.push(line.replace("⚠️", "").trim());
        return;
      }

      if (line.startsWith("👉")) {
        tips.push(line.replace("👉", "").trim());
      } else if (line.startsWith("*") || line.startsWith("-")) {
        const cleanLine = line.replace(/^[\*\-\u2022]\s*/, "").trim();
        if (currentCategory === "tips") {
          tips.push(cleanLine.replace(/\*\*/g, ""));
        } else if (currentCategory === "analysis") {
          analysisBullets.push(cleanLine);
        } else if (currentCategory === "intro") {
          paragraphs.push(line);
        }
      } else if (line.length > 0) {
        if (currentCategory === "analysis") {
          analysisBullets.push(line);
        } else if (currentCategory === "intro") {
          paragraphs.push(line);
        }
      }
    });

    // Deteksi keberadaan short selling dari teks atau porsi alokasi murni
    const hasShortSelling =
      (text &&
        (text.toLowerCase().includes("short selling") ||
          text.toLowerCase().includes("negatif"))) ||
      pData?.portfolio?.some((stock) => stock.weight < 0);

    return (
      <div className="flex flex-col gap-6 w-full text-slate-700">
        {/* Welcome / Greeting Card */}
        {paragraphs.length > 0 && (
          <div className="bg-gradient-to-r from-blue-50/70 to-indigo-50/50 border border-blue-100/60 rounded-2xl p-6 shadow-sm animate-fade-in">
            <h4 className="text-lg font-black text-smart-navy mb-3 flex items-center gap-2">
              <span className="animate-waving-hand text-xl">👋</span> Hallo
              Sobat SmartInvest!
            </h4>
            <div className="flex flex-col gap-3">
              {paragraphs.slice(1).map((p, i) => (
                <p
                  key={i}
                  className="text-sm text-slate-600 leading-relaxed font-semibold"
                >
                  {p
                    .replace(/\*\*/g, "")
                    .replace("👋 Hallo Sobat SmartInvest!", "")}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Short Selling Warning Badge */}
        {hasShortSelling && (
          <div className="bg-gradient-to-r from-rose-50 to-red-50/60 border border-red-200/80 rounded-2xl p-6 shadow-sm animate-fade-in flex gap-4 items-start">
            <span className="text-2xl shrink-0">⚠️</span>
            <div>
              <p className="text-xs font-black text-rose-700 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                Alokasi Bobot Negatif (Short Selling) Terdeteksi! 🚨
              </p>
              <p className="text-xs text-slate-600 leading-relaxed font-bold">
                Portofolio ini mencakup posisi Short Selling (bobot negatif) pada emiten tertentu sebagai bagian dari optimasi kuantitatif. Strategi ini memanfaatkan potensi koreksi harga saham sebagai pelindung nilai (hedging), namun memiliki profil risiko asimetris yang memerlukan pengawasan aktif dan batas stop-loss yang disiplin.
              </p>
            </div>
          </div>
        )}

        {/* Dedicated Analisis Finansial Pintar Card */}
        {analysisBullets.length > 0 && (
          <div className="bg-gradient-to-br from-indigo-50/40 via-white to-blue-50/30 border border-blue-100 rounded-2xl p-6 shadow-sm overflow-hidden relative animate-fade-in">
            <div className="absolute right-0 top-0 w-64 h-64 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />
            <p className="text-xs font-bold text-indigo-600 uppercase tracking-wider mb-4 flex items-center gap-2">
              <span className="flex h-2.5 w-2.5 rounded-full bg-indigo-500 animate-pulse" />
              <span>🛡️ Analisis Finansial Pintar</span>
            </p>
            <div className="flex flex-col gap-4">
              {analysisBullets.map((bullet, i) => {
                const parts = bullet.split("**");
                if (parts.length >= 3) {
                  const title = parts[1].replace(/:$/, "").trim();
                  const description = parts
                    .slice(2)
                    .join("**")
                    .replace(/^:\s*/, "")
                    .trim();
                  return (
                    <div
                      key={i}
                      className="bg-white border border-blue-50/50 rounded-xl p-4 transition-all hover:scale-[1.005] hover:shadow-sm shadow-sm"
                    >
                      <h5 className="text-xs font-black text-indigo-700 mb-1.5 flex items-center gap-2">
                        <span>✨</span> {title}
                      </h5>
                      <p className="text-xs text-slate-600 leading-relaxed font-semibold">
                        {description.replace(/\*\*/g, "")}
                      </p>
                    </div>
                  );
                }
                return (
                  <div
                    key={i}
                    className="bg-white border border-blue-50/50 rounded-xl p-4"
                  >
                    <p className="text-xs text-slate-600 leading-relaxed font-semibold">
                      {bullet.replace(/\*\*/g, "")}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Actionable Tips Card */}
        {tips.length > 0 && (
          <div className="bg-emerald-50/20 border border-emerald-100/60 rounded-2xl p-6 shadow-sm animate-fade-in">
            <p className="text-xs font-bold text-emerald-700 uppercase tracking-wider mb-4 flex items-center gap-1.5">
              <span>💡</span> Rencana Aksi & Strategi Portofolio
            </p>
            <div className="flex flex-col gap-3">
              {tips.map((t, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 bg-white/60 border border-white rounded-xl p-3 shadow-inner"
                >
                  <div className="w-5 h-5 rounded-full bg-emerald-500 text-white flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">
                    ✓
                  </div>
                  <p className="text-xs text-slate-700 leading-relaxed font-semibold">
                    {t.replace(/\*\*/g, "")}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Alert Disclaimer */}
        {disclaimer.length > 0 && (
          <div className="bg-amber-50/60 border border-amber-200/50 rounded-xl p-4 flex items-start gap-3 animate-fade-in">
            <span className="text-sm shrink-0">⚠️</span>
            <p className="text-xs text-amber-800 leading-relaxed font-semibold">
              {disclaimer.join(" ").replace(/\*\*/g, "")}
            </p>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 min-h-[85vh]">
      <main className="w-full mx-auto flex flex-col gap-6">
        {/* HEADER HALAMAN */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-gray-100">
          <div>
            <h1 className="text-2xl font-bold text-smart-navy">
              Analisis Kuantitatif Portofolio & IHSG
            </h1>
            <p className="text-gray-400 text-sm mt-0.5">
              Sinkronisasi Alokasi Kuantitatif Terpilih dengan Prediksi Arah AI
              Makro bursa.
            </p>
          </div>
          {analysisCompleted && result && !isArchiveMode && (
            <button
              onClick={() => setIsAnalysisModalOpen(true)}
              className="bg-white border border-gray-200 text-gray-600 px-4 py-2.5 rounded-xl text-xs font-bold hover:bg-gray-50 flex items-center gap-2 shadow-sm transition-all text-center shrink-0"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                <path d="M3 3v5h5" />
              </svg>
              Hitung Ulang Analisis
            </button>
          )}
        </div>

        {!analysisCompleted || !result ? (
          <section className="flex flex-col items-center justify-center py-24 bg-gray-50/50 rounded-2xl border border-dashed border-gray-200 transition-all">
            <button
              onClick={() => setIsAnalysisModalOpen(true)}
              className="group w-24 h-24 bg-emerald-50 rounded-[2rem] flex items-center justify-center text-smart-green mb-6 shadow-inner hover:scale-105 hover:bg-emerald-100/70 transition-all border border-emerald-100"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="48"
                height="48"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="group-hover:rotate-12 transition-transform"
              >
                <rect x="4" y="4" width="16" height="16" rx="2" />
                <rect x="9" y="9" width="6" height="6" />
                <line x1="9" y1="1" x2="9" y2="4" />
                <line x1="15" y1="1" x2="15" y2="4" />
                <line x1="9" y1="20" x2="9" y2="23" />
                <line x1="15" y1="20" x2="15" y2="23" />
                <line x1="20" y1="9" x2="23" y2="9" />
                <line x1="20" y1="15" x2="23" y2="15" />
                <line x1="1" y1="9" x2="4" y2="9" />
                <line x1="1" y1="15" x2="4" y2="15" />
              </svg>
            </button>
            <h2 className="text-xl font-bold text-smart-navy mb-1">
              Optimasi Portofolio Anda
            </h2>
            <p className="text-gray-400 text-sm font-medium mb-6 text-center max-w-sm px-4">
              Tentukan target indeks bursa dan model perhitungan manajemen
              risiko yang Anda inginkan.
            </p>
            <button
              onClick={() => setIsAnalysisModalOpen(true)}
              className="bg-smart-navy text-white font-bold px-6 py-3 rounded-xl text-sm transition-opacity hover:opacity-90 shadow-sm"
            >
              Konfigurasi Parameter Perhitungan
            </button>
          </section>
        ) : (
          <div className="flex flex-col gap-6 animate-fade-in w-full">
            {/* Info strip ringkas */}
            <div className="bg-smart-navy text-white rounded-2xl px-6 py-4 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 relative overflow-hidden w-full">
              <div className="absolute -right-6 -bottom-6 w-24 h-24 bg-white/5 rounded-full blur-xl pointer-events-none" />
              <div className="flex items-center gap-3 relative z-10">
                <div className="w-10 h-10 rounded-xl bg-smart-green/20 flex items-center justify-center">
                  <span className="text-lg">🧮</span>
                </div>
                <div>
                  <p className="text-sm font-black tracking-wide">
                    Metode: {metaForm?.model_choice}
                  </p>
                  <p className="text-[10px] text-gray-400 uppercase tracking-wider">
                    Indeks {iData?.metadata?.index_choice} • BI Rate{" "}
                    {iData?.metadata?.bi_rate}%
                  </p>
                </div>
              </div>
              <div className="text-left sm:text-right relative z-10">
                <p className="text-[10px] uppercase tracking-wider font-bold text-gray-400">
                  Periode Historis
                </p>
                <p className="text-xs font-bold text-white mt-0.5">
                  {metaForm?.start_date} — {metaForm?.end_date}
                </p>
              </div>
            </div>

            {/* Tabel Komposisi */}
            <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm w-full">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
                <h3 className="font-bold text-smart-navy text-base flex items-center gap-2">
                  <span>📊</span> Komposisi Alokasi Saham Pilihan (
                  {metaForm?.model_choice})
                </h3>
              </div>

              <div className="overflow-x-auto rounded-xl border border-gray-100">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="bg-gray-50/70 text-gray-500 font-bold border-b border-gray-100 text-xs uppercase tracking-wider">
                      <th className="p-4">Ticker</th>
                      <th className="p-4">Sektor</th>
                      <th className="p-4">Bobot</th>
                      <th className="p-4 text-right">Alokasi Dana</th>
                      <th className="p-4 text-center">Tren</th>
                      <th className="p-4 text-center">Rekomendasi</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50 text-gray-600 font-medium">
                    {(() => {
                      const isCAPM = metaForm?.model_choice === "CAPM";
                      const stocksToRender = isCAPM
                        ? pData?.portfolio?.slice(0, 10)
                        : pData?.portfolio;

                      return stocksToRender?.map((stock, idx) => {
                        const isShort = stock.weight < 0;
                        return (
                          <tr
                            key={idx}
                            className="hover:bg-gray-50/30 transition-colors"
                          >
                            <td className="p-4">
                              <span className="font-bold text-smart-navy block">
                                {stock.ticker?.replace(".JK", "")}
                              </span>
                              <span className="text-[10px] text-gray-400 font-normal block max-w-[150px] truncate">
                                {stock.fullname}
                              </span>
                            </td>
                            <td className="p-4 text-gray-700">
                              {stock.sector}
                            </td>

                            {/* ── BOBOT DAN ALOKASI OTOMATIS MERAH JIKA SHORT SELLING ── */}
                            <td
                              className={`p-4 font-bold ${isShort ? "text-red-500" : "text-gray-700"}`}
                            >
                              {fmtPersen(stock.weight)}
                            </td>
                            <td
                              className={`p-4 text-right font-bold ${isShort ? "text-red-500" : "text-smart-green"}`}
                            >
                              {fmtRupiah(stock.allocation)}
                            </td>

                            {/* ── COLUMN TREN BADGE SOLID SINKRON ── */}
                            <td className="p-4 text-center relative">
                              <div className="inline-block group relative cursor-help">
                                <span
                                  className={`px-3 py-1 rounded-full text-xs font-bold tracking-wide transition-all min-w-[75px] inline-block text-center text-white ${
                                    stock.trend === "Bullish"
                                      ? "bg-emerald-500 border border-emerald-600"
                                      : stock.trend === "Bearish"
                                        ? "bg-red-500 border border-red-600"
                                        : "bg-amber-500 border border-amber-600"
                                  }`}
                                >
                                  {stock.trend || "Sideways"}
                                </span>

                                <div className="absolute left-full top-1/2 -translate-y-1/2 ml-2 hidden group-hover:block w-56 p-2.5 bg-slate-900 text-white text-[11px] rounded-lg shadow-xl z-50 text-left leading-normal font-normal pointer-events-none transition-all animate-fade-in">
                                  <p className="font-bold border-b border-slate-700 pb-1 mb-1 flex items-center gap-1 text-white">
                                    <span>
                                      {stock.trend === "Bullish"
                                        ? "📈"
                                        : stock.trend === "Bearish"
                                          ? "📉"
                                          : "📊"}
                                    </span>
                                    Arti Kondisi: {stock.trend || "Sideways"}
                                  </p>
                                  <p className="text-slate-300 font-medium">
                                    {stock.trend === "Bullish" &&
                                      "Harga saham cenderung naik secara konsisten dalam jangka pendek-menengah. Sinyal kuat untuk akumulasi/beli."}
                                    {stock.trend === "Bearish" &&
                                      "Harga saham cenderung turun secara konsisten. Risiko penurunan tinggi, disarankan waspada/hindari."}
                                    {(stock.trend === "Sideways" ||
                                      !stock.trend) &&
                                      "Harga bergerak mendatar dalam rentang konsolidasi terbatas tanpa arah naik/turun yang dominan."}
                                  </p>
                                  <div className="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-[6px] border-t-transparent border-b-[6px] border-b-transparent border-r-[6px] border-r-slate-900" />
                                </div>
                              </div>
                            </td>

                            {/* ── COLUMN REKOMENDASI BADGE SOLID SINKRON ── */}
                            <td className="p-4 text-center relative">
                              <div className="inline-block group relative cursor-help">
                                <span
                                  className={`px-3 py-1 rounded-full text-xs font-bold tracking-wide transition-all min-w-[75px] inline-block text-center text-white ${
                                    stock.recommendation === "BUY"
                                      ? "bg-emerald-500 border border-emerald-600"
                                      : stock.recommendation === "HOLD"
                                        ? "bg-amber-500 border border-amber-600"
                                        : "bg-red-500 border border-red-600"
                                  }`}
                                >
                                  {stock.recommendation || "HOLD"}
                                </span>

                                <div className="absolute right-full top-1/2 -translate-y-1/2 mr-2 hidden group-hover:block w-56 p-2.5 bg-slate-900 text-white text-[11px] rounded-lg shadow-xl z-50 text-left leading-normal font-normal pointer-events-none transition-all animate-fade-in">
                                  <p className="font-bold border-b border-slate-700 pb-1 mb-1 flex items-center gap-1 text-white">
                                    <span>
                                      {stock.recommendation === "BUY"
                                        ? "🟢"
                                        : stock.recommendation === "HOLD"
                                          ? "🟡"
                                          : "🔴"}
                                    </span>
                                    Saran: {stock.recommendation || "HOLD"}
                                  </p>
                                  <p className="text-slate-300 font-medium">
                                    {stock.recommendation === "BUY" &&
                                      "Model menyarankan untuk melakukan pembelian alokasi dana secara penuh pada harga pasar saat ini karena momentum pertumbuhan."}
                                    {stock.recommendation === "HOLD" &&
                                      "Disarankan mempertahankan kepemilikan lot saham saat ini sembari memantau volatilitas, jangan menambah posisi dulu."}
                                    {stock.recommendation === "AVOID" &&
                                      "Sinyal risiko teknis terdeteksi tinggi. Sebaiknya hindari membeli saham ini untuk mengamankan modal tunai Anda."}
                                  </p>
                                  <div className="absolute left-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-[6px] border-t-transparent border-b-[6px] border-b-transparent border-l-[6px] border-l-slate-900" />
                                </div>
                              </div>
                            </td>
                          </tr>
                        );
                      });
                    })()}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Narasi AI Interpretasi */}
            {pData?.portfolio_summary && (
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm flex flex-col w-full overflow-hidden">
                <div className="bg-gradient-to-r from-smart-navy via-[#1a2740] to-smart-navy px-6 py-4 flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-smart-green/20 flex items-center justify-center">
                    <span className="text-base">💡</span>
                  </div>
                  <div>
                    <h3 className="font-bold text-white text-base">
                      Interpretasi Pintar AI
                    </h3>
                    <p className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">
                      Analisis Naratif oleh SmartInvest AI •{" "}
                      {metaForm?.model_choice}
                    </p>
                  </div>
                </div>
                <div className="p-6 flex flex-col gap-3">
                  {renderGenAISections(pData?.portfolio_summary)}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

function TrendIcon({ up, size = 11 }) {
  return up ? (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
    >
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
      <polyline points="17 6 23 6 23 12" />
    </svg>
  ) : (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
    >
      <polyline points="23 18 13.5 8.5 8.5 13.5 1 6" />
      <polyline points="17 18 23 18 23 12" />
    </svg>
  );
}
