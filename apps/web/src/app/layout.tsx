import type { Metadata } from "next";
import "./globals.css";
import Shell from "./_workspace/shell";
export const metadata: Metadata = { title: "DATCO 업무 공간", description: "정부지원사업 운영관리" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ko"><body><Shell>{children}</Shell></body></html>;
}
