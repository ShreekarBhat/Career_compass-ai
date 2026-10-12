import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Career Compass AI",
  description: "Agentic career intelligence and personalised job navigation",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
