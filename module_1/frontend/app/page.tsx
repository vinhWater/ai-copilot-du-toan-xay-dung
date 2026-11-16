import { Suspense } from "react";
import Explorer from "./explorer";

export default function Page() {
  return (
    <main>
      <h1>Lược đồ văn bản</h1>
      <p className="sub">Quan hệ đã duyệt giữa các văn bản; màu node = tình trạng hiệu lực tại ngày chọn.</p>
      <Suspense fallback={<p className="sub">Đang tải…</p>}>
        <Explorer />
      </Suspense>
    </main>
  );
}
