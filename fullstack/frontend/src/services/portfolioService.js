import axios from "axios";

const API =
  (import.meta.env.VITE_AI_BASE_URL || "https://galihpp123-smartinvestapi.hf.space").replace(/\/$/, "");

export const analyzePortfolio = async (payload) => {
  const envKey =
    import.meta.env.VITE_GEMINI_API_KEY ||
    (typeof window !== "undefined" ? localStorage.getItem("SMARTINVEST_GEMINI_KEY") : null);
  const body = envKey && !payload.gemini_api_key ? { ...payload, gemini_api_key: envKey } : payload;
  const response = await axios.post(`${API}/api/analyze-portfolio`, body);
  return response.data;
};
