import type { Metadata } from "next";
import "leaflet/dist/leaflet.css";
import "maplibre-gl/dist/maplibre-gl.css";
import "../globals.css";

export const metadata: Metadata = {
  title: "OutWeather — smarter field and crop rotation insights",
  description:
    "OutWeather simulates crop rotations against historical droughts and future climate scenarios using NASA and USDA data.",
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
