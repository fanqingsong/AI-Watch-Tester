import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { JetBrains_Mono } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import "./globals.css";
import { AuthProvider } from "@/components/AuthProvider";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import ServerWarmup from "@/components/ServerWarmup";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
});

export const metadata: Metadata = {
  title: {
    default: "AWT — AI-Powered E2E Testing That Heals Itself",
    template: "%s | AWT",
  },
  description:
    "Test Smarter, Fix Faster. AWT scans your site, generates test scenarios with AI, executes them with Playwright, and auto-fixes failures. The DevQA loop that never sleeps.",
  keywords: [
    "AI testing",
    "E2E testing",
    "automated testing",
    "web testing",
    "Playwright",
    "DevQA",
    "test automation",
    "AI QA",
    "self-healing tests",
    "DevQA loop",
  ],
  metadataBase: new URL("https://ai-watch-tester.vercel.app"),
  openGraph: {
    type: "website",
    siteName: "AWT",
    title: "AWT — AI-Powered E2E Testing That Heals Itself",
    description:
      "Test Smarter, Fix Faster. AWT scans your site, generates test scenarios, and auto-fixes failures.",
    images: [{ url: "/og-image.png", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "AWT — AI-Powered E2E Testing That Heals Itself",
    description:
      "Test Smarter, Fix Faster. AWT scans your site, generates test scenarios, and auto-fixes failures.",
    images: ["/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale}>
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${jetbrainsMono.variable} font-sans antialiased`}
      >
        <NextIntlClientProvider messages={messages}>
          <AuthProvider>
            <ServerWarmup />
            <Header />
            <main>{children}</main>
            <Footer />
          </AuthProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
