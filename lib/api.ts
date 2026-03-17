const API = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

type RateRow = Record<string, unknown>;

type RatesResponse = {
  rates: RateRow[];
};

const getApiUrl = (path: string) => {
  if (!API) {
    throw new Error("NEXT_PUBLIC_API_URL is not configured.");
  }

  return `${API}${path}`;
};

const getStoredToken = () => {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem("token");
};

const parseResponse = async (response: Response) => {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();
  return text ? { detail: text } : null;
};

export async function apiRequest<T = unknown>(path: string, options: RequestInit = {}) {
  const token = getStoredToken();
  const headers = new Headers(options.headers);
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;

  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(getApiUrl(path), {
    ...options,
    headers,
    credentials: "include",
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    const detail =
      data &&
      typeof data === "object" &&
      "detail" in data &&
      typeof data.detail === "string"
        ? data.detail
        : "API Error";

    throw new Error(detail);
  }

  return data as T;
}

export const getFinancialHealth = (userId: number) => {
  return apiRequest(`/financial-health/${userId}`);
};

export const getGstSummary = (userId: number, month: string) => {
  return apiRequest(`/gst-summary/${userId}/${month}`);
};

export const getAlerts = (userId: number) => {
  return apiRequest(`/alerts/${userId}`);
};

export const getPnl = (userId: number) => {
  return apiRequest(`/pnl/${userId}`);
};

export const getBalanceSheet = (userId: number) => {
  return apiRequest(`/balance-sheet/${userId}`);
};

export const getAdvice = (userId: number, question: string) => {
  const params = new URLSearchParams({ question });
  return apiRequest(`/advice/${userId}?${params.toString()}`);
};

export async function getAdminGstRates(): Promise<RateRow[] | RatesResponse> {
  return apiRequest<RateRow[] | RatesResponse>("/admin/gst-rates", {
    method: "GET",
  });
}

export const saveAdminGstRates = (rates: unknown) => {
  return apiRequest("/admin/gst-rates", {
    method: "POST",
    body: JSON.stringify({ rates }),
  });
};

export const uploadFile = (file: File) => {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest("/upload", {
    method: "POST",
    body: formData,
  });
};
