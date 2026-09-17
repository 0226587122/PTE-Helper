import type { ChartData } from "../../api/types";
import styles from "../Tasks.module.css";

const COLOURS = ["#1d4ed8", "#0d9488", "#db2777", "#f59e0b", "#7c3aed", "#16a34a", "#dc2626", "#0891b2"];
const W = 640;
const H = 380;
const PAD = { top: 50, right: 24, bottom: 70, left: 64 };

function niceMax(value: number): number {
  const magnitude = 10 ** Math.floor(Math.log10(Math.max(value, 1)));
  return Math.ceil(value / magnitude) * magnitude;
}

function formatValue(value: number, unit: string) {
  return `${value.toLocaleString()}${unit}`;
}

/** Draws the Describe Image chart as SVG from the generated data. */
export function Chart({ data }: { data: ChartData }) {
  const { kind, title, unit, categories, values } = data;
  return (
    <svg className={styles.chart} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title}>
      <rect width={W} height={H} fill="white" />
      <text x={W / 2} y={28} textAnchor="middle" fontSize={18} fontWeight={700} fill="#0f172a">
        {title}
      </text>
      {kind === "pie" ? <Pie categories={categories} values={values} unit={unit} /> : <Axes data={data} />}
    </svg>
  );
}

function Axes({ data }: { data: ChartData }) {
  const { kind, unit, categories, values, x_label, y_label } = data;
  const top = niceMax(Math.max(...values) * 1.1);
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;
  const y = (v: number) => PAD.top + plotH - (v / top) * plotH;
  const step = plotW / categories.length;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round(top * f));
  const points = values.map((v, i) => `${PAD.left + step * i + step / 2},${y(v)}`).join(" ");

  return (
    <g>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} stroke="#e2e8f0" />
          <text x={PAD.left - 8} y={y(t) + 4} textAnchor="end" fontSize={12} fill="#475569">
            {t.toLocaleString()}
          </text>
        </g>
      ))}
      {kind === "bar"
        ? values.map((v, i) => (
            <g key={categories[i]}>
              <rect
                x={PAD.left + step * i + step * 0.18}
                y={y(v)}
                width={step * 0.64}
                height={PAD.top + plotH - y(v)}
                fill={COLOURS[i % COLOURS.length]}
                rx={4}
              />
              <text x={PAD.left + step * i + step / 2} y={y(v) - 6} textAnchor="middle" fontSize={12} fill="#0f172a">
                {formatValue(v, unit)}
              </text>
            </g>
          ))
        : (
          <g>
            <polyline points={points} fill="none" stroke="#1d4ed8" strokeWidth={3} />
            {values.map((v, i) => (
              <g key={categories[i]}>
                <circle cx={PAD.left + step * i + step / 2} cy={y(v)} r={5} fill="#1d4ed8" />
                <text x={PAD.left + step * i + step / 2} y={y(v) - 10} textAnchor="middle" fontSize={12} fill="#0f172a">
                  {formatValue(v, unit)}
                </text>
              </g>
            ))}
          </g>
        )}
      {categories.map((c, i) => (
        <text key={c} x={PAD.left + step * i + step / 2} y={PAD.top + plotH + 20} textAnchor="middle" fontSize={12} fill="#334155">
          {c}
        </text>
      ))}
      <line x1={PAD.left} x2={W - PAD.right} y1={PAD.top + plotH} y2={PAD.top + plotH} stroke="#94a3b8" />
      {x_label && (
        <text x={PAD.left + plotW / 2} y={H - 18} textAnchor="middle" fontSize={13} fill="#475569">
          {x_label}
        </text>
      )}
      {y_label && (
        <text transform={`translate(18 ${PAD.top + plotH / 2}) rotate(-90)`} textAnchor="middle" fontSize={13} fill="#475569">
          {y_label}
        </text>
      )}
    </g>
  );
}

function Pie({ categories, values, unit }: { categories: string[]; values: number[]; unit: string }) {
  const total = values.reduce((a, b) => a + b, 0) || 1;
  const cx = 220;
  const cy = 210;
  const r = 140;
  let angle = -Math.PI / 2;
  return (
    <g>
      {values.map((v, i) => {
        const start = angle;
        const sweep = (v / total) * Math.PI * 2;
        angle += sweep;
        const x1 = cx + r * Math.cos(start);
        const y1 = cy + r * Math.sin(start);
        const x2 = cx + r * Math.cos(start + sweep);
        const y2 = cy + r * Math.sin(start + sweep);
        const large = sweep > Math.PI ? 1 : 0;
        const mid = start + sweep / 2;
        return (
          <g key={categories[i]}>
            <path d={`M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${large} 1 ${x2},${y2} Z`} fill={COLOURS[i % COLOURS.length]} stroke="white" strokeWidth={2} />
            {v >= 6 && (
              <text x={cx + r * 0.65 * Math.cos(mid)} y={cy + r * 0.65 * Math.sin(mid) + 4} textAnchor="middle" fontSize={13} fontWeight={700} fill="white">
                {formatValue(v, unit)}
              </text>
            )}
          </g>
        );
      })}
      {categories.map((c, i) => (
        <g key={c} transform={`translate(400 ${110 + i * 30})`}>
          <rect width={16} height={16} rx={3} fill={COLOURS[i % COLOURS.length]} />
          <text x={24} y={13} fontSize={14} fill="#0f172a">
            {c} ({formatValue(values[i], unit)})
          </text>
        </g>
      ))}
    </g>
  );
}
