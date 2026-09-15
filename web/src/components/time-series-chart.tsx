"use client";

import { useId, useState } from "react";
import { formatTimestamp } from "@/lib/presentation";

export type ChartPoint = { time: number; value: number | null; source?: string };
const number = (value: number) => value.toLocaleString("en", { maximumFractionDigits: 2 });

export function TimeSeriesChart({ title, unit, points, threshold, percent = false }: {
  title: string; unit: string; points: ChartPoint[]; threshold?: number; percent?: boolean;
}) {
  const id = useId();
  const [selected, setSelected] = useState<number | null>(null);
  const ordered = points.filter(p => Number.isFinite(p.time)).toSorted((a, b) => a.time - b.time);
  const valid = ordered.filter((p): p is ChartPoint & { value: number } => p.value !== null && Number.isFinite(p.value));
  if (!valid.length) return <p className="empty-state">No recorded {title.toLowerCase()} values available.</p>;
  const low = Math.min(...valid.map(p => p.value), threshold ?? Infinity, ...(percent ? [0] : []));
  const high = Math.max(...valid.map(p => p.value), threshold ?? -Infinity, ...(percent ? [100] : []));
  const padding = percent ? 0 : Math.max((high - low) * .12, Math.abs(high) * .02, .1);
  const min = low - padding, max = high + padding;
  const first = ordered[0].time, last = ordered.at(-1)!.time;
  const x = (time: number) => first === last ? 338 : 66 + (time - first) / (last - first) * 544;
  const y = (value: number) => 200 - (value - min) / (max - min || 1) * 168;
  const segments: Array<Array<ChartPoint & { value: number }>> = [];
  let segment: Array<ChartPoint & { value: number }> = [];
  for (const point of ordered) {
    if (point.value === null || !Number.isFinite(point.value)) { if (segment.length) segments.push(segment); segment = []; }
    else segment.push({ ...point, value: point.value });
  }
  if (segment.length) segments.push(segment);
  const active = valid.find(p => p.time === selected) ?? valid.at(-1)!;
  const sources = new Set(valid.map(p => p.source));
  const synthetic = valid.some(p => p.source === "SYNTHETIC_LIVE_SIMULATION");
  return <figure className="time-series">
    <div className="chart-summary"><div><span className="chart-label">{selected === null ? "Latest recorded" : "Selected reading"}</span><strong>{number(active.value)} <small>{unit}</small></strong></div><span className="chart-source">{synthetic ? sources.size === 1 ? "Simulation · persisted readings" : "Mixed sources · includes simulation" : "Backend records"}</span></div>
    <svg viewBox="0 0 640 238" role="group" aria-label={`${title}, ${valid.length} recorded values. Use Tab to inspect points.`}>
      <defs><linearGradient id={id} x1="0" y1="0" x2="0" y2="1"><stop stopColor="currentColor" stopOpacity=".22" /><stop offset="1" stopColor="currentColor" stopOpacity=".015" /></linearGradient></defs>
      {[0, 1, 2, 3, 4].map(tick => { const value = min + (max - min) * tick / 4; return <g key={tick}><line className="series-grid" x1="66" x2="610" y1={y(value)} y2={y(value)} /><text className="series-axis" x="56" y={y(value) + 4} textAnchor="end">{number(value)}{percent ? "%" : ""}</text></g>; })}
      {threshold !== undefined && <line className="series-threshold" x1="66" x2="610" y1={y(threshold)} y2={y(threshold)} />}
      {segments.map((group, index) => { const line = group.map(p => `${x(p.time)},${y(p.value)}`).join(" "); return <g key={index}>{group.length > 1 && <><polygon points={`${x(group[0].time)},200 ${line} ${x(group.at(-1)!.time)},200`} fill={`url(#${id})`} /><polyline points={line} className="series-line" /></>}</g>; })}
      <line className="series-cursor" x1={x(active.time)} x2={x(active.time)} y1="32" y2="200" />
      {valid.map((point, index) => <circle key={`${point.time}-${index}`} cx={x(point.time)} cy={y(point.value)} r={point === active ? 5 : 3} className="series-point" tabIndex={0} role="button" aria-label={`${formatTimestamp(point.time)}: ${number(point.value)} ${unit}`} onFocus={() => setSelected(point.time)} onPointerEnter={() => setSelected(point.time)} onClick={() => setSelected(point.time)} onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelected(point.time); } }}><title>{`${formatTimestamp(point.time)}: ${number(point.value)} ${unit}`}</title></circle>)}
      <text className="series-axis" x="66" y="226">{new Date(first).toISOString().slice(11, 16)} UTC</text><text className="series-axis" x="610" y="226" textAnchor="end">{new Date(last).toISOString().slice(11, 16)} UTC</text>
    </svg>
    <figcaption className="chart-inspection"><span>{formatTimestamp(active.time)} · {valid.length} recorded values</span>{selected !== null && <button type="button" onClick={() => setSelected(null)}>Latest reading</button>}</figcaption>
    {threshold !== undefined && <p className="threshold-legend">Dashed line: server failure threshold {number(threshold)}{unit}</p>}
    {valid.length === 1 && <p className="monitoring-context">One reading recorded. More readings are needed for a trend.</p>}
    <details className="chart-data"><summary>View recorded values</summary><div><table><thead><tr><th>Timestamp (UTC)</th><th>{title} ({unit})</th><th>Source</th></tr></thead><tbody>{valid.map((p, index) => <tr key={index}><td>{formatTimestamp(p.time)}</td><td>{number(p.value)}</td><td>{p.source ?? "Not supplied"}</td></tr>)}</tbody></table></div></details>
  </figure>;
}
