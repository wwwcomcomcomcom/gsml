import axios from "axios";
import { authStore } from "../lib/auth";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const api = axios.create({ baseURL });

api.interceptors.request.use((config) => {
  const token = authStore.get();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      authStore.clear();
      if (location.pathname !== "/") location.href = "/";
    }
    return Promise.reject(err);
  }
);

export type Me = {
  id: string;
  email: string;
  name: string;
  usage_limit: number;
  current_usage: number;
  max_concurrent: number;
};

export type KeyInfo = {
  prefix: string;
  expires_at: string;
  created_at: string;
};

export type IssuedKey = {
  api_key: string;
  prefix: string;
  expires_at: string;
};

export type UsageToday = { used: number; limit: number; reset_at: string };
export type UsageHistoryItem = { date: string; total_tokens: number; request_count: number };
