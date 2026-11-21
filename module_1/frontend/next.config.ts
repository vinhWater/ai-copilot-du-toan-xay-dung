import type { NextConfig } from "next";

// Trình duyệt gọi /api/* cùng origin, Next proxy sang Legal Knowledge API → không cần CORS.
// Đọc lúc build: Docker truyền qua build arg LEGAL_API_URL.
const API = process.env.LEGAL_API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  output: "standalone",
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/:path*` }];
  },
};

export default nextConfig;
