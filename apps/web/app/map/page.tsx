"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";

type MapPoint = {
  lat: number;
  lng: number;
  count: number;
  city: string;
  country: string;
  label: string;
  style?: string;
};

type HexBin = {
  points: MapPoint[];
  sumWeight: number;
  center: { lat: number; lng: number };
};

// Distinct colors per style (visible on dark globe). Same style always gets same color via index.
const STYLE_PALETTE = [
  "rgb(255,140,60)",   // orange (default when "All styles")
  "rgb(100,180,255)",  // blue
  "rgb(120,220,120)",  // green
  "rgb(220,120,255)",  // purple
  "rgb(255,200,80)",   // amber
  "rgb(80,220,220)",   // cyan
  "rgb(255,100,150)",  // pink
  "rgb(255,180,80)",   // gold
  "rgb(150,200,255)",  // light blue
  "rgb(180,255,180)",  // mint
  "rgb(255,140,200)",  // rose
  "rgb(200,160,255)",  // lavender
];

function getStyleColor(style: string, sortedStyles: string[]): string {
  const i = sortedStyles.indexOf(style);
  return i >= 0 ? STYLE_PALETTE[(i + 1) % STYLE_PALETTE.length] : STYLE_PALETTE[0];
}

export default function MapPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<{
    hexBinPointsData: (data: MapPoint[]) => unknown;
    controls: () => { autoRotate: (v: boolean) => void; autoRotateSpeed: (v: number) => void };
  } | null>(null);
  const pointsRef = useRef<MapPoint[]>([]);
  const selectedStyleRef = useRef<string>("");
  const stylesRef = useRef<string[]>([]);
  const autoRotateResumeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const controlsHandlersRef = useRef<{ start: () => void; end: () => void } | null>(null);
  const [styles, setStyles] = useState<string[]>([]);
  const [selectedStyle, setSelectedStyle] = useState<string>("");
  const [points, setPoints] = useState<MapPoint[]>([]);
  const [totalArtists, setTotalArtists] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    pointsRef.current = points;
  }, [points]);
  useEffect(() => {
    selectedStyleRef.current = selectedStyle;
    stylesRef.current = styles;
  }, [selectedStyle, styles]);

  const fetchMapData = useCallback(async (style: string | null) => {
    setLoading(true);
    const url = style ? `/api/map-data?style=${encodeURIComponent(style)}` : "/api/map-data";
    const res = await fetch(url);
    const data = await res.json();
    setPoints(data.points || []);
    if (data.styles) setStyles(data.styles);
    setTotalArtists(typeof data.totalArtists === "number" ? data.totalArtists : null);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchMapData(selectedStyle || null);
  }, [selectedStyle, fetchMapData]);

  useEffect(() => {
    if (!containerRef.current) return;
    let mounted = true;
    import("globe.gl")
      .then(({ default: Globe }) => {
        if (!mounted || !containerRef.current) return;
        try {
          const GlobeFn = Globe as unknown as () => (el: HTMLElement) => unknown;
      const globeRaw = GlobeFn()(containerRef.current);
      const globe = globeRaw as {
        globeImageUrl: (u: string) => unknown;
        bumpImageUrl: (u: string) => unknown;
        backgroundImageUrl: (u: string) => unknown;
        onGlobeReady: (fn: () => void) => unknown;
        hexBinPointLat: (a: string) => unknown;
        hexBinPointLng: (a: string) => unknown;
        hexBinPointWeight: (a: (d: MapPoint) => number) => unknown;
        hexBinResolution: (n: number) => unknown;
        hexAltitude: (a: (d: HexBin) => number) => unknown;
        hexTopColor: (a: (d: HexBin) => string) => unknown;
        hexSideColor: (a: (d: HexBin) => string) => unknown;
        hexLabel: (a: (d: HexBin) => string) => unknown;
        hexBinMerge: (v: boolean) => unknown;
        enablePointerInteraction: (v: boolean) => unknown;
        hexBinPointsData: (d: MapPoint[]) => unknown;
        controls: () => { autoRotate: (v: boolean) => void; autoRotateSpeed: (v: number) => void };
      };

      globe.globeImageUrl("https://unpkg.com/three-globe/example/img/earth-night.jpg");
      globe.bumpImageUrl("https://unpkg.com/three-globe/example/img/earth-topology.png");
      globe.backgroundImageUrl("https://unpkg.com/three-globe/example/img/night-sky.png");
      (globe as { showAtmosphere?: (v: boolean) => void }).showAtmosphere?.(false); // avoid opacity null read in lib

      // Defer hex data so internal materials exist (avoids opacity null read in lib)
          const applyHexData = () => {
            if (!mounted || !globeRef.current) return;
            try {
              const data = pointsRef.current;
              if (Array.isArray(data) && data.length > 0) globe.hexBinPointsData(data);
            } catch (e) {
              console.warn("Globe hex bin data:", e);
            }
          };
          globe.onGlobeReady(() => {
            requestAnimationFrame(() => {
              requestAnimationFrame(() => setTimeout(applyHexData, 150));
            });
          });

      // Hex Bin Layer – larger hexes and height so they’re visible with ~4k artists
      globe.hexBinPointLat("lat");
      globe.hexBinPointLng("lng");
      globe.hexBinPointWeight((d: MapPoint) => d.count);
      globe.hexBinResolution(5); // finer grid so many cities show as separate pillars // bigger cells (resolution 3 = fewer, larger hexagons)
      // Altitude: minimum 0.12 so every bin is visible; scale with artist count
      globe.hexAltitude((d: HexBin) => Math.min(0.65, 0.12 + d.sumWeight * 0.012));
      // Per-style colors. "All styles": color by dominant style in bin; single style: one color.
      // Always return a valid color string so three-globe’s colorAlpha() never gets null.
      const hexColor = (d: HexBin) => {
        const list = stylesRef.current;
        let style = selectedStyleRef.current;
        if (!style && d?.points?.length && list.length > 0) {
          // All styles: dominant style in this hex bin
          const byStyle = new Map<string, number>();
          for (const p of d.points) {
            const s = p.style ?? "";
            if (s) byStyle.set(s, (byStyle.get(s) ?? 0) + (Number(p.count) || 0));
          }
          let maxCount = 0;
          for (const [s, c] of byStyle) {
            if (c > maxCount) {
              maxCount = c;
              style = s;
            }
          }
        }
        const base =
          style && list.length > 0
            ? getStyleColor(style, list)
            : STYLE_PALETTE[0];
        const w = Number(d?.sumWeight) || 0;
        const t = Math.min(1, Math.max(0, w / 80));
        const brighten = 1 + 0.15 * t;
        const match = base.match(/rgb\((\d+),(\d+),(\d+)\)/);
        if (match) {
          const r = Math.min(255, Math.round(Number(match[1]) * brighten));
          const g = Math.min(255, Math.round(Number(match[2]) * brighten));
          const b = Math.min(255, Math.round(Number(match[3]) * brighten));
          return `rgb(${r},${g},${b})`;
        }
        return base;
      };
      globe.hexTopColor(hexColor);
      globe.hexSideColor(hexColor);
      globe.hexLabel((d: HexBin) => {
        const list = d.points
          .slice()
          .sort((a, b) => b.count - a.count)
          .slice(0, 8)
          .map((p) => (p.city ? `${p.city}, ${p.country}: ${p.count}` : `${p.country}: ${p.count}`));
        return `${d.sumWeight} artists in this region:\n${list.join("\n")}${d.points.length > 8 ? "\n…" : ""}`;
      });
      globe.hexBinMerge(false); // keep false so hover/tooltips work
      globe.enablePointerInteraction(true);

      const controls = globe.controls() as {
        autoRotate: boolean;
        autoRotateSpeed: number;
        addEventListener: (event: string, fn: () => void) => void;
        removeEventListener: (event: string, fn: () => void) => void;
      };
      controls.autoRotate = true;
      controls.autoRotateSpeed = 0.4;

      const onInteractionStart = () => {
        if (autoRotateResumeTimeoutRef.current) {
          clearTimeout(autoRotateResumeTimeoutRef.current);
          autoRotateResumeTimeoutRef.current = null;
        }
        controls.autoRotate = false;
      };
      const onInteractionEnd = () => {
        autoRotateResumeTimeoutRef.current = setTimeout(() => {
          if (mounted) controls.autoRotate = true;
          autoRotateResumeTimeoutRef.current = null;
        }, 2000);
      };
      controlsHandlersRef.current = { start: onInteractionStart, end: onInteractionEnd };
      controls.addEventListener("start", onInteractionStart);
      controls.addEventListener("end", onInteractionEnd);

      globeRef.current = globe;
        } catch (e) {
          console.error("Globe init:", e);
        }
      })
      .catch((e) => console.error("Globe load:", e));
    return () => {
      mounted = false;
      if (autoRotateResumeTimeoutRef.current) {
        clearTimeout(autoRotateResumeTimeoutRef.current);
        autoRotateResumeTimeoutRef.current = null;
      }
      const globe = globeRef.current;
      const handlers = controlsHandlersRef.current;
      if (globe && handlers) {
        try {
          const ctrl = globe.controls() as { removeEventListener?: (event: string, fn: () => void) => void };
          if (typeof ctrl.removeEventListener === "function") {
            ctrl.removeEventListener("start", handlers.start);
            ctrl.removeEventListener("end", handlers.end);
          }
        } catch (_) {}
        controlsHandlersRef.current = null;
      }
      globeRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!globeRef.current || !Array.isArray(points) || points.length === 0) return;
    try {
      globeRef.current.hexBinPointsData(points);
    } catch (e) {
      console.warn("Globe hex bin update:", e);
    }
  }, [points]);

  return (
    <main className="relative min-h-screen">
      <div className="fixed inset-0 z-0" ref={containerRef} />
      <div className="absolute left-0 right-0 top-0 z-10 px-4 py-3 flex flex-wrap items-center gap-3 pointer-events-none [&>*]:pointer-events-auto">
        <select
          value={selectedStyle}
          onChange={(e) => setSelectedStyle(e.target.value)}
          className="rounded border border-white/30 bg-black/20 text-white px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-white/40"
          aria-label="Filter by style"
        >
          <option value="">All styles</option>
          {styles.map((s) => (
            <option key={s} value={s} className="bg-background text-foreground">
              {s}
            </option>
          ))}
        </select>
        {loading && (
          <span className="text-xs text-white/80">Loading…</span>
        )}
        {!loading && points.length > 0 && (
          <span className="text-xs text-white/80">
            {new Set(points.map((p) => `${p.city}|${p.country}`)).size} locations ·{" "}
            {totalArtists ?? points.reduce((s, p) => s + p.count, 0)} artists
          </span>
        )}
      </div>
    </main>
  );
}
