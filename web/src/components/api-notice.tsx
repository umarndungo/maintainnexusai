import type { ApiResult } from "@/lib/api";

export function ApiNotice({ result, label }: { result: ApiResult<unknown>; label: string }) {
  if (result.available) return null;
  const explanation = result.error ?? (result.status === 404
    ? "This resource is not supplied by the current backend."
    : result.status === 403 ? "Your current backend permissions do not allow access to this resource."
    : result.status ? `The backend returned HTTP ${result.status}.` : "The API could not be reached.");
  return <p className="notice" role="status"><strong>{label}.</strong> {explanation}</p>;
}
