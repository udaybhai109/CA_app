import { apiRequest } from "./api";

const AUTH_COOKIE = "is_authenticated";

const setAuthCookie = () => {
  if (typeof document === "undefined") return;
  document.cookie = `${AUTH_COOKIE}=1; path=/; max-age=${7 * 24 * 60 * 60}; samesite=lax`;
};

const clearAuthCookie = () => {
  if (typeof document === "undefined") return;
  document.cookie = `${AUTH_COOKIE}=; path=/; max-age=0; samesite=lax`;
};

const persistToken = (token: string | null) => {
  if (typeof window === "undefined") return;

  if (token) {
    window.localStorage.setItem("token", token);
    return;
  }

  window.localStorage.removeItem("token");
};

export const register = async (
  email: string,
  password: string,
  role = "business"
) => {
  return apiRequest("/register", {
    method: "POST",
    body: JSON.stringify({ email, password, role }),
  });
};

export const login = async (email: string, password: string): Promise<string> => {
  const data = await apiRequest<{ access_token?: string }>("/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  const accessToken = data.access_token;
  if (!accessToken) {
    throw new Error("Access token not returned from login.");
  }

  persistToken(accessToken);
  setAuthCookie();
  return accessToken;
};

export const logout = async (): Promise<void> => {
  try {
    await apiRequest("/logout", { method: "POST" });
  } finally {
    persistToken(null);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem("role");
    }
    clearAuthCookie();
  }
};

export const refreshAccessToken = async (): Promise<string> => {
  const data = await apiRequest<{ access_token?: string }>("/refresh", {
    method: "POST",
  });

  const accessToken = data.access_token;
  if (!accessToken) {
    persistToken(null);
    clearAuthCookie();
    throw new Error("Access token not returned from refresh.");
  }

  persistToken(accessToken);
  setAuthCookie();
  return accessToken;
};
