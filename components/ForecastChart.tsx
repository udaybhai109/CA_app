import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type ForecastPoint = {
  month: string;
  projected_revenue?: number;
  projected_expense?: number;
  projected_cash_balance?: number;
  projectedRevenue?: number;
  projectedExpense?: number;
  projectedCashBalance?: number;
};

type ForecastChartProps = {
  data: ForecastPoint[];
};

const normalizeData = (data: ForecastPoint[]) =>
  data.map((item) => ({
    month: item.month,
    projectedRevenue: Number(item.projected_revenue ?? item.projectedRevenue ?? 0),
    projectedExpense: Number(item.projected_expense ?? item.projectedExpense ?? 0),
    projectedCashBalance: Number(item.projected_cash_balance ?? item.projectedCashBalance ?? 0),
  }));

export default function ForecastChart({ data }: ForecastChartProps) {
  const chartData = normalizeData(data);

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis dataKey="month" tick={{ fill: "#6B7280", fontSize: 12 }} />
          <YAxis tick={{ fill: "#6B7280", fontSize: 12 }} />
          <Tooltip />
          <Legend />
          <Line
            type="natural"
            dataKey="projectedRevenue"
            name="Projected Revenue"
            stroke="#00B37E"
            strokeWidth={3}
            strokeDasharray="8 6"
            isAnimationActive
            animationDuration={850}
            animationEasing="ease-in-out"
            dot={{ r: 3 }}
          />
          <Line
            type="natural"
            dataKey="projectedExpense"
            name="Projected Expense"
            stroke="#E02424"
            strokeWidth={3}
            strokeDasharray="8 6"
            isAnimationActive
            animationDuration={850}
            animationEasing="ease-in-out"
            dot={{ r: 3 }}
          />
          <Line
            type="natural"
            dataKey="projectedCashBalance"
            name="Projected Cash Balance"
            stroke="#0B63FF"
            strokeWidth={3}
            strokeDasharray="8 6"
            isAnimationActive
            animationDuration={850}
            animationEasing="ease-in-out"
            dot={{ r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
