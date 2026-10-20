import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jbMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jbmono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Curator",
  description: "Multi-agent research team dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${jbMono.variable}`}>
      {/* eslint-disable-next-line @next/next/no-page-custom-font */}
      <head>
        {/* Geist (headlines/display) loaded via <link>, per the reference
            mockups — next/font/google in this Next 14 version doesn't
            export "Geist" the way it does Inter/JetBrains Mono. */}
        <link
          href="https://fonts.googleapis.com/css2?family=Geist:wght@100..900&display=swap"
          rel="stylesheet"
          precedence="default"
        />
        {/* Material Symbols Outlined (variable font) for all icons. */}
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
          rel="stylesheet"
          precedence="default"
        />
      </head>
      <body className="min-h-screen bg-background text-on-surface font-body-md text-body-md antialiased">
        {children}
      </body>
    </html>
  );
}
