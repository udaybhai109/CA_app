import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

import { refreshAccessToken } from "./auth";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API,
  withCredentials: true,
});
export const apiClient = api;

type AuthConfig = {
  getAccessToken: () => string | null;
  setAccessToken: (token: string | null) => void;
};

let authConfig: AuthConfig = {
  getAccessToken: () => null,
  setAccessToken: () => undefined,
};

let refreshPromise: Promise<string> | null = null;

type RetryRequestConfig = InternalAxiosRequestConfig & { _retry?: boolean };

export const configureApiAuth = (config: AuthConfig) => {
  authConfig = config;
};

api.interceptors.request.use((config) => {
  const token = authConfig.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryRequestConfig | undefined;

    if (!originalRequest || originalRequest._retry || error.response?.status !== 401) {
      return Promise.reject(error);
    }

    const url = originalRequest.url || "";
    if (url.includes("/login") || url.includes("/register") || url.includes("/refresh")) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      if (!refreshPromise) {
        refreshPromise = refreshAccessToken();
      }
      const newAccessToken = await refreshPromise;
      authConfig.setAccessToken(newAccessToken);
      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      return api(originalRequest);
    } catch (refreshError) {
      authConfig.setAccessToken(null);
      return Promise.reject(refreshError);
    } finally {
      refreshPromise = null;
    }
  }
);

export const getFinancialHealth = async (userId: number) => {
  const response = await api.get(`/financial-health/${userId}`);
  return response.data;
};

export const getGstSummary = async (userId: number, month: string) => {
  const response = await api.get(`/gst-summary/${userId}/${month}`);
  return response.data;
};

export const getAlerts = async (userId: number) => {
  const response = await api.get(`/alerts/${userId}`);
  return response.data;
};

export const getPnl = async (userId: number) => {
  const response = await api.get(`/pnl/${userId}`);
  return response.data;
};

export const getBalanceSheet = async (userId: number) => {
  const response = await api.get(`/balance-sheet/${userId}`);
  return response.data;
};

export const uploadFile = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};
