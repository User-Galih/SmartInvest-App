import axios from "axios";

const API =
  (import.meta.env.VITE_AI_BASE_URL || "https://galihpp123-smartinvestapi.hf.space").replace(/\/$/, "");

export const predictIHSG = async (payload) => {
  const response = await axios.post(`${API}/api/predict-ihsg`, payload);
  return response.data;
};
