import React from "react";
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { formatTime, fmtMs } from "../lib/utils-sp";
import { lossColor, LOSS_COLORS } from "../mock";

function SmokeTooltip({ active, payload, rangeKey }) {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0].payload;
  return (
    <div className="glass rounded-lg px-3 py-2 text-xs shadow-xl">
      <div className="mb-1 font-semibold text-foreground">
        {new Date(d.time).toLocaleString([], {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })}
      </div>
      <div className="mono space-y-0.5">
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Median</span>
          <span className="text-cyan-300">{fmtMs(d.median)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Min / Max</span>
          <span className="text-foreground/80">
            {fmtMs(d.min)} / {fmtMs(d.max)}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Loss</span>
          <span style={{ color: lossColor(d.loss) }}>{d.loss}%</span>
        </div>
      </div>
    </div>
  );
}

const LossDot = (props) => {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null || payload.loss <= 0) return null;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={3}
      fill={lossColor(payload.loss)}
      stroke="#0a0a0f"
      strokeWidth={1}
    />
  );
};

export default function SmokeGraph({ data, rangeKey, height = 320 }) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={data}
          margin={{ top: 10, right: 12, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="smokeFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#a855f7" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#22d3ee" stopOpacity={0.12} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="hsl(240 14% 20%)"
            vertical={false}
          />
          <XAxis
            dataKey="time"
            tickFormatter={(t) => formatTime(t, rangeKey)}
            stroke="hsl(220 12% 45%)"
            tick={{ fontSize: 11 }}
            minTickGap={40}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            stroke="hsl(220 12% 45%)"
            tick={{ fontSize: 11 }}
            tickFormatter={(v) => `${v}`}
            axisLine={false}
            tickLine={false}
            width={44}
            label={{
              value: "ms",
              angle: 0,
              position: "top",
              offset: 8,
              fill: "hsl(220 12% 45%)",
              fontSize: 10,
            }}
          />
          <Tooltip
            content={<SmokeTooltip rangeKey={rangeKey} />}
            cursor={{ stroke: "hsl(187 92% 54%)", strokeWidth: 1, strokeDasharray: "4 4" }}
          />
          {/* invisible base for stacking the smoke band */}
          <Area
            type="monotone"
            dataKey="min"
            stackId="smoke"
            stroke="none"
            fill="transparent"
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="band"
            stackId="smoke"
            stroke="none"
            fill="url(#smokeFill)"
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="median"
            stroke="#22d3ee"
            strokeWidth={1.75}
            dot={<LossDot />}
            activeDot={{ r: 4, fill: "#22d3ee", stroke: "#0a0a0f" }}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export function LossLegend() {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[10px] text-muted-foreground">
      <span className="font-medium uppercase tracking-wider">Packet loss</span>
      {LOSS_COLORS.map((b) => (
        <div key={b.label} className="flex items-center gap-1">
          <span
            className="h-2.5 w-2.5 rounded-sm"
            style={{ background: b.color }}
          />
          <span className="mono">{b.label}</span>
        </div>
      ))}
    </div>
  );
}
