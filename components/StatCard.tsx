type StatCardProps = {
  title: string;
  value: string;
  subtext?: string;
  color?: string;
};

export default function StatCard({ title, value, subtext, color }: StatCardProps) {
  return (
    <div className="overflow-hidden rounded-2xl bg-white shadow-sm transition-all duration-200 ease-in-out hover:-translate-y-0.5 hover:shadow-md">
      <div
        className="h-1.5 w-full"
        style={{ backgroundColor: color || "#0B63FF" }}
        aria-hidden="true"
      />
      <div className="space-y-2 p-6">
        <p className="text-sm font-medium text-muted">{title}</p>
        <p className="text-3xl font-bold leading-none text-navy">{value}</p>
        {subtext ? <p className="text-sm text-muted">{subtext}</p> : null}
      </div>
    </div>
  );
}
