import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import "./globals.css";

const jakarta = Plus_Jakarta_Sans({
  variable: "--font-jakarta",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Clearpath · Human-in-the-loop lending",
  description: "An AI analyst does the underwriting legwork; a loan officer decides where judgment is needed.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // Extensions such as Dark Reader add attributes to <html> before hydration; ignore those.
    <html lang="en" className={`${jakarta.variable} h-full antialiased`} suppressHydrationWarning>
      <head>
        {/* The pastel palette is designed light-only; ask Dark Reader not to recolor it. */}
        <meta name="darkreader-lock" />
      </head>
      <body className="flex min-h-full flex-col bg-canvas font-sans">
        <SiteHeader />
        <main className="flex-1">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
