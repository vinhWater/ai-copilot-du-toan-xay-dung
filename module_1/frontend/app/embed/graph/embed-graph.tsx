"use client";

import { useSearchParams } from "next/navigation";
import GraphView from "@/components/GraphView";

export default function EmbedGraph() {
  const p = useSearchParams();
  const soHieu = p.get("so_hieu");
  if (!soHieu) return <p className="graph-error">Thiếu tham số so_hieu</p>;
  return <GraphView soHieu={soHieu} asOfDate={p.get("as_of_date") ?? undefined} depth={Number(p.get("depth") ?? 1)} />;
}
