"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";
import GraphView from "@/components/GraphView";
import { TINH_TRANG, VanBan } from "@/lib/api";

export default function Explorer() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const soHieu = params.get("so_hieu") ?? "";
  const asOf = params.get("as_of_date") ?? "";
  const depth = Number(params.get("depth") ?? 1);
  const [draft, setDraft] = useState(soHieu);
  const [selected, setSelected] = useState<VanBan | null>(null);

  const go = (next: Record<string, string>) => {
    const q = new URLSearchParams(params);
    for (const [k, v] of Object.entries(next)) (v ? q.set(k, v) : q.delete(k));
    router.replace(`${pathname}?${q}`);
  };
  const submit = (e: FormEvent) => {
    e.preventDefault();
    setSelected(null);
    go({ so_hieu: draft.trim() });
  };

  return (
    <>
      <form className="toolbar" onSubmit={submit}>
        <label>
          Số hiệu
          <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="206/2026/NĐ-CP" required />
        </label>
        <label>
          Tại ngày
          <input type="date" value={asOf} onChange={(e) => go({ as_of_date: e.target.value })} />
        </label>
        <label>
          Độ sâu
          <select value={depth} onChange={(e) => go({ depth: e.target.value })}>
            {[1, 2, 3].map((d) => (
              <option key={d}>{d}</option>
            ))}
          </select>
        </label>
        <button className="primary">Xem</button>
      </form>

      {soHieu ? (
        <div className="layout">
          <GraphView soHieu={soHieu} asOfDate={asOf || undefined} depth={depth} onSelect={setSelected} />
          <aside className="panel">
            {selected ? (
              <>
                <h2 style={{ fontSize: "1rem", marginTop: 0 }}>{selected.so_hieu}</h2>
                <dl>
                  <dt>Loại</dt>
                  <dd>{selected.loai || "—"}</dd>
                  <dt>Cơ quan</dt>
                  <dd>{selected.co_quan_ban_hanh || "—"}</dd>
                  <dt>Ban hành</dt>
                  <dd>{selected.ngay_ban_hanh ?? "—"}</dd>
                  <dt>Hiệu lực</dt>
                  <dd>{selected.ngay_hieu_luc ?? "—"}</dd>
                  <dt>Tình trạng</dt>
                  <dd>{TINH_TRANG[selected.tinh_trang ?? "khong_ro"].label}</dd>
                </dl>
                {selected.so_hieu !== soHieu && (
                  <p>
                    <button
                      onClick={() => {
                        setDraft(selected.so_hieu);
                        setSelected(null);
                        go({ so_hieu: selected.so_hieu });
                      }}
                    >
                      Xem lược đồ văn bản này
                    </button>
                  </p>
                )}
              </>
            ) : (
              <p className="sub">Bấm vào một văn bản để xem thông tin.</p>
            )}
          </aside>
        </div>
      ) : (
        <p className="sub">Nhập số hiệu văn bản để xem lược đồ.</p>
      )}
    </>
  );
}
