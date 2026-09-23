import { notFound } from "next/navigation";

import { RunView } from "@/components/RunView";
import { fetchRun } from "@/lib/api";

export const dynamic = "force-dynamic";

// Next 16: route params arrive as a promise.
export default async function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const run = await fetchRun(id);
  if (!run) notFound();

  return <RunView saved={run} />;
}
