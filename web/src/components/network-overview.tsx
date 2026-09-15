import Link from "./navigation-link";
import type { EquipmentReading } from "@/lib/api";

export function NetworkOverview({ equipment }: { equipment: EquipmentReading[] }) {
  const stations = new Map<string, EquipmentReading[]>();
  for (const row of equipment) {
    const station = row.station_id ?? "Station not supplied";
    stations.set(station, [...(stations.get(station) ?? []), row]);
  }
  const states = [...new Set(equipment.map(row => row.state))].sort();
  return <section className="executive-panel"><div className="panel-header"><div><span className="eyebrow">CURRENT EQUIPMENT PICTURE</span><h2>Network equipment state</h2></div><Link href="/monitoring">Explore monitoring</Link></div>
    <p className="monitoring-context">Latest recorded evaluations across accessible assets. Unscored assets have unknown health. This is a current snapshot, not measured uptime.</p>
    {equipment.some(row => row.telemetry.provenance === "SYNTHETIC_LIVE_SIMULATION") && <p className="chart-source">Includes persisted simulation readings</p>}
    {!equipment.length ? <p className="empty-state">No equipment records supplied.</p> : <><div className="network-state-grid">{states.map(state => <article key={state}><span>{state.replaceAll("_", " ")}</span><strong>{equipment.filter(row => row.state === state).length}</strong><small>recorded assets</small></article>)}</div><div className="network-table"><table><caption>Equipment evaluations by station</caption><thead><tr><th>Station</th><th>Assets</th><th>Needs attention</th><th>Unscored</th></tr></thead><tbody>{[...stations].sort(([a], [b]) => a.localeCompare(b)).map(([station, rows]) => <tr key={station}><th scope="row">{station}</th><td>{rows.length}</td><td>{rows.filter(row => ["APPROACHING_THRESHOLD", "FAILURE_DETECTED"].includes(row.state)).length}</td><td>{rows.filter(row => row.state === "UNSCORED").length}</td></tr>)}</tbody></table></div></>}
  </section>;
}
