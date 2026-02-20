import type { AppProps } from "next/app";
import { useRouter } from "next/router";

import Sidebar from "../components/Sidebar";
import { AuthProvider } from "../context/AuthContext";

export default function App({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const isLoginRoute = router.pathname === "/login";

  return (
    <AuthProvider>
      <div className="min-h-screen bg-bg" style={{ backgroundColor: "#F7FAFC" }}>
        {!isLoginRoute ? <Sidebar /> : null}
        <main
          className={`${isLoginRoute ? "" : "ml-[240px]"} min-h-screen bg-bg`}
          style={{ backgroundColor: "#F7FAFC" }}
        >
          <Component {...pageProps} />
        </main>
      </div>
    </AuthProvider>
  );
}
