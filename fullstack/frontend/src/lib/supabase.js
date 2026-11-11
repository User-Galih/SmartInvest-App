import { createClient } from "@supabase/supabase-js";

const DEFAULT_SUPABASE_URL = "https://alsduqrfszpqktliknfe.supabase.co";
const DEFAULT_SUPABASE_ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFsc2R1cXJmc3pwcWt0bGlrbmZlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTQ0MjA0ODAsImV4cCI6MjEwOTk5NjQ4MH0.jq_DxhB_Y24yZcesaLy7cu2FDkcJbB5qxjYOw1PmMcU";

const supabaseUrl =
  import.meta.env.VITE_SUPABASE_URL || DEFAULT_SUPABASE_URL;

const supabaseKey =
  import.meta.env.VITE_SUPABASE_ANON_KEY || DEFAULT_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseKey);
