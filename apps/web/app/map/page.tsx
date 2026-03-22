"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { cellToLatLng, latLngToCell } from "h3-js";
import { X } from "lucide-react";

const LIST_PREVIEW = 24;
/** Must stay in sync with `globe.hexBinResolution(...)`. */
const HEX_H3_RESOLUTION = 5;
/**
 * Invisible point hit cylinders use this radius in **degrees** (globe.gl convention).
 * There is no true screen-space padding in WebGL; ~0.032° is a rough match for ~20px
 * at a typical map zoom (varies with zoom / latitude).
 */
const HEX_HIT_RADIUS_DEG = 0.032;
/** Delay before auto-rotate resumes after drag/zoom or closing the hex modal. */
const AUTO_ROTATE_RESUME_MS = 5000;

function uniqueLocationsFromPoints(points: MapPoint[]): { city: string; country: string }[] {
  const map = new Map<string, { city: string; country: string }>();
  for (const p of points) {
    const key = `${p.city.trim()}|${p.country.trim()}`;
    if (!map.has(key)) map.set(key, { city: p.city.trim(), country: p.country.trim() });
  }
  return [...map.values()];
}

function buildBrowseUrl(locations: { city: string; country: string }[], style: string): string {
  const params = new URLSearchParams();
  if (style.trim()) {
    params.set("styles", style.trim());
  }
  const countries = [...new Set(locations.map((l) => l.country).filter(Boolean))];
  const cities = [...new Set(locations.map((l) => l.city).filter(Boolean))];
  if (countries.length) {
    params.set("countries", countries.map((c) => encodeURIComponent(c)).join(","));
  }
  if (cities.length) {
    params.set("cities", cities.map((c) => encodeURIComponent(c)).join(","));
  }
  const q = params.toString();
  return q ? `/?${q}` : "/";
}

/** e.g. `United Kingdom: Lymington, New Milton · anime` */
function formatHexModalSubheader(
  locations: { city: string; country: string }[],
  styleFilter: string
): string {
  const byCountry = new Map<string, Set<string>>();
  for (const l of locations) {
    const country = l.country.trim();
    if (!country) continue;
    if (!byCountry.has(country)) byCountry.set(country, new Set());
    const city = l.city.trim();
    if (city) byCountry.get(country)!.add(city);
  }
  const countryOrder = [...byCountry.keys()].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
  const parts = countryOrder.map((country) => {
    const cities = [...byCountry.get(country)!].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
    return cities.length ? `${country}: ${cities.join(", ")}` : country;
  });
  let s = parts.join(" · ");
  const st = styleFilter.trim();
  if (st) s += ` · ${st}`;
  return s;
}

type MapPoint = {
  lat: number;
  lng: number;
  count: number;
  city: string;
  country: string;
  label: string;
  style?: string;
};

/** Sum of map point weights in a hex for the current style filter (matches list API intent). Raw globe sumWeight sums every point in the bin — with "All styles" that stacks multiple rows per city (one per style), so it over-counts vs unique artists. */
function filteredPillarCount(points: MapPoint[], styleFilter: string): number {
  const t = styleFilter.trim();
  if (!t) {
    return points.reduce((s, p) => s + (Number(p.count) || 0), 0);
  }
  return points.reduce((s, p) => {
    if ((p.style ?? "") !== t) return s;
    return s + (Number(p.count) || 0);
  }, 0);
}

function escapeHtmlText(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/**
 * Hex hover text: globe.gl passes tooltip strings through .html(), so use <br>.
 * With "All styles", many points share the same city (one row per style) — group by location
 * instead of repeating "Winnipeg, Canada: 3" per style row.
 */
function formatHexTooltipHtml(points: MapPoint[], styleFilter: string): string {
  const styleTrim = styleFilter.trim();
  const maxLines = 8;
  const lines: string[] = [];

  if (styleTrim) {
    const byLoc = new Map<string, number>();
    for (const p of points) {
      if ((p.style ?? "") !== styleTrim) continue;
      const key = `${p.city.trim()}|${p.country.trim()}`;
      byLoc.set(key, (byLoc.get(key) ?? 0) + (Number(p.count) || 0));
    }
    const sorted = [...byLoc.entries()].sort((a, b) => b[1] - a[1]);
    for (const [key, c] of sorted.slice(0, maxLines)) {
      const i = key.indexOf("|");
      const city = i >= 0 ? key.slice(0, i) : "";
      const country = i >= 0 ? key.slice(i + 1) : key;
      const loc =
        city.trim() !== ""
          ? `${escapeHtmlText(city)}, ${escapeHtmlText(country)}`
          : escapeHtmlText(country);
      lines.push(`${loc}: ${c}`);
    }
    if (sorted.length > maxLines) lines.push("…");
  } else {
    type StyleMap = Map<string, number>;
    const byLoc = new Map<string, StyleMap>();
    for (const p of points) {
      const city = p.city.trim();
      const country = p.country.trim();
      const key = `${city}|${country}`;
      if (!byLoc.has(key)) byLoc.set(key, new Map());
      const st = p.style ?? "";
      const m = byLoc.get(key)!;
      m.set(st, (m.get(st) ?? 0) + (Number(p.count) || 0));
    }
    const sumStyle = (m: StyleMap) => [...m.values()].reduce((s, n) => s + n, 0);
    const sorted = [...byLoc.entries()].sort((a, b) => sumStyle(b[1]) - sumStyle(a[1]));
    for (const [key, styles] of sorted.slice(0, maxLines)) {
      const i = key.indexOf("|");
      const city = i >= 0 ? key.slice(0, i) : "";
      const country = i >= 0 ? key.slice(i + 1) : key;
      const loc =
        city.trim() !== ""
          ? `${escapeHtmlText(city)}, ${escapeHtmlText(country)}`
          : escapeHtmlText(country);
      const parts = [...styles.entries()]
        .filter(([s]) => s)
        .sort((a, b) => b[1] - a[1])
        .map(([s, c]) => `${escapeHtmlText(s)} ${c}`);
      lines.push(parts.length ? `${loc}: ${parts.join(", ")}` : loc);
    }
    if (sorted.length > maxLines) lines.push("…");
  }

  const w = filteredPillarCount(points, styleFilter);
  const artistWord = w === 1 ? "artist" : "artists";
  const head = `${w} ${artistWord} in this region`;
  if (lines.length === 0) return head;
  return `${head}:<br>${lines.join("<br>")}`;
}

type HexBin = {
  points: MapPoint[];
  sumWeight: number;
  center: { lat: number; lng: number };
};

/** Invisible “fat finger” targets aligned to the same H3 cells as hex bins. */
type HexHitPoint = {
  lat: number;
  lng: number;
  alt: number;
  hex: HexBin;
};

function buildHexHitLayerPoints(points: MapPoint[], styleFilter: string): HexHitPoint[] {
  if (!points.length) return [];
  const byCell = new Map<string, MapPoint[]>();
  for (const p of points) {
    const idx = latLngToCell(p.lat, p.lng, HEX_H3_RESOLUTION);
    if (!byCell.has(idx)) byCell.set(idx, []);
    byCell.get(idx)!.push(p);
  }
  const out: HexHitPoint[] = [];
  for (const [h3Idx, cellPoints] of byCell) {
    const [lat, lng] = cellToLatLng(h3Idx);
    const sumWeight = cellPoints.reduce((s, p) => s + (Number(p.count) || 0), 0);
    const w = filteredPillarCount(cellPoints, styleFilter);
    const alt = Math.min(0.65, 0.12 + w * 0.012);
    out.push({
      lat,
      lng,
      alt,
      hex: {
        points: cellPoints,
        sumWeight,
        center: { lat, lng },
      },
    });
  }
  return out;
}

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

type HexModalState =
  | null
  | {
      locations: { city: string; country: string }[];
      artists: { id: string; name: string }[];
      loading: boolean;
      error: string | null;
      styleFilter: string;
    };

export default function MapPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<{
    hexBinPointsData: (data: MapPoint[]) => unknown;
    pointsData: (data: HexHitPoint[]) => unknown;
    controls: () => unknown;
  } | null>(null);
  const orbitControlsRef = useRef<{
    autoRotate: boolean;
    addEventListener: (event: string, fn: () => void) => void;
    removeEventListener: (event: string, fn: () => void) => void;
  } | null>(null);
  const pointsRef = useRef<MapPoint[]>([]);
  const selectedStyleRef = useRef<string>("");
  const stylesRef = useRef<string[]>([]);
  const autoRotateResumeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const controlsHandlersRef = useRef<{ start: () => void; end: () => void } | null>(null);
  const mountedRef = useRef(true);
  const [styles, setStyles] = useState<string[]>([]);
  const [selectedStyle, setSelectedStyle] = useState<string>("");
  const [points, setPoints] = useState<MapPoint[]>([]);
  const [totalArtists, setTotalArtists] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [hexModal, setHexModal] = useState<HexModalState>(null);

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

  const stopAutoRotate = useCallback(() => {
    if (autoRotateResumeTimeoutRef.current) {
      clearTimeout(autoRotateResumeTimeoutRef.current);
      autoRotateResumeTimeoutRef.current = null;
    }
    const c = orbitControlsRef.current;
    if (c) c.autoRotate = false;
  }, []);

  const scheduleAutoRotateResume = useCallback(() => {
    if (autoRotateResumeTimeoutRef.current) {
      clearTimeout(autoRotateResumeTimeoutRef.current);
      autoRotateResumeTimeoutRef.current = null;
    }
    const c = orbitControlsRef.current;
    if (!c) return;
    autoRotateResumeTimeoutRef.current = setTimeout(() => {
      if (mountedRef.current) c.autoRotate = true;
      autoRotateResumeTimeoutRef.current = null;
    }, AUTO_ROTATE_RESUME_MS);
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

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
        hexMargin: (n: number) => unknown;
        hexAltitude: (a: (d: HexBin) => number) => unknown;
        hexTopColor: (a: (d: HexBin) => string) => unknown;
        hexSideColor: (a: (d: HexBin) => string) => unknown;
        hexLabel: (a: (d: HexBin) => string) => unknown;
        hexBinMerge: (v: boolean) => unknown;
        enablePointerInteraction: (v: boolean) => unknown;
        hexBinPointsData: (d: MapPoint[]) => unknown;
        onHexClick: (fn: (d: HexBin) => void) => unknown;
        pointsData: (d: HexHitPoint[]) => unknown;
        pointLat: (a: string) => unknown;
        pointLng: (a: string) => unknown;
        pointAltitude: (a: (d: HexHitPoint) => number) => unknown;
        pointRadius: (n: number) => unknown;
        pointColor: (a: () => string) => unknown;
        pointLabel: (a: (d: HexHitPoint) => string) => unknown;
        pointsMerge: (v: boolean) => unknown;
        pointsTransitionDuration: (n: number) => unknown;
        onPointClick: (fn: (d: HexHitPoint) => void) => unknown;
        controls: () => unknown;
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
      globe.hexBinResolution(HEX_H3_RESOLUTION);
      // Full H3 footprint for hits (default margin shrinks only the mesh, not bin membership).
      globe.hexMargin(0);
      // Altitude: minimum 0.12 so every bin is visible; scale with artist count
      globe.hexAltitude((d: HexBin) => {
        const w = filteredPillarCount(d.points as MapPoint[], selectedStyleRef.current);
        return Math.min(0.65, 0.12 + w * 0.012);
      });
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
        const w = filteredPillarCount((d?.points ?? []) as MapPoint[], selectedStyleRef.current);
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
      globe.hexLabel((d: HexBin) =>
        formatHexTooltipHtml(d.points as MapPoint[], selectedStyleRef.current)
      );
      globe.hexBinMerge(false); // keep false so hover/tooltips work
      globe.enablePointerInteraction(true);

      // Wider invisible cylinders at each cell (same H3 index as hex layer) for easier hover/click.
      globe.pointsMerge(false);
      globe.pointsTransitionDuration(0);
      globe.pointLat("lat");
      globe.pointLng("lng");
      globe.pointAltitude((d: HexHitPoint) => d.alt);
      globe.pointRadius(HEX_HIT_RADIUS_DEG);
      globe.pointColor(() => "rgba(255,255,255,0.006)");
      globe.pointLabel((d: HexHitPoint) =>
        formatHexTooltipHtml(d.hex.points as MapPoint[], selectedStyleRef.current)
      );

      const controls = globe.controls() as unknown as {
        autoRotate: boolean;
        autoRotateSpeed: number;
        addEventListener: (event: string, fn: () => void) => void;
        removeEventListener: (event: string, fn: () => void) => void;
      };
      orbitControlsRef.current = controls;
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
        }, AUTO_ROTATE_RESUME_MS);
      };
      controlsHandlersRef.current = { start: onInteractionStart, end: onInteractionEnd };
      controls.addEventListener("start", onInteractionStart);
      controls.addEventListener("end", onInteractionEnd);

      const openHexAreaModal = (hex: HexBin) => {
        if (!hex?.points?.length) return;
        stopAutoRotate();
        const locations = uniqueLocationsFromPoints(hex.points as MapPoint[]);
        const styleFilter = selectedStyleRef.current;
        setHexModal({
          locations,
          artists: [],
          loading: true,
          error: null,
          styleFilter,
        });
        void fetch("/api/map-hex-artists", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            locations,
            style: styleFilter || null,
          }),
        })
          .then(async (res) => {
            if (!res.ok) throw new Error(await res.text());
            return res.json() as Promise<{ artists: { id: string; name: string }[] }>;
          })
          .then((data) => {
            setHexModal((prev) =>
              prev && prev.loading
                ? {
                    ...prev,
                    loading: false,
                    artists: data.artists ?? [],
                    error: null,
                  }
                : prev
            );
          })
          .catch((e) => {
            setHexModal((prev) =>
              prev && prev.loading
                ? {
                    ...prev,
                    loading: false,
                    artists: [],
                    error: e instanceof Error ? e.message : "Failed to load artists",
                  }
                : prev
            );
          });
      };

      globe.onHexClick((hex: HexBin) => openHexAreaModal(hex));
      globe.onPointClick((d: HexHitPoint) => openHexAreaModal(d.hex));

      globe.pointsData(buildHexHitLayerPoints(pointsRef.current, selectedStyleRef.current));

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
          const ctrl = globe.controls() as unknown as { removeEventListener?: (event: string, fn: () => void) => void };
          if (typeof ctrl.removeEventListener === "function") {
            ctrl.removeEventListener("start", handlers.start);
            ctrl.removeEventListener("end", handlers.end);
          }
        } catch (_) {}
        controlsHandlersRef.current = null;
      }
      orbitControlsRef.current = null;
      globeRef.current = null;
    };
  }, [stopAutoRotate]);

  useEffect(() => {
    if (!globeRef.current || !Array.isArray(points) || points.length === 0) return;
    try {
      globeRef.current.hexBinPointsData(points);
    } catch (e) {
      console.warn("Globe hex bin update:", e);
    }
  }, [points]);

  useEffect(() => {
    const g = globeRef.current;
    if (!g?.pointsData) return;
    try {
      g.pointsData(points.length ? buildHexHitLayerPoints(points, selectedStyle) : []);
    } catch (e) {
      console.warn("Globe hex hit layer:", e);
    }
  }, [points, selectedStyle]);

  useEffect(() => {
    if (!hexModal) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setHexModal(null);
        scheduleAutoRotateResume();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [hexModal, scheduleAutoRotateResume]);

  return (
    <main className="relative min-h-screen">
      <div className="fixed inset-0 z-0" ref={containerRef} />
      <div className="absolute left-0 right-0 top-0 z-10 px-4 py-3 flex flex-wrap items-center gap-3 pointer-events-none [&>*]:pointer-events-auto">
        <select
          value={selectedStyle}
          onChange={(e) => setSelectedStyle(e.target.value)}
          className="h-[26px] min-w-[8rem] max-w-[min(100%,14rem)] cursor-pointer rounded border border-white/30 bg-black/20 text-xs text-white focus:outline-none focus:ring-2 focus:ring-white/40"
          style={{
            appearance: "none",
            WebkitAppearance: "none",
            paddingLeft: 12,
            paddingRight: 28,
            lineHeight: "26px",
            backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='white' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E")`,
            backgroundRepeat: "no-repeat",
            backgroundSize: "0.875rem 0.875rem",
            backgroundPosition: "right 10px center",
          }}
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

      {hexModal && (
        <div
          className="fixed inset-0 z-30 flex items-center justify-center bg-black/55 p-4"
          onClick={() => {
            setHexModal(null);
            scheduleAutoRotateResume();
          }}
          role="presentation"
        >
          <div
            className="w-full max-w-md rounded-lg border border-white/25 bg-zinc-950/95 p-4 text-white shadow-xl backdrop-blur-sm"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="map-hex-modal-title"
          >
            <div className="flex justify-between items-start gap-3 mb-2">
              <h2 id="map-hex-modal-title" className="text-sm font-semibold pr-2">
                {hexModal.loading ? (
                  "Loading artists in this area"
                ) : hexModal.error ? (
                  "Artists in this area"
                ) : (
                  <>
                    {hexModal.artists.length} Artist{hexModal.artists.length !== 1 ? "s" : ""} in this
                    area
                  </>
                )}
              </h2>
              <button
                type="button"
                onClick={() => {
                  setHexModal(null);
                  scheduleAutoRotateResume();
                }}
                className="shrink-0 rounded text-white/55 hover:text-white transition-colors"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="text-xs text-white/65">
              {formatHexModalSubheader(hexModal.locations, hexModal.styleFilter)}
            </p>
            {hexModal.error && (
              <p className="mt-3 text-xs text-red-300">{hexModal.error}</p>
            )}
            {!hexModal.loading && !hexModal.error && (
              <>
                {hexModal.artists.length === 0 ? (
                  <p className="mt-3 text-xs text-white/60">No matching artists in the directory.</p>
                ) : (
                  <ul className="mt-3 max-h-52 overflow-y-auto rounded-md border border-white/15 text-xs divide-y divide-white/10">
                    {hexModal.artists.slice(0, LIST_PREVIEW).map((a) => (
                      <li key={a.id} className="truncate px-2.5 py-2">
                        {a.name}
                      </li>
                    ))}
                  </ul>
                )}
                {hexModal.artists.length > LIST_PREVIEW && (
                  <p className="mt-2 text-xs text-white/45">
                    …and {hexModal.artists.length - LIST_PREVIEW} more
                  </p>
                )}
              </>
            )}

            <div className="mt-4 flex flex-wrap justify-end">
              {hexModal.loading ? (
                <span
                  className="rounded bg-white/35 px-3 py-1.5 text-xs font-medium text-black/50 cursor-not-allowed"
                  aria-disabled="true"
                >
                  Show Artists
                </span>
              ) : (
                <a
                  href={buildBrowseUrl(hexModal.locations, hexModal.styleFilter)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded bg-white px-3 py-1.5 text-xs font-medium text-black hover:bg-white/90"
                >
                  Show Artists
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
