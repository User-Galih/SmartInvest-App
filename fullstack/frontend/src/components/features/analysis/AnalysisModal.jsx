import { useState, useEffect } from "react";
import toast from "react-hot-toast";
import { analyzePortfolio } from "../../../services/portfolioService";
import { predictIHSG } from "../../../services/ihsgService";
import { supabase } from "../../../services/supabaseClient";
import { saveInvestmentHistory } from "../../../services/investmentService";

const METHODS = [
  { value: "", label: "Pilih model analisis..." },
  { value: "MVEP", label: "MVEP (Minimum Variance)" },
  { value: "SIM", label: "SIM (Single Index Model)" },
  { value: "CAPM", label: "CAPM (Capital Asset Pricing)" },
];

const TARGET_INDICES = [
  { value: "", label: "Pilih indeks target..." },
  { value: "LQ45", label: "LQ45" },
  { value: "IDX30", label: "IDX30" },
];

export default function AnalysisModal({
  isOpen,
  onClose,
  onAnalysisComplete,
  preSelectedMethod = "",
}) {
  // ⚡ DEFAULT STATE KOSONG (TANPA DEFAULT VALUE) ⚡
  const [formData, setFormData] = useState({
    model_choice: "",
    index_choice: "",
    start_date: "",
    end_date: "",
    investment_amount: "",
  });
  const [errors, setErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      if (preSelectedMethod) {
        setFormData({
          model_choice: preSelectedMethod,
          index_choice: "",
          start_date: "",
          end_date: "",
          investment_amount: "",
        });
      } else {
        setFormData({
          model_choice: "",
          index_choice: "",
          start_date: "",
          end_date: "",
          investment_amount: "",
        });
      }
      setErrors({});
    }
  }, [isOpen, preSelectedMethod]);

  const handleChange = (field) => (e) => {
    const value =
      field === "investment_amount"
        ? e.target.value === ""
          ? ""
          : Number(e.target.value)
        : e.target.value;
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  // Batas maksimum dataset historis yang tersedia di bursa (2026-03-31)
  const MAX_DATASET_DATE = "2026-03-31";
  const effectiveMaxDate =
    new Date().toISOString().split("T")[0] > MAX_DATASET_DATE
      ? MAX_DATASET_DATE
      : new Date().toISOString().split("T")[0];

  const handleQuickSelect = (months) => {
    const [year, month, day] = effectiveMaxDate.split("-").map(Number);
    const targetDate = new Date(Date.UTC(year, month - 1 - months, 1));
    const targetYear = targetDate.getUTCFullYear();
    const targetMonth = targetDate.getUTCMonth();
    const daysInTargetMonth = new Date(
      Date.UTC(targetYear, targetMonth + 1, 0),
    ).getUTCDate();
    const clampedDay = Math.min(day, daysInTargetMonth);
    const startStr = `${targetYear}-${String(targetMonth + 1).padStart(2, "0")}-${String(clampedDay).padStart(2, "0")}`;

    setFormData((prev) => ({
      ...prev,
      start_date: startStr,
      end_date: effectiveMaxDate,
    }));

    // Opsional: hapus error jika user klik tombol cepat
    setErrors((prev) => ({ ...prev, start_date: null, end_date: null }));
  };

  const validateForm = () => {
    const localErrors = {};
    if (!formData.model_choice)
      localErrors.model_choice = "Model wajib dipilih";
    if (!formData.index_choice)
      localErrors.index_choice = "Indeks wajib dipilih";
    if (!formData.start_date)
      localErrors.start_date = "Tanggal mulai wajib diisi";
    if (!formData.end_date) localErrors.end_date = "Tanggal akhir wajib diisi";
    if (formData.start_date && formData.end_date) {
      const start = new Date(formData.start_date);
      const end = new Date(formData.end_date);
      if (end <= start) {
        localErrors.end_date = "Tanggal akhir harus setelah tanggal mulai";
      } else {
        const diffMs = end - start;
        const diffYears = diffMs / (1000 * 60 * 60 * 24 * 365.25);
        const diffMonths = diffMs / (1000 * 60 * 60 * 24 * 30.4375);
        if (diffMonths < 5) {
          localErrors.start_date = "Periode minimal 5 bulan";
        } else if (diffYears > 5) {
          localErrors.start_date = "Periode maksimal 5 tahun";
        }
      }
    }
    if (!formData.investment_amount || formData.investment_amount < 100000) {
      localErrors.investment_amount = "Minimal investasi adalah Rp 100.000";
    }
    return localErrors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isLoading) return;

    const localErrors = validateForm();
    if (Object.keys(localErrors).length > 0) {
      setErrors(localErrors);
      toast.error(Object.values(localErrors)[0]);
      return;
    }

    setErrors({});
    setIsLoading(true);

    try {
      // 1. Eksekusi tembakan paralel ke API Backend FastAPI
      const [portfolioRes, ihsgRes] = await Promise.all([
        analyzePortfolio(formData),
        predictIHSG(formData),
      ]);

      const combinedResponse = {
        portfolio_data: portfolioRes,
        ihsg_data: ihsgRes,
      };

      // 2. Kalkulasi metrik penyesuaian model untuk backup data
      const selectedMetrics = ihsgRes?.method_comparison?.find(
        (m) => m.method === formData.model_choice,
      );
      const finalReturn = selectedMetrics
        ? selectedMetrics.return
        : ihsgRes?.best_method_metrics?.expected_return ||
          portfolioRes?.expectedReturn ||
          0;
      const finalRisk = selectedMetrics
        ? selectedMetrics.risk
        : ihsgRes?.best_method_metrics?.annual_risk || portfolioRes?.risk || 0;
      const finalSharpe = selectedMetrics
        ? selectedMetrics.sharpe
        : ihsgRes?.best_method_metrics?.sharpe_ratio ||
          portfolioRes?.sharpeRatio ||
          0;

      // 3. PANGGIL SERVICE SERVICE BARU UNTUK SAVE AMAN KE SUPABASE
      try {
        const { error: dbError } = await saveInvestmentHistory({
          targetIndex: formData.index_choice,

          method: formData.model_choice,

          capital: Number(formData.investment_amount),

          expectedReturn: Number(finalReturn),

          risk: Number(finalRisk),

          sharpeRatio: Number(finalSharpe),

          marketSentiment: ihsgRes?.ihsg_analysis?.market_trend || "Sideways",

          biRate: Number(ihsgRes?.metadata?.bi_rate || 5.8),

          startDate: formData.start_date,

          endDate: formData.end_date,

          aiInterpretation: ihsgRes?.ai_interpretation || "",

          portfolioAllocation: portfolioRes?.portfolio || [],

          // ⭐ BARU
          analysisForm: formData,

          analysisResult: {
            portfolio_data: portfolioRes,

            ihsg_data: ihsgRes,
          },
        });

        if (dbError) throw new Error(dbError);
      } catch (dbError) {
        console.error(
          "Gagal menyimpan ke investment_histories Supabase via service:",
          dbError,
        );
      }

      // 4. Salurkan hasil kalkulasi ke state global App.jsx dan tutup tirai modal
      toast.success("Analisis Ganda Berhasil Terintegrasi!");
      onAnalysisComplete(combinedResponse, formData);
      onClose();
    } catch (error) {
      console.error(error);
      const detail = error?.response?.data?.detail;
      toast.error(
        detail
          ? `Gagal analisis: ${detail}`
          : "Gagal melakukan proses analisis data.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-smart-navy/60 backdrop-blur-sm p-6"
      onClick={(e) => e.target === e.currentTarget && !isLoading && onClose()}
    >
      {isLoading ? (
        /* ⚡ TAMPILAN LOADING PREMIUM KHUSUS (REVISI 5) ⚡ */
        <div className="bg-white rounded-2xl w-full max-w-md p-8 shadow-2xl border border-gray-100 flex flex-col items-center justify-center text-center gap-6 min-h-[380px] animate-fade-in">
          <div className="relative flex items-center justify-center my-2">
            {/* Glowing outer pulse rings */}
            <div className="absolute w-24 h-24 bg-emerald-500/10 rounded-full animate-ping" />
            <div className="absolute w-16 h-16 bg-smart-navy/5 rounded-full animate-pulse" />

            {/* Rotating central ring */}
            <div className="w-14 h-14 border-4 border-smart-green border-t-transparent rounded-full animate-spin shadow-md z-10" />
            <span className="absolute text-xl">🤖</span>
          </div>

          <div>
            <h3 className="text-lg font-extrabold text-smart-navy mb-1.5 animate-pulse">
              SmartInvest AI Sedang Bekerja...
            </h3>
            <p className="text-gray-400 text-xs max-w-xs mx-auto leading-relaxed">
              Harap tunggu sebentar. Sistem AI kami sedang memuat data historis
              bursa dan menyinkronkan metode alokasi portofolio terbaik untuk
              Anda.
            </p>
          </div>

          {/* Steps Progress Visual Checklist */}
          <div className="w-full bg-slate-50 border border-slate-100 rounded-xl p-4 flex flex-col gap-2.5 text-left">
            <div className="flex items-center gap-2.5 text-xs font-semibold text-slate-600">
              <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse shrink-0" />
              <span>Memuat data historis emiten BEI...</span>
            </div>
            <div className="flex items-center gap-2.5 text-xs font-semibold text-slate-600">
              <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse shrink-0" />
              <span>Mengalkulasi bobot efisiensi portofolio...</span>
            </div>
            <div className="flex items-center gap-2.5 text-xs font-semibold text-slate-500">
              <span className="w-2 h-2 bg-amber-400 rounded-full animate-pulse shrink-0" />
              <span>Menghasilkan narasi rekomendasi AI...</span>
            </div>
          </div>
        </div>
      ) : (
        /* TAMPILAN MODAL NORMAL */
        <div className="bg-white rounded-2xl w-full max-w-md p-8 shadow-2xl border border-gray-100 flex flex-col gap-6 max-h-[88vh] overflow-y-auto relative">
          <div>
            <h2 className="text-2xl font-bold text-smart-navy mb-1">
              Konfigurasi AI
            </h2>
            <p className="text-gray-400 text-sm font-medium">
              Masukkan parameter analisis baru Anda
            </p>
          </div>

          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            {/* Model */}
            <div
              className={`bg-gray-50 p-4 rounded-xl border flex flex-col gap-1 ${errors.model_choice ? "border-red-300" : "border-gray-50"}`}
            >
              <label className="text-[10px] uppercase tracking-wider font-bold text-gray-400">
                Model Analisis
              </label>
              <select
                value={formData.model_choice}
                onChange={handleChange("model_choice")}
                disabled={isLoading}
                className="bg-transparent text-sm font-bold text-smart-navy outline-none cursor-pointer"
              >
                {METHODS.map((m) => (
                  <option
                    key={m.value}
                    value={m.value}
                    disabled={m.value === "" && formData.model_choice !== ""}
                  >
                    {m.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Target Index */}
            <div
              className={`bg-gray-50 p-4 rounded-xl border flex flex-col gap-1 ${errors.index_choice ? "border-red-300" : "border-gray-50"}`}
            >
              <label className="text-[10px] uppercase tracking-wider font-bold text-gray-400">
                Indeks Target
              </label>
              <select
                value={formData.index_choice}
                onChange={handleChange("index_choice")}
                disabled={isLoading}
                className="bg-transparent text-sm font-bold text-smart-navy outline-none cursor-pointer"
              >
                {TARGET_INDICES.map((idx) => (
                  <option
                    key={idx.value}
                    value={idx.value}
                    disabled={idx.value === "" && formData.index_choice !== ""}
                  >
                    {idx.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Period */}
            <div
              className={`bg-gray-50 p-4 rounded-xl border flex flex-col gap-1 ${errors.start_date || errors.end_date ? "border-red-300" : "border-gray-50"}`}
            >
              <label className="text-[10px] uppercase tracking-wider font-bold text-gray-400">
                Periode Historis
              </label>
              <div className="flex gap-4 mt-1">
                <div className="flex-1 flex flex-col">
                  <span className="text-[9px] font-bold text-gray-400 mb-0.5">
                    Mulai
                  </span>
                  <input
                    type="date"
                    value={formData.start_date}
                    onChange={handleChange("start_date")}
                    min="2018-01-01"
                    max={effectiveMaxDate}
                    disabled={isLoading}
                    className="bg-transparent text-xs font-bold text-smart-navy outline-none border-b border-gray-200 pb-1"
                  />
                </div>
                <div className="flex-1 flex flex-col">
                  <span className="text-[9px] font-bold text-gray-400 mb-0.5">
                    Akhir
                  </span>
                  <input
                    type="date"
                    value={formData.end_date}
                    onChange={handleChange("end_date")}
                    min="2018-01-01"
                    max={effectiveMaxDate}
                    disabled={isLoading}
                    className="bg-transparent text-xs font-bold text-smart-navy outline-none border-b border-gray-200 pb-1"
                  />
                </div>
              </div>

              {/* radio button */}
              <div className="flex flex-wrap gap-x-4 gap-y-2 mt-3 px-1">
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    name="period"
                    className="accent-smart-navy h-3.5 w-3.5"
                    onChange={() => handleQuickSelect(6)}
                  />
                  <span className="text-[10px] font-bold text-gray-500">
                    6 Bulan
                  </span>
                </label>
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    name="period"
                    className="accent-smart-navy h-3.5 w-3.5"
                    onChange={() => handleQuickSelect(12)}
                  />
                  <span className="text-[10px] font-bold text-gray-500">
                    1 Tahun
                  </span>
                </label>
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    name="period"
                    className="accent-smart-navy h-3.5 w-3.5"
                    onChange={() => handleQuickSelect(24)}
                  />
                  <span className="text-[10px] font-bold text-gray-500">
                    2 Tahun
                  </span>
                </label>
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    name="period"
                    className="accent-smart-navy h-3.5 w-3.5"
                    onChange={() => handleQuickSelect(36)}
                  />
                  <span className="text-[10px] font-bold text-gray-500">
                    3 Tahun
                  </span>
                </label>
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    name="period"
                    className="accent-smart-navy h-3.5 w-3.5"
                    onChange={() => handleQuickSelect(60)}
                  />
                  <span className="text-[10px] font-bold text-gray-500">
                    5 Tahun
                  </span>
                </label>
              </div>

              {/* ⚡ REVISI 3: Keterangan Pilihan Cepat ⚡ */}
              <p className="text-[10px] text-gray-400 mt-2.5 leading-relaxed italic">
                * Pilihan cepat akan menarik data historis mundur dari tanggal
                hari ini (contoh: 6 Bulan / 1 Tahun Terakhir).
              </p>
            </div>

            {/* Investment Amount */}
            <div
              className={`
                bg-gray-50
                p-4
                rounded-xl
                border
                flex
                flex-col
                gap-1
                ${errors.investment_amount ? "border-red-300" : "border-gray-50"}
              `}
            >
              <label
                className="
                  text-[10px]
                  uppercase
                  tracking-wider
                  font-bold
                  text-gray-400
                "
              >
                Investment Amount
              </label>

              <div
                className="
                  flex
                  items-center
                  gap-2
                  mt-1
                "
              >
                <span
                  className="
                    text-sm
                    font-bold
                    text-gray-400
                  "
                >
                  Rp
                </span>

                <input
                  type="text"
                  inputMode="numeric"
                  placeholder="10.000.000"
                  value={
                    formData.investment_amount
                      ? new Intl.NumberFormat("id-ID").format(
                          formData.investment_amount,
                        )
                      : ""
                  }
                  onChange={(e) => {
                    const rawValue = e.target.value.replace(/\D/g, "");

                    setFormData((prev) => ({
                      ...prev,
                      investment_amount:
                        rawValue === "" ? "" : Number(rawValue),
                    }));
                  }}
                  disabled={isLoading}
                  className="
                    bg-transparent
                    text-sm
                    font-bold
                    text-smart-navy
                    outline-none
                    w-full
                    placeholder-gray-300
                  "
                />
              </div>

              {/* ⚡ REVISI 2: Batas & Keterangan Minimal Investasi ⚡ */}
              <span className="text-[10px] text-gray-400 mt-1 font-bold">
                * Minimal investasi Rp 100.000 (Seratus Ribu Rupiah)
              </span>
            </div>

            <div className="flex gap-3 mt-4">
              <button
                type="button"
                onClick={onClose}
                disabled={isLoading}
                className="flex-1 bg-gray-100 text-gray-600 py-3 rounded-xl font-bold text-sm hover:bg-gray-200 transition-all"
              >
                Batal
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="flex-[2] bg-smart-green text-white py-3 rounded-xl font-bold text-sm hover:bg-[#00b86a] transition-all flex items-center justify-center gap-2 shadow-sm"
              >
                Mulai Analisis
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
