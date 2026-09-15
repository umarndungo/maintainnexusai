import { OrderWorkspace } from "@/components/order-workspace";
export default async function ApprovalsPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const { status = "" } = await searchParams;
  return <OrderWorkspace approvals status={status} />;
}
