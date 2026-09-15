import type { Metadata } from "next";
import { Lato } from "next/font/google";
import "./globals.css";
import "./design-system.css";
import { DemoControlCenter } from "@/components/demo-control-center";

const lato = Lato({
  variable: "--font-lato",
  weight: ["400", "700", "900"],
  subsets: ["latin"],
});


export const metadata: Metadata = {
  title: "MaintainNexus AI | Station overview",
  description: "Predictive maintenance operations dashboard",
  icons: { icon: "/brand/assetguard-mark.svg" },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-scroll-behavior="smooth"
      className={`${lato.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}<DemoControlCenter /></body>
    </html>
  );
}
