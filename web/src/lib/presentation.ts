/** Deterministic UTC display on both server and browser to avoid hydration drift. */
export function formatTimestamp(value: string | number | undefined | null) {
  if (value == null) return "Not supplied";
  const date = new Date(value);
  return Number.isFinite(date.getTime()) ? `${date.toISOString().slice(0,16).replace("T"," ")} UTC` : "Invalid timestamp";
}
