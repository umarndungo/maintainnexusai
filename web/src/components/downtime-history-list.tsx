"use client";
import { useState } from "react";
import Link from "./navigation-link";
import { TablePagination } from "./table-pagination";
import type { DowntimeWindow } from "@/lib/api";

const PAGE_SIZE = 8;

export function DowntimeHistoryList({ windows }: { windows: DowntimeWindow[] }) {
  const [page, setPage] = useState(1);
  const current = Math.min(page, Math.max(1, Math.ceil(windows.length / PAGE_SIZE)));

  return (
    <>
      <div className="window-list">
        {windows.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE).map((window) => (
          <article key={window.id}>
            <strong>
              {window.work_order_id ? (
                <Link href={`/work-orders/${encodeURIComponent(window.work_order_id)}`}>
                  {window.work_order_id}
                </Link>
              ) : (
                "Unlinked event"
              )}
            </strong>
            <span>
              {new Date(window.started_at).toLocaleString()}
              {" "}?{" "}
              {window.ended_at ? new Date(window.ended_at).toLocaleString() : "Still open"}
            </span>
            <b>
              {window.duration_seconds == null
                ? "Duration unavailable"
                : `${Math.round(window.duration_seconds / 60)} min`}
            </b>
          </article>
        ))}
      </div>
      {windows.length > PAGE_SIZE && (
        <TablePagination
          page={current}
          total={windows.length}
          pageSize={PAGE_SIZE}
          onChange={setPage}
        />
      )}
    </>
  );
}
