import { useEffect, useState } from "react";
import type { NextPage } from "next";
import Head from "next/head";
import { getAdminGstRates, saveAdminGstRates } from "../../lib/api";

type GSTRateRow = {
  id?: number | string;
  hsn: string;
  rate: string;
  effective_from: string;
  effective_to: string;
};

const normalizeRateRow = (row: Record<string, unknown>, index: number): GSTRateRow => {
  return {
    id: (row.id as number | string | undefined) ?? `row-${index}`,
    hsn: String(row.hsn ?? row.HSN ?? ""),
    rate: String(row.rate ?? ""),
    effective_from: String(row.effective_from ?? row.effectiveFrom ?? ""),
    effective_to: String(row.effective_to ?? row.effectiveTo ?? ""),
  };
};

const AdminRatesPage: NextPage = () => {
  const [isCheckingAccess, setIsCheckingAccess] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [rows, setRows] = useState<GSTRateRow[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const role =
      window.localStorage.getItem("role") ||
      window.sessionStorage.getItem("role") ||
      "business";
    setIsAdmin(role === "admin");
    setIsCheckingAccess(false);
  }, []);

  useEffect(() => {
    if (isCheckingAccess || !isAdmin) return;

    const fetchRates = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const payload = await getAdminGstRates();
        const data = Array.isArray(payload) ? payload : payload?.rates;
        const normalized = Array.isArray(data)
          ? data.map((row, index) => normalizeRateRow(row as Record<string, unknown>, index))
          : [];
        setRows(normalized);
      } catch {
        setError("Failed to fetch GST rates.");
      } finally {
        setIsLoading(false);
      }
    };

    void fetchRates();
  }, [isCheckingAccess, isAdmin]);

  const updateCell = (index: number, field: keyof GSTRateRow, value: string) => {
    setRows((prev) =>
      prev.map((row, rowIndex) => (rowIndex === index ? { ...row, [field]: value } : row))
    );
  };

  const addRow = () => {
    setRows((prev) => [
      ...prev,
      {
        id: `new-${Date.now()}`,
        hsn: "",
        rate: "",
        effective_from: "",
        effective_to: "",
      },
    ]);
  };

  const saveRates = async () => {
    try {
      setIsSaving(true);
      setError(null);
      setSuccess(null);

      const payload = rows.map((row) => ({
        hsn: row.hsn.trim(),
        rate: Number(row.rate),
        effective_from: row.effective_from,
        effective_to: row.effective_to,
      }));

      await saveAdminGstRates(payload);
      setSuccess("GST rates saved successfully.");
    } catch {
      setError("Failed to save GST rates.");
    } finally {
      setIsSaving(false);
    }
  };

  if (isCheckingAccess) {
    return (
      <div className="min-h-screen bg-bg p-8">
        <div className="rounded-2xl border border-borderLight bg-card p-6 shadow-sm">
          <p className="text-sm text-muted">Checking access...</p>
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-bg p-8">
        <div className="mx-auto max-w-2xl rounded-2xl border border-borderLight bg-card p-8 text-center shadow-sm">
          <h1 className="text-xl font-semibold text-navy">Access Restricted</h1>
          <p className="mt-2 text-sm text-muted">
            This page is available only for users with the admin role.
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>Admin GST Rates</title>
      </Head>

      <div className="min-h-screen bg-bg p-6 md:p-8">
        <div className="mx-auto max-w-7xl space-y-6">
          <header className="rounded-2xl border border-borderLight bg-card p-6 shadow-sm">
            <h1 className="text-2xl font-semibold text-navy">GST Rate Management</h1>
            <p className="mt-1 text-sm text-muted">
              Configure HSN-based tax rates and effective periods.
            </p>
          </header>

          <section className="rounded-2xl border border-borderLight bg-card p-6 shadow-sm">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-navy">Rate Table</h2>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={addRow}
                  className="rounded-xl border border-borderLight bg-white px-4 py-2 text-sm font-medium text-navy"
                >
                  Add Row
                </button>
                <button
                  type="button"
                  onClick={saveRates}
                  disabled={isSaving || isLoading}
                  className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSaving ? "Saving..." : "Save"}
                </button>
              </div>
            </div>

            {error ? <p className="mb-4 text-sm text-danger">{error}</p> : null}
            {success ? <p className="mb-4 text-sm text-success">{success}</p> : null}

            <div className="overflow-x-auto rounded-xl border border-borderLight">
              <table className="min-w-full border-collapse">
                <thead>
                  <tr className="bg-bg text-left">
                    <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted">
                      HSN
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted">
                      Rate
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted">
                      Effective From
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted">
                      Effective To
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {isLoading ? (
                    <tr>
                      <td colSpan={4} className="px-4 py-6 text-center text-sm text-muted">
                        Loading rates...
                      </td>
                    </tr>
                  ) : rows.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-4 py-6 text-center text-sm text-muted">
                        No rates found.
                      </td>
                    </tr>
                  ) : (
                    rows.map((row, index) => (
                      <tr key={row.id ?? index} className="border-t border-borderLight">
                        <td className="px-4 py-3">
                          <input
                            value={row.hsn}
                            onChange={(event) => updateCell(index, "hsn", event.target.value)}
                            className="w-full rounded-lg border border-borderLight bg-white px-3 py-2 text-sm text-navy outline-none ring-primary/30 focus:ring-2"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="number"
                            step="0.01"
                            value={row.rate}
                            onChange={(event) => updateCell(index, "rate", event.target.value)}
                            className="w-full rounded-lg border border-borderLight bg-white px-3 py-2 text-sm text-navy outline-none ring-primary/30 focus:ring-2"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="date"
                            value={row.effective_from}
                            onChange={(event) =>
                              updateCell(index, "effective_from", event.target.value)
                            }
                            className="w-full rounded-lg border border-borderLight bg-white px-3 py-2 text-sm text-navy outline-none ring-primary/30 focus:ring-2"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="date"
                            value={row.effective_to}
                            onChange={(event) =>
                              updateCell(index, "effective_to", event.target.value)
                            }
                            className="w-full rounded-lg border border-borderLight bg-white px-3 py-2 text-sm text-navy outline-none ring-primary/30 focus:ring-2"
                          />
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>
    </>
  );
};

export default AdminRatesPage;
