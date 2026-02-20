import { useEffect, useMemo, useState } from "react";
import type { NextPage } from "next";

import AIChat from "../components/AIChat";
import CashFlowChart from "../components/CashFlowChart";
import StatCard from "../components/StatCard";
import { getAlerts, getBalanceSheet, getFinancialHealth, getGstSummary, getPnl } from "../lib/api";

type FinancialHealthResponse = {
  current_ratio: number | null;
  net_profit_margin: number | null;
  cash_runway: number | null;
};

type GstSummaryResponse = {
  output_gst: number;
  input_gst: number;
  net_payable: number;
};

type PnlResponse = {
  revenues: Record<string, number>;
  expenses: Record<string, number>;
  total_revenue: number;
  total_expenses: number;
  net_profit: number;
};

type BalanceSheetResponse = {
  assets: Record<string, number>;
  liabilities: Record<string, number>;
  equity: Record<string, number>;
  total_assets: number;
  total_liabilities: number;
  total_equity: number;
};

type CashFlowDataPoint = {
  month: string;
  inflow: number;
  outflow: number;
};

const formatCurrency = (value: number | null | undefined) => {
  if (value === null || value === undefined) return "N/A";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
};

const HomePage: NextPage = () => {
  const [financialHealth, setFinancialHealth] = useState<FinancialHealthResponse | null>(null);
  const [gstSummary, setGstSummary] = useState<GstSummaryResponse | null>(null);
  const [pnl, setPnl] = useState<PnlResponse | null>(null);
  const [balanceSheet, setBalanceSheet] = useState<BalanceSheetResponse | null>(null);
  const [alerts, setAlerts] = useState<string[]>([]);
  const [cashFlowData, setCashFlowData] = useState<CashFlowDataPoint[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const currentMonth = useMemo(() => new Date().toISOString().slice(0, 7), []);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [financialHealthData, gstSummaryData, pnlData, balanceSheetData, alertsData] =
          await Promise.all([
            getFinancialHealth(1),
            getGstSummary(1, currentMonth),
            getPnl(1),
            getBalanceSheet(1),
            getAlerts(1),
          ]);

        const normalizedAlerts = Array.isArray(alertsData) ? alertsData : alertsData?.alerts || [];

        setFinancialHealth(financialHealthData);
        setGstSummary(gstSummaryData);
        setPnl(pnlData);
        setBalanceSheet(balanceSheetData);
        setAlerts(normalizedAlerts);
        setCashFlowData([
          {
            month: "Current",
            inflow: Number(pnlData?.total_revenue || 0),
            outflow: Number(pnlData?.total_expenses || 0),
          },
        ]);
      } catch {
        setError("Failed to load dashboard data");
      } finally {
        setLoading(false);
      }
    };

    void fetchDashboardData();
  }, [currentMonth]);

  const cashBalance = balanceSheet?.assets?.["Cash"];
  const netProfit = pnl?.net_profit;
  const gstPayable = gstSummary?.net_payable;
  const cashRunway = financialHealth?.cash_runway;

  return (
    <div className="min-h-screen bg-bg p-6 md:p-8">
      <header className="mb-8 flex items-center justify-between rounded-2xl bg-card p-5 shadow-sm">
        <div>
          <h1 className="text-2xl font-semibold text-navy">FinSight</h1>
          <p className="text-sm text-muted">Financial Command Center</p>
        </div>
        <div className="h-11 w-11 rounded-full bg-primary/15 ring-2 ring-primary/25" />
      </header>

      <main className="grid grid-cols-1 gap-6 xl:grid-cols-10">
        <section className="space-y-6 xl:col-span-7">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <StatCard
              title="Cash Balance"
              value={loading ? "Loading..." : formatCurrency(cashBalance)}
              color="#0B63FF"
            />
            <StatCard
              title="Net Profit"
              value={loading ? "Loading..." : formatCurrency(netProfit)}
              color="#00B37E"
            />
            <StatCard
              title="GST Payable"
              value={loading ? "Loading..." : formatCurrency(gstPayable)}
              color="#F59E0B"
            />
            <StatCard
              title="Cash Runway"
              value={
                loading
                  ? "Loading..."
                  : cashRunway === null || cashRunway === undefined
                    ? "N/A"
                    : `${cashRunway.toFixed(1)} months`
              }
              color="#0F172A"
            />
          </div>

          <div className="rounded-2xl bg-card p-6 shadow-sm">
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-navy">Cash Flow</h2>
              <p className="text-sm text-muted">Revenue vs expense for current period</p>
            </div>
            <CashFlowChart data={cashFlowData} />
          </div>

          <div className="rounded-2xl bg-card p-6 shadow-sm">
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-navy">Expense Donut</h2>
              <p className="text-sm text-muted">Category split placeholder</p>
            </div>
            <div className="flex h-64 items-center justify-center rounded-xl border border-dashed border-borderLight bg-bg text-sm text-muted">
              Expense donut chart placeholder
            </div>
          </div>
        </section>

        <aside className="space-y-6 xl:col-span-3">
          <div className="rounded-2xl bg-card p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold text-navy">AI Assistant</h2>
            <AIChat />
          </div>

          <div className="rounded-2xl bg-card p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold text-navy">Alerts</h2>
            {error ? (
              <p className="text-sm text-danger">{error}</p>
            ) : alerts.length === 0 ? (
              <p className="text-sm text-muted">No active alerts.</p>
            ) : (
              <ul className="space-y-3">
                {alerts.map((alertText, index) => (
                  <li
                    key={`${alertText}-${index}`}
                    className="rounded-xl border border-borderLight bg-bg p-3 text-sm text-navy"
                  >
                    {alertText}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>
      </main>
    </div>
  );
};

export default HomePage;
