import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { login as loginRequest, logout as logoutRequest, refreshAccessToken } from "../lib/auth";
import { configureApiAuth } from "../lib/api";

type CurrentUser = {
  id: number;
  role: string;
};

type AuthContextValue = {
  currentUser: CurrentUser | null;
  isAuthenticated: boolean;
  accessToken: string | null;
  authLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const decodeToken = (token: string): CurrentUser | null => {
  try {
    const payloadSegment = token.split(".")[1];
    if (!payloadSegment) return null;
    const normalized = payloadSegment.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
    const payload = JSON.parse(atob(padded)) as { sub?: string; role?: string };
    if (!payload.sub) return null;
    return {
      id: Number(payload.sub),
      role: payload.role || "business",
    };
  } catch {
    return null;
  }
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  const applyAccessToken = useCallback((token: string | null) => {
    setAccessToken(token);
    setCurrentUser(token ? decodeToken(token) : null);
  }, []);

  useEffect(() => {
    configureApiAuth({
      getAccessToken: () => accessToken,
      setAccessToken: applyAccessToken,
    });
  }, [accessToken, applyAccessToken]);

  useEffect(() => {
    let mounted = true;

    const bootstrap = async () => {
      try {
        const refreshed = await refreshAccessToken();
        if (mounted) {
          applyAccessToken(refreshed);
        }
      } catch {
        if (mounted) {
          applyAccessToken(null);
        }
      } finally {
        if (mounted) {
          setAuthLoading(false);
        }
      }
    };

    void bootstrap();

    return () => {
      mounted = false;
    };
  }, [applyAccessToken]);

  const login = useCallback(
    async (email: string, password: string) => {
      const token = await loginRequest(email, password);
      applyAccessToken(token);
    },
    [applyAccessToken]
  );

  const logout = useCallback(async () => {
    await logoutRequest();
    applyAccessToken(null);
  }, [applyAccessToken]);

  const value = useMemo<AuthContextValue>(
    () => ({
      currentUser,
      isAuthenticated: !!accessToken,
      accessToken,
      authLoading,
      login,
      logout,
    }),
    [currentUser, accessToken, authLoading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};
