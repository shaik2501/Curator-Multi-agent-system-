import RunClient from "@/components/run/run-client";

export default function RunPage({ params }: { params: { id: string } }) {
  return <RunClient runId={params.id} />;
}
