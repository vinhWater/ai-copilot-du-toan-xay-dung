import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lược đồ văn bản — Module 1",
  description: "Legal Knowledge Base: lược đồ quan hệ văn bản pháp luật theo thời điểm",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
