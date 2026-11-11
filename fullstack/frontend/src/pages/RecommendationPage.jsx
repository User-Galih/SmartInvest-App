import { useState } from "react";

export default function RecommendationPage({ analysisCompleted, result, metaForm, setIsAnalysisModalOpen }) {
  const onOpenAnalysisModal = () => setIsAnalysisModalOpen(true);

  // Ambil objek utama dari response /api/predict-ihsg
  const iData = result?.ihsg_data; 

  if (!analysisCompleted || !iData) {
    return (
      <div className="flex flex-col items-center justify-center py-24 bg-gray-50/50 rounded-2xl border border-dashed border-gray-200 transition-all">
        <div className="w-20 h-20 bg-gray-100 rounded-2xl flex items-center justify-center mb-6 border border-gray-200/40">
          <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-gray-400">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
        </div>
        <h2 className="text-xl font-bold text-smart-navy mb-2">Halaman Belum Tersedia</h2>
        <p className="text-gray-400 text-sm font-medium text-center max-w-sm mb-6 px-4">
          Lakukan analisis terlebih dahulu di halaman Analysis untuk membuka konten dashboard rekomendasi AI.
        </p>
        <button
          onClick={onOpenAnalysisModal}
          className="bg-smart-navy text-white px-6 py-3 rounded-xl text-sm font-bold hover:opacity-90 transition-all flex items-center gap-2 shadow-sm"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="animate-pulse">
            <rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="15" x2="23" y2="15"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="15" x2="4" y2="15"/>
          </svg>
          Mulai Analysis
        </button>
      </div>
    );
  }

  const COLORS = [
    "#10b981", // Emerald
    "#3b82f6", // Blue
    "#f59e0b", // Amber
    "#ef4444", // Rose
    "#8b5cf6", // Purple
    "#ec4899", // Pink
    "#06b6d4", // Cyan
    "#14b8a6", // Teal
    "#f97316", // Orange
    "#64748b"  // Slate
  ];

  // Helper Formatter Pintar
  const fmtPersen = (val) => {
    if (val == null) return "N/A";
    return (Number(val) * 100).toFixed(2) + "%";
  };
  
  const fmtNum = (val) => (val != null ? Number(val).toFixed(4) : "N/A");
  const fmtRupiah = (val) => val != null ? "Rp " + Number(val).toLocaleString("id-ID") : "Rp 0";
  const fmtScore = (val) => val != null ? Number(val).toFixed(4) : "N/A";

  // Helper: Parse GenAI text into styled sections (premium rendering)
  const renderGenAISections = (text) => {
    if (!text) return null;

    const lines = text.split("\n").map(l => l.trim());
    
    // ── DIRECT METRIC INJECTION: LANGSUNG SESUAI PROPERTI JSON PAYLOAD BACKEND ──
    const expectedReturn = fmtPersen(iData?.best_method_metrics?.expected_return);
    const risiko = fmtPersen(iData?.best_method_metrics?.annual_risk);
    const sharpe = fmtNum(iData?.best_method_metrics?.sharpe_ratio);
    const gain = fmtRupiah(iData?.investment_simulation?.potential_gain);
    const loss = fmtRupiah(iData?.investment_simulation?.potential_loss);
    const initialAmountStr = fmtRupiah(iData?.investment_simulation?.initial_amount);

    const hasShortSelling = 
      (text && (text.toLowerCase().includes("short selling") || text.toLowerCase().includes("negatif"))) ||
      (iData?.portfolio_allocation?.some(stock => stock.weight < 0));

    const paragraphs = [];
    const terms = [];
    const tips = [];
    const comparisons = [];
    const disclaimer = [];

    let currentCategory = "intro";

    lines.forEach(line => {
      if (line.startsWith("👋") || line.toLowerCase().includes("hallo sobat")) {
        paragraphs.push(line);
        return;
      }
      if (line.includes("━━━━━━━━━━━━━━━━━━")) {
        return;
      }
      if (line.includes("DATA PENTING") || line.includes("HASIL PORTOFOLIO") || line.includes("DATA ANALISIS")) {
        currentCategory = "metrics";
        return;
      }
      if (line.includes("ALOKASI PORTOFOLIO") || line.includes("KOMPOSISI PORTOFOLIO") || line.includes("Komposisi alokasi saham")) {
        currentCategory = "stocks";
        return;
      }
      if (line.includes("ISTILAH INVESTASI")) {
        currentCategory = "terms";
        return;
      }
      if (line.includes("PERBANDINGAN METODE") || line.includes("PERBANDINGAN METODE LAIN")) {
        currentCategory = "comparison";
        return;
      }
      if (line.includes("tips yang harus Kamu lakukan") || line.includes("Tips Penting Rekomendasi") || line.includes("Beberapa tips")) {
        currentCategory = "tips";
        return;
      }
      if (line.startsWith("⚠️") || line.includes("jaminan keuntungan") || line.includes("proyeksi berdasarkan")) {
        disclaimer.push(line.replace("⚠️", "").trim());
        return;
      }

      if (line.startsWith("👉")) {
        tips.push(line.replace("👉", "").trim());
      } else if (line.startsWith("*") || line.startsWith("-")) {
        const cleanLine = line.replace(/^[\*\-\u2022]\s*/, "").trim();
        if (currentCategory === "terms") {
          const parts = cleanLine.split(":");
          if (parts.length >= 2) {
            terms.push({
              name: parts[0].replace(/\*\fail/g, "").replace(/\*\*/g, "").trim(),
              description: parts.slice(1).join(":").replace(/\*\*/g, "").trim()
            });
          } else {
            terms.push({ name: "Istilah", description: cleanLine.replace(/\*\*/g, "") });
          }
        } else if (currentCategory === "tips") {
          tips.push(cleanLine.replace(/\*\*/g, ""));
        } else if (currentCategory === "comparison") {
          comparisons.push(cleanLine);
        } else if (currentCategory === "intro") {
          paragraphs.push(line);
        }
      } else if (line.length > 0) {
        if (currentCategory === "metrics" || line.startsWith("💰") || line.startsWith("📉") || line.startsWith("🎯") || line.startsWith("💸")) {
          return;
        }
        if (currentCategory === "comparison") {
          comparisons.push(line);
        } else if (currentCategory === "intro") {
          paragraphs.push(line);
        }
      }
    });

    return (
      <div className="flex flex-col gap-6 w-full text-slate-700">
        {/* Welcome / Greeting Banner */}
        {paragraphs.length > 0 && (
          <div className="bg-gradient-to-br from-blue-50/80 via-white to-indigo-50/30 border border-blue-100/60 rounded-2xl p-6 shadow-sm relative overflow-hidden animate-fade-in">
            <div className="absolute right-0 top-0 w-32 h-32 bg-indigo-500/5 rounded-full blur-2xl pointer-events-none" />
            <h4 className="text-base font-black text-smart-navy mb-4 flex items-center gap-2">
              <span className="animate-waving-hand text-xl">👋</span> Hallo Sobat SmartInvest!
            </h4>
            <div className="flex flex-col gap-3">
              {paragraphs.slice(1).map((p, i) => (
                <p key={i} className="text-sm text-slate-600 leading-relaxed font-semibold">
                  {p.replace(/\*\*/g, "").replace("👋 Hallo Sobat SmartInvest!", "")}
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

        {/* Premium Metrics Grid Card */}
        {expectedReturn && (
          <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm animate-fade-in">
            <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4">🏆 METRIK PORTOFOLIO TERBAIK</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
              <div className="bg-emerald-50/50 border border-emerald-100 rounded-xl p-4 text-center">
                <p className="text-[10px] font-bold text-emerald-600 uppercase tracking-wide mb-1">Expected Return</p>
                <p className="text-xl font-black text-emerald-600">{expectedReturn}</p>
              </div>
              <div className="bg-rose-50/50 border border-rose-100 rounded-xl p-4 text-center">
                <p className="text-[10px] font-bold text-rose-600 uppercase tracking-wide mb-1">Risiko Tahunan</p>
                <p className="text-xl font-black text-rose-600">{risiko}</p>
              </div>
              <div className="bg-blue-50/50 border border-blue-100 rounded-xl p-4 text-center">
                <p className="text-[10px] font-bold text-blue-600 uppercase tracking-wide mb-1">Sharpe Ratio</p>
                <p className="text-xl font-black text-smart-navy">{sharpe}</p>
              </div>
            </div>
            {(gain || loss) && (
              <div className="bg-slate-50 border border-slate-100 rounded-xl p-4">
                <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide mb-2 text-center">Estimasi Keuntungan & Risiko (Modal Investasi {initialAmountStr})</p>
                <div className="grid grid-cols-2 gap-4 text-center">
                   <div className="border-r border-slate-200">
                     <p className="text-xs font-bold text-gray-500 mb-0.5">Potensi Untung</p>
                     <p className="text-sm font-black text-emerald-600">+{gain}</p>
                   </div>
                   <div>
                     <p className="text-xs font-bold text-gray-500 mb-0.5">Potensi Rugi</p>
                     <p className="text-sm font-black text-rose-500">-{loss}</p>
                   </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Glossary FAQ Grid */}
        {terms.length > 0 && (
          <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm animate-fade-in">
            <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4">📖 GLOSARIUM PINTAR FINANSIAL</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {terms.map((t, i) => (
                <div key={i} className="bg-slate-50 border border-slate-100 rounded-xl p-4 hover:border-slate-200 transition-colors">
                  <p className="text-xs font-bold text-smart-navy mb-1 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                    {t.name.replace(/\*\*/g, "")}
                  </p>
                  <p className="text-xs text-slate-500 leading-relaxed font-medium">
                    {t.description.replace(/\*\*/g, "")}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Dedicated Perbandingan Metode Card */}
        {comparisons.length > 0 && (
          <div className="bg-gradient-to-br from-indigo-50/40 via-white to-blue-50/30 border border-blue-100 rounded-2xl p-6 shadow-sm overflow-hidden relative animate-fade-in">
            <div className="absolute right-0 top-0 w-64 h-64 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />
            <p className="text-xs font-bold text-indigo-600 uppercase tracking-wider mb-4 flex items-center gap-2">
              <span className="flex h-2.5 w-2.5 rounded-full bg-indigo-500 animate-pulse" />
              <span>⚖️ Perbandingan & Evaluasi Metode Optimasi</span>
            </p>
            <div className="flex flex-col gap-4">
              {comparisons.map((comp, i) => {
                const isBest = comp.toLowerCase().includes("terbaik");
                const parts = comp.split(":");
                if (parts.length >= 2) {
                  const title = parts[0].replace(/-/, "").replace(/\*\*/g, "").trim();
                  const description = parts.slice(1).join(":").replace(" [Metode Terbaik]", "").replace("(Metode Terbaik)", "").replace(/\*\*/g, "").trim();
                  return (
                    <div key={i} className={`border rounded-xl p-4 transition-all hover:scale-[1.005] shadow-sm ${
                      isBest ? "bg-emerald-50/50 border-emerald-200" : "bg-white border-blue-50/50"
                    }`}>
                      <h5 className="text-xs font-black mb-1.5 flex items-center justify-between">
                        <span className={isBest ? "text-emerald-700" : "text-indigo-700"}>
                          {title}
                        </span>
                        {isBest && (
                          <span className="bg-emerald-500 text-white text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded animate-pulse">
                            Terbaik Terpilih
                          </span>
                        )}
                      </h5>
                      <p className="text-xs text-slate-600 leading-relaxed font-semibold">
                        {description}
                      </p>
                    </div>
                  );
                }
                return (
                  <div key={i} className="bg-white border border-blue-50/50 rounded-xl p-4">
                    <p className="text-xs text-slate-600 leading-relaxed font-semibold">
                      {comp.replace(/\*\*/g, "")}
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
              <span>💡</span> Tips Penting Rekomendasi
            </p>
            <div className="flex flex-col gap-3">
              {tips.map((t, i) => (
                <div key={i} className="flex items-start gap-3 bg-white/60 border border-white rounded-xl p-3 shadow-inner">
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
    <div className="flex flex-col gap-6 animate-fade-in">

      {/* HEADER UTAMA */}
      <div className="bg-smart-navy px-8 py-6 rounded-2xl flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 shadow-sm relative overflow-hidden">
        <div className="absolute -right-10 -top-10 w-32 h-32 bg-white/5 rounded-full blur-2xl pointer-events-none" />
        <div className="relative z-10">
          <h1 className="text-xl font-bold text-white">SmartInvest Portfolio Dashboard</h1>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <span className={`inline-flex items-center gap-1 text-[10px] font-black uppercase tracking-wide px-3 py-1 rounded-full ${
              iData?.ihsg_analysis?.market_trend === "Bullish" ? "bg-emerald-500/20 text-emerald-300" : "bg-rose-500/20 text-rose-300"
            }`}>
              Market Sentiment: {iData?.ihsg_analysis?.market_trend || "N/A"}
            </span>
          </div>
        </div>
        <div className="text-left sm:text-right relative z-10">
          <p className="text-[10px] uppercase tracking-wider font-bold text-gray-400">Periode Analisis Historis</p>
          <p className="text-sm font-bold text-white mt-0.5">
            {iData?.metadata?.start_date || "N/A"} — {iData?.metadata?.end_date || "N/A"}
          </p>
        </div>
      </div>

      {/* Kontainer 1: Grid Metrik Utama (4 Kolom) */}
      <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-50/60 border border-gray-100 rounded-xl p-4 text-center flex flex-col justify-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-smart-green">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
              </svg>
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Metode Terbaik</p>
            </div>
            <p className="text-xl font-black text-smart-navy">{iData?.decision_engine?.best_method || "N/A"}</p>
          </div>
          <div className="bg-emerald-50/40 border border-emerald-100/60 rounded-xl p-4 text-center flex flex-col justify-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-smart-green">
                <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>
              </svg>
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Expected Return</p>
            </div>
            <p className="text-xl font-black text-smart-green">{fmtPersen(iData?.best_method_metrics?.expected_return)}</p>
          </div>
          <div className="bg-rose-50/40 border border-rose-100/60 rounded-xl p-4 text-center flex flex-col justify-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-rose-500">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Risiko Tahunan</p>
            </div>
            <p className="text-xl font-black text-rose-500">{fmtPersen(iData?.best_method_metrics?.annual_risk)}</p>
          </div>
          <div className="bg-blue-50/30 border border-blue-100/50 rounded-xl p-4 text-center flex flex-col justify-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-500">
                <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
              </svg>
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Sharpe Ratio</p>
            </div>
            <p className="text-xl font-black text-smart-navy">{fmtNum(iData?.best_method_metrics?.sharpe_ratio)}</p>
          </div>
        </div>
      </div>

      {/* Kontainer 2.5: Estimasi 1 Tahun Dana Investasi */}
      <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm">
        <h2 className="text-base font-bold text-smart-navy mb-4 flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/xl" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-500">
            <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
          </svg>
          Estimasi Simulasi Dana 1 Tahun
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-blue-50/40 border border-blue-100/50 rounded-xl p-4 text-center flex flex-col justify-center">
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide mb-1">Modal Awal</p>
            <p className="text-lg font-black text-blue-600">{fmtRupiah(iData?.investment_simulation?.initial_amount)}</p>
          </div>
          <div className="bg-emerald-50/40 border border-emerald-100/60 rounded-xl p-4 text-center flex flex-col justify-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-smart-green">
                <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>
              </svg>
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Potensi Naik</p>
            </div>
            {/* MURNI MENGIKUTI VALUE DARI JSON PAYLOAD BACKEND SECARA RIYEL */}
            <p className="text-lg font-black text-smart-green">+{fmtRupiah(iData?.investment_simulation?.potential_gain)}</p>
          </div>
          <div className="bg-rose-50/40 border border-rose-100/60 rounded-xl p-4 text-center flex flex-col justify-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-rose-500">
                <polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/>
              </svg>
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">Potensi Turun</p>
            </div>
            {/* MURNI MENGIKUTI VALUE DARI JSON PAYLOAD BACKEND SECARA RIYEL */}
            <p className="text-lg font-black text-rose-500">-{fmtRupiah(iData?.investment_simulation?.potential_loss)}</p>
          </div>
        </div>
        <p className="text-[10px] text-gray-400 mt-3 leading-relaxed text-center">
          * Estimasi dihitung berdasarkan expected return dan risiko tahunan metode terbaik terhadap modal investasi awal.
        </p>
      </div>

      {/* Kontainer 3: Metrik Sekunder */}
      <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-gray-50 border border-gray-100 rounded-xl p-4 text-center">
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide mb-1">Beta Terhadap IHSG</p>
            <p className="text-lg font-bold text-gray-800">{fmtNum(iData?.best_method_metrics?.beta)}</p>
          </div>
          <div className="bg-gray-50 border border-gray-100 rounded-xl p-4 text-center">
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide mb-1">Alpha Penyesuaian</p>
            <p className="text-lg font-bold text-gray-800">{fmtNum(iData?.best_method_metrics?.alpha)}</p>
          </div>
          <div className="bg-gray-50 border border-gray-100 rounded-xl p-4 text-center">
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide mb-1">Rasio Treynor</p>
            <p className="text-lg font-bold text-gray-800">{fmtNum(iData?.best_method_metrics?.treynor_ratio)}</p>
          </div>
        </div>
      </div>

      {/* Kontainer 3: Alokasi Portofolio Dinamik */}
      <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm animate-fade-in">
        <h2 className="text-base font-bold text-smart-navy mb-4 flex items-center gap-2"><span>📊</span> Pembagian Porsi Dana Investasi</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
          <div className="flex items-center justify-center py-4">
            {(() => {
              const allocation = iData?.portfolio_allocation || [];
              const totalAbsWeight = allocation.reduce((sum, s) => sum + Math.abs(s.weight), 0);

              const radius = 70;
              const circ = 2 * Math.PI * radius;
              let currentOffset = 0;

              const donutSlices = allocation.map((stock, idx) => {
                const isShort = stock.weight < 0;
                const color = isShort ? "#ef4444" : COLORS[idx % COLORS.length];
                const percentage = Math.abs(stock.weight) / (totalAbsWeight || 1);
                const strokeLength = percentage * circ;
                const strokeOffset = currentOffset;
                currentOffset += strokeLength;

                return {
                  ticker: stock.ticker?.replace(".JK", ""),
                  color,
                  strokeLength,
                  strokeOffset,
                  weight: stock.weight,
                  isShort
                };
              });

              return (
                <div className="relative flex items-center justify-center">
                  <svg width="180" height="180" viewBox="0 0 200 200" className="drop-shadow-sm select-none">
                    <circle cx="100" cy="100" r={radius} fill="transparent" stroke="#f8fafc" strokeWidth="18" />
                    {donutSlices.map((slice, i) => (
                      <circle
                        key={i}
                        cx="100"
                        cy="100"
                        r={radius}
                        fill="transparent"
                        stroke={slice.color}
                        strokeWidth="18"
                        strokeDasharray={`${slice.strokeLength.toFixed(2)} ${(circ - slice.strokeLength).toFixed(2)}`}
                        strokeDashoffset={-slice.strokeOffset}
                        transform="rotate(-90 100 100)"
                        className="transition-all duration-1000 ease-out hover:stroke-[22px] cursor-pointer"
                        style={{ transitionDelay: `${i * 70}ms` }}
                        title={`${slice.ticker}: ${(slice.weight * 100).toFixed(1)}%`}
                      />
                    ))}
                    <circle cx="100" cy="100" r={radius - 9} fill="white" />
                  </svg>
                  <div className="absolute flex flex-col items-center justify-center text-center">
                    <span className="text-2xl font-black text-smart-navy leading-none">
                      {allocation.length}
                    </span>
                    <span className="text-[8px] font-bold text-gray-400 uppercase tracking-wider mt-1.5 leading-none">
                      {allocation.some(s => s.weight < 0) ? (
                        <>
                          <span className="text-emerald-600 font-extrabold">{allocation.filter(s => s.weight > 0).length}L</span>
                          {" / "}
                          <span className="text-rose-500 font-extrabold">{allocation.filter(s => s.weight < 0).length}S</span>
                        </>
                      ) : "Saham Pilihan"}
                    </span>
                  </div>
                </div>
              );
            })()}
          </div>
          
          <div className="flex flex-col gap-2 max-h-[300px] overflow-y-auto pr-1">
            {iData?.portfolio_allocation?.map((stock, i) => {
              const isShort = stock.weight < 0;
              const color = isShort ? "#ef4444" : COLORS[i % COLORS.length];
              return (
                <div key={i} className={`flex items-center justify-between py-2.5 px-4 border rounded-xl hover:bg-slate-50/50 transition-all ${
                  isShort ? "bg-rose-50/20 border-rose-100/70 hover:border-rose-200" : "bg-gray-50/70 border-gray-50/70 hover:border-gray-100"
                }`}>
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${isShort ? "animate-pulse" : ""}`} style={{ backgroundColor: color }} />
                    <span className="text-sm font-bold text-smart-navy shrink-0">{stock.ticker?.replace(".JK", "")}</span>
                    <span className="text-xs text-gray-400 truncate font-normal">{stock.fullname}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {isShort && (
                      <span className="bg-red-500 text-white text-[8px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded shadow-sm">SHORT</span>
                    )}
                    <span className={`text-sm font-bold ml-2 ${isShort ? "text-red-500" : "text-gray-700"}`}>{fmtPersen(stock.weight)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        <p className="text-xs font-semibold text-gray-400 mt-5 text-center bg-gray-50 py-2 rounded-xl border border-gray-100">
          Total Alokasi Modal Kerja: <span className="font-bold text-blue-600">{fmtRupiah(iData?.investment_simulation?.initial_amount)}</span>
        </p>
      </div>

      {/* Kontainer 4: Tabel Perbandingan Metode Ganda */}
      <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm">
        <h2 className="text-base font-bold text-smart-navy mb-4">Perbandingan Hasil 3 Metode Analisis</h2>
        <div className="overflow-x-auto rounded-xl border border-gray-100">
          <table className="w-full text-sm text-left whitespace-nowrap">
            <thead>
              <tr className="bg-gray-50 text-gray-500 font-bold border-b border-gray-100 text-xs uppercase tracking-wider">
                <th className="p-4">Nama Metode</th>
                <th className="p-4 text-center">Return</th>
                <th className="p-4 text-center">Risiko</th>
                <th className="p-4 text-center">Sharpe</th>
                <th className="p-4 text-center">Beta</th>
                <th className="p-4 text-center">Alpha</th>
                <th className="p-4 text-center">BI Rate Acuan</th>
                <th className="p-4 text-center">Final Score</th>
                <th className="p-4 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50 font-medium text-gray-600">
              {iData?.method_comparison?.map((m, idx) => (
                <tr key={idx} className={`hover:bg-gray-50/40 transition-colors ${m.is_best ? 'bg-emerald-50/20' : ''}`}>
                  <td className="p-4 font-bold text-smart-navy">{m.method}</td>
                  <td className="p-4 text-center text-emerald-600 font-bold">{fmtPersen(m.return)}</td>
                  <td className="p-4 text-center text-rose-500 font-bold">{fmtPersen(m.risk)}</td>
                  <td className="p-4 text-center text-gray-700 font-bold">{fmtNum(m.sharpe)}</td>
                  <td className="p-4 text-center text-gray-600">{fmtNum(m.beta)}</td>
                  <td className="p-4 text-center text-gray-600">{fmtNum(m.alpha)}</td>
                  <td className="p-4 text-center font-semibold text-gray-500">{iData?.metadata?.bi_rate != null ? iData.metadata.bi_rate + "%" : "N/A"}</td>
                  <td className="p-4 text-center">
                    <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-black tracking-wide ${
                      m.is_best ? 'bg-smart-green/10 text-smart-green border border-smart-green/20' : 'bg-gray-100 text-gray-500'
                    }`}>{fmtScore(m.final_score)}</span>
                  </td>
                  <td className="p-4 text-center">
                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-black tracking-wide flex items-center gap-1 ${
                      m.is_best ? "bg-smart-green text-white shadow-sm" : "bg-gray-100 text-gray-400"
                    }`}>{m.is_best ? "⭐ TERBAIK" : "PEMBANDING"}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-[10px] text-gray-400 mt-3 leading-relaxed px-1">
          * Return dan Risiko dihitung secara tahunan. Sharpe Ratio menggunakan risk-free rate BI terkini sebesar {iData?.metadata?.bi_rate || 5.8}%. Beta & Alpha dihitung terhadap volatilitas pergerakan pasar (IHSG). <strong>Final Score</strong> adalah skor pembobotan akhir yang digunakan Decision Engine untuk menentukan metode terbaik berdasarkan kondisi pasar.
        </p>
      </div>

      {/* Kontainer 5: Interpretasi AI */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="bg-gradient-to-r from-smart-navy via-[#1a2740] to-smart-navy px-6 py-4 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-smart-green/20 flex items-center justify-center"><span className="text-base">🤖</span></div>
          <div>
            <h2 className="text-base font-bold text-white">Interpretasi Rekomendasi Pintar AI</h2>
            <p className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">Rekomendasi Naratif oleh SmartInvest AI • {iData?.decision_engine?.best_method || 'N/A'}</p>
          </div>
        </div>
        {iData?.ai_interpretation && (
          <div className="p-6 flex flex-col gap-3">
            {renderGenAISections(iData.ai_interpretation)}
          </div>
        )}
      </div>

      {/* DISCLAIMER */}
      <div className="bg-amber-50/70 border border-amber-200/60 rounded-xl p-4 flex items-start gap-3">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-600 shrink-0 mt-0.5">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        <p className="text-xs text-amber-800 font-medium leading-relaxed">
          Disclaimer: Hasil analisis ini dihasilkan oleh mesin AI berdasarkan data historis dan model statistik kuantitatif bursa efek dari endpoint predict-ihsg.
        </p>
      </div>

    </div>
  );
}