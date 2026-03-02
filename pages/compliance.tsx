import type { NextPage } from "next";

const CompliancePage: NextPage = () => {
  return (
    <div className="min-h-screen bg-bg p-6 md:p-8">
      <div className="rounded-2xl border border-borderLight bg-card p-6 shadow-sm transition-all duration-200 ease-in-out hover:-translate-y-0.5 hover:shadow-md">
        <h1 className="text-2xl font-semibold text-navy">Compliance</h1>
        <p className="mt-2 text-sm text-muted">
          Compliance view is ready. GST/TDS widgets can be expanded next.
        </p>
      </div>
    </div>
  );
};

export default CompliancePage;
