import axios, { type AxiosError } from "axios";
import type { ApiError } from "./types/common.types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Inject JWT on every request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("wt_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Normalize errors; 401 clears session and reloads to login
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ error?: string; message?: string; detail?: string }>) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("wt_token");
      window.location.href = "/auth/login";
      return Promise.reject(error);
    }

    const apiError: ApiError = {
      status: error.response?.status ?? 0,
      code: error.response?.data?.error ?? "NETWORK_ERROR",
      message:
        error.response?.data?.message ??
        error.response?.data?.detail ??
        error.message,
    };
    return Promise.reject(apiError);
  }
);
