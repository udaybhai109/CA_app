import Link from "next/link";
import { useRouter } from "next/router";
import type { ComponentType, SVGProps } from "react";
import {
  ChartBarSquareIcon,
  DocumentChartBarIcon,
  HomeIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";

type NavItem = {
  label: string;
  href: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
};

const navItems: NavItem[] = [
  { label: "Dashboard", href: "/", icon: HomeIcon },
  { label: "Compliance", href: "/compliance", icon: ShieldCheckIcon },
  { label: "Reports", href: "/reports", icon: DocumentChartBarIcon },
  { label: "Admin", href: "/admin/rates", icon: ChartBarSquareIcon },
];

export default function Sidebar() {
  const router = useRouter();

  const isActive = (href: string) => {
    if (href.startsWith("/admin")) {
      return router.pathname.startsWith("/admin");
    }
    return router.pathname === href;
  };

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-[240px] bg-[#0F172A] text-white shadow-sm">
      <div className="border-b border-white/10 px-6 py-6">
        <h1 className="text-xl font-semibold tracking-tight">FinSight</h1>
        <p className="mt-1 text-xs text-white/60">Fintech Control Center</p>
      </div>

      <nav className="px-3 py-4">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);

            return (
              <li key={item.label}>
                <Link
                  href={item.href}
                  className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 ease-in-out ${
                    active ? "bg-white/10" : "text-white hover:bg-white/5"
                  }`}
                  style={active ? { color: "#0B63FF" } : undefined}
                >
                  <Icon className="h-5 w-5 shrink-0" />
                  <span>{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}
