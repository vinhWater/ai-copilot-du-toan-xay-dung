"use client";

import cytoscape from "cytoscape";
import { useEffect, useRef, useState } from "react";
import { api, dieuKhoan, GraphOut, LOAI_LABEL, TINH_TRANG, VanBan } from "@/lib/api";

export interface GraphViewProps {
  soHieu: string;
  asOfDate?: string; // YYYY-MM-DD, bỏ trống = hôm nay (giờ VN, phía API)
  depth?: number;
  apiBase?: string; // mặc định "/api" (proxy cùng origin)
  onSelect?: (vb: VanBan) => void;
}

/** Lược đồ văn bản: node tô màu theo tình trạng hiệu lực tại asOfDate, cạnh = quan hệ đã duyệt. */
export default function GraphView({ soHieu, asOfDate, depth = 1, apiBase, onSelect }: GraphViewProps) {
  const box = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<GraphOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    if (!soHieu) return;
    const q = new URLSearchParams({ depth: String(depth) });
    if (asOfDate) q.set("as_of_date", asOfDate);
    let live = true;
    setError(null);
    api<GraphOut>(`/graph/${soHieu}?${q}`, undefined, apiBase)
      .then((g) => live && setData(g))
      .catch((e: Error) => live && (setData(null), setError(e.message)));
    return () => {
      live = false;
    };
  }, [soHieu, asOfDate, depth, apiBase]);

  useEffect(() => {
    if (!data || !box.current) return;
    // Gộp các cạnh cùng (nguồn, đích, loại) — VD hướng dẫn Điều 74 và khoản 7 Điều 76 → 1 cạnh
    const edges = new Map<string, { source: string; target: string; label: string; refs: string[] }>();
    for (const e of data.edges) {
      const key = `${e.nguon}|${e.dich}|${e.loai}`;
      const cur = edges.get(key) ?? { source: e.nguon, target: e.dich, label: LOAI_LABEL[e.loai], refs: [] };
      const ref = dieuKhoan(e);
      if (ref) cur.refs.push(ref);
      edges.set(key, cur);
    }
    const cy = cytoscape({
      container: box.current,
      elements: [
        ...data.nodes.map((n) => ({
          data: {
            id: n.so_hieu,
            label: n.loai ? `${n.so_hieu}\n${n.loai}` : n.so_hieu,
            color: TINH_TRANG[n.tinh_trang ?? "khong_ro"].color,
            ngoai: n.ngay_hieu_luc === null ? 1 : 0,
            root: n.so_hieu === data.root ? 1 : 0,
          },
        })),
        ...[...edges.entries()].map(([id, e]) => ({
          data: { id, source: e.source, target: e.target, label: e.refs.length ? `${e.label} (${e.refs.join("; ")})` : e.label },
        })),
      ],
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(color)",
            label: "data(label)",
            "text-wrap": "wrap",
            "text-valign": "bottom",
            "text-margin-y": 6,
            "font-size": 11,
            color: "#374151",
            "text-background-color": "#ffffff",
            "text-background-opacity": 0.85,
            "text-background-padding": "2px",
            width: 26,
            height: 26,
            "border-width": 2,
            "border-color": "#ffffff",
          },
        },
        { selector: "node[ngoai = 1]", style: { "border-style": "dashed", "border-color": "#6b7280", "background-opacity": 0.5 } },
        { selector: "node[root = 1]", style: { width: 38, height: 38, "border-width": 4, "border-color": "#111827" } },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#9ca3af",
            "target-arrow-color": "#9ca3af",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": 9,
            color: "#4b5563",
            "text-rotation": "autorotate",
            "text-background-color": "#ffffff",
            "text-background-opacity": 0.85,
          },
        },
      ],
      layout: { name: "breadthfirst", roots: [data.root], spacingFactor: 1.3, padding: 30, animate: false },
      wheelSensitivity: 0.3,
    });
    cy.on("tap", "node", (ev) => {
      const vb = data.nodes.find((n) => n.so_hieu === ev.target.id());
      if (vb) onSelectRef.current?.(vb);
    });
    return () => cy.destroy();
  }, [data]);

  return (
    <div className="graph">
      {error && <p className="graph-error">{error}</p>}
      <div ref={box} className="graph-canvas" aria-label={`Lược đồ văn bản ${soHieu}`} role="img" />
      <ul className="graph-legend">
        {Object.entries(TINH_TRANG).map(([k, v]) => (
          <li key={k}>
            <span className="dot" style={{ background: v.color }} /> {v.label}
          </li>
        ))}
      </ul>
      {data?.nodes.some((n) => n.minh_hoa) && (
        <p className="graph-note">⚠️ Có văn bản dữ liệu minh họa / chưa xác minh nguồn chính thống.</p>
      )}
    </div>
  );
}
