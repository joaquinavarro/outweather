import type { Metadata } from "next";
import "./landing.css";

export const metadata: Metadata = {
  title: "OUTWEATHER · Test before you sow",
  description:
    "Outweather: test a crop rotation against past droughts and 2050 climate scenarios before you sow.",
};

export default function LandingLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
        <link rel="stylesheet" href="https://unpkg.com/lenis@1.1.18/dist/lenis.css" />
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/0.160.0/three.min.js" defer></script>
        <script src="https://unpkg.com/lenis@1.1.18/dist/lenis.min.js" defer></script>
        <script src="/landing.js" defer></script>
      </head>
      <body>{children}</body>
    </html>
  );
}
