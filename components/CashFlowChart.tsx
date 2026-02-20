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

type CashFlowPoint = {
  month: string;
  inflow: number;
  outflow: number;
};

type CashFlowChartProps = {
  data: CashFlowPoint[];
};

export default function CashFlowChart({ data }: CashFlowChartProps) {
  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis dataKey="month" tick={{ fill: "#6B7280", fontSize: 12 }} />
          <YAxis tick={{ fill: "#6B7280", fontSize: 12 }} />
          <Tooltip />
          <Legend />
          <Line
            type="natural"
            dataKey="inflow"
            name="Inflow"
            stroke="#00B37E"
            strokeWidth={3}
            isAnimationActive
            animationDuration={850}
            animationEasing="ease-in-out"
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
          <Line
            type="natural"
            dataKey="outflow"
            name="Outflow"
            stroke="#E02424"
            strokeWidth={3}
            isAnimationActive
            animationDuration={850}
            animationEasing="ease-in-out"
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
