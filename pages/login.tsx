import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/router";
import type { NextPage } from "next";

import { useAuth } from "../context/AuthContext";

const LoginPage: NextPage = () => {
  const router = useRouter();
  const { login, authLoading, isAuthenticated } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const redirectTo = useMemo(() => {
    const value = router.query.next;
    return typeof value === "string" && value.startsWith("/") ? value : "/";
  }, [router.query.next]);

  if (!authLoading && isAuthenticated) {
    void router.replace(redirectTo);
  }

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!email || !password || isSubmitting) return;

    try {
      setIsSubmitting(true);
      setError(null);
      await login(email, password);
      await router.replace(redirectTo);
    } catch {
      setError("Invalid login credentials.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg p-6">
      <div className="w-full max-w-md rounded-2xl border border-borderLight bg-card p-6 shadow-sm transition-all duration-200 ease-in-out hover:-translate-y-0.5 hover:shadow-md">
        <h1 className="text-2xl font-semibold text-navy">Sign In</h1>
        <p className="mt-2 text-sm text-muted">Access your fintech dashboard securely.</p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-navy">Email</label>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="h-10 w-full rounded-lg border border-borderLight px-3 text-sm outline-none ring-primary/30 transition-all duration-200 ease-in-out focus:ring-2"
              placeholder="you@company.com"
              autoComplete="email"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-navy">Password</label>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="h-10 w-full rounded-lg border border-borderLight px-3 text-sm outline-none ring-primary/30 transition-all duration-200 ease-in-out focus:ring-2"
              placeholder="Enter your password"
              autoComplete="current-password"
            />
          </div>

          {error ? <p className="text-sm text-danger">{error}</p> : null}

          <button
            type="submit"
            disabled={isSubmitting || authLoading}
            className="h-10 w-full rounded-lg bg-primary text-sm font-semibold text-white transition-all duration-200 ease-in-out hover:brightness-110 active:scale-95 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Signing in..." : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
