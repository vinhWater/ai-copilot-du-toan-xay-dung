import { Suspense } from "react";
import EmbedGraph from "./embed-graph";

/** Trang nhúng cho Module 2: <iframe src="http://localhost:3000/embed/graph?so_hieu=…&as_of_date=…&depth=1"> */
export default function Page() {
  return (
    <div className="embed">
      <Suspense fallback={null}>
        <EmbedGraph />
      </Suspense>
    </div>
  );
}
