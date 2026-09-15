import { OrderWorkspace } from "@/components/order-workspace";
export default async function WorkOrdersPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const { status = "" } = await searchParams;
  return <OrderWorkspace status={status} />;
}
