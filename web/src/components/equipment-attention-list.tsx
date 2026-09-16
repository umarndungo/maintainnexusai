"use client";
import { useMemo, useState } from "react";
import Link from "./navigation-link";
import { TablePagination } from "./table-pagination";
import { EquipmentState } from "./equipment-monitor";
import type { EquipmentReading } from "@/lib/api";

const ATTENTION_STATES = ["FAILURE_DETECTED", "APPROACHING_THRESHOLD"];
const PAGE_SIZE = 5;

export function EquipmentAttentionList({
  equipment,
  available,
}: {
  equipment: EquipmentReading[];
  available: boolean;
}) {
  const [query, setQuery] = useState("");
  const [state, setState] = useState("");
  const [page, setPage] = useState(1);

  const attention = useMemo(
    () => equipment.filter((row) => ATTENTION_STATES.includes(row.state)),
    [equipment],
  );
  const rows = attention.filter(
    (row) =>
      (!state || row.state === state) &&
      `${row.equipment_id} ${row.station_id ?? ""} ${row.telemetry.asset_type ?? ""}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  const current = Math.min(
    page,
    Math.max(1, Math.ceil(rows.length / PAGE_SIZE)),
  );

  return (
    <>
      {attention.length > 0 && (
        <div className="filter-bar">
          <label>
            Search
            <input
              type="search"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setPage(1);
              }}
              placeholder="Equipment, station or type"
            />
          </label>
          <label>
            State
            <select
              value={state}
              onChange={(event) => {
                setState(event.target.value);
                setPage(1);
              }}
            >
              <option value="">All states</option>
              <option value="FAILURE_DETECTED">Failure risk detected</option>
              <option value="APPROACHING_THRESHOLD">
                Approaching threshold
              </option>
            </select>
          </label>
        </div>
      )}
      {rows.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE).map((row) => (
        <div className="fleet-row" key={row.equipment_id}>
          <Link href={`/equipment/${encodeURIComponent(row.equipment_id)}`}>
            {row.equipment_id}
          </Link>
          <EquipmentState state={row.state} />
        </div>
      ))}
      {available && attention.length === 0 && (
        <div className="empty-state">
          No evaluated equipment currently requires attention. Unscored
          equipment is listed separately.
        </div>
      )}
      {available && attention.length > 0 && rows.length === 0 && (
        <div className="empty-state">No equipment matches these filters.</div>
      )}
      {rows.length > 0 && (
        <TablePagination
          page={current}
          total={rows.length}
          pageSize={PAGE_SIZE}
          onChange={setPage}
        />
      )}
    </>
  );
}
