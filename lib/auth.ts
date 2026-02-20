import axios from "axios";

const authApi = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API,
  withCredentials: true,
});

const AUTH_COOKIE = "is_authenticated";

const setAuthCookie = () => {
  if (typeof document === "undefined") return;
  document.cookie = `${AUTH_COOKIE}=1; path=/; max-age=${7 * 24 * 60 * 60}; samesite=lax`;
};

const clearAuthCookie = () => {
  if (typeof document === "undefined") return;
  document.cookie = `${AUTH_COOKIE}=; path=/; max-age=0; samesite=lax`;
};

export const login = async (email: string, password: string): Promise<string> => {
  const response = await authApi.post("/login", { email, password });
  const accessToken = response.data?.access_token as string;
  if (!accessToken) {
    throw new Error("Access token not returned from login.");
  }
  setAuthCookie();
  return accessToken;
};

export const logout = async (): Promise<void> => {
  try {
    await authApi.post("/logout");
  } finally {
    clearAuthCookie();
  }
};

export const refreshAccessToken = async (): Promise<string> => {
  const response = await authApi.post("/refresh");
  const accessToken = response.data?.access_token as string;
  if (!accessToken) {
    clearAuthCookie();
    throw new Error("Access token not returned from refresh.");
  }
  setAuthCookie();
  return accessToken;
};
