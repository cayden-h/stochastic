"use client";

import { useEffect, useRef } from "react";

/* The Stochastic mark (docs/design/brand.md): a random walk inside a circle, with a filled start dot and barbed
 * arrowheads along the walk. Geometry in the 1300-unit source, shown through the viewBox 240 240 820 820.
 * desktop/splash.html repeats this geometry and the timings below; change both together. */

const VIEWBOX = "240 240 820 820";
const RING = { cx: 650, cy: 650, r: 392 };
const WALK: [number, number][] = [
  [437, 397], [550, 588], [752, 385], [345, 637], [812, 925], [812, 628],
  [402, 763], [515, 898], [958, 793], [622, 632], [782, 498], [896, 566],
];
/** Where each arrowhead sits along its segment (segments 1 to 11), read from the reference mark. */
const HEAD_AT = [0.55, 0.62, 0.62, 0.55, 0.35, 0.47, 0.35, 0.55, 0.55, 0.55, 0.45];
const HEAD_PATH = "M12 0 L-12 -11 L-5 0 L-12 11 Z";
const STROKE = 7;
const DOT_R = 27;
const POINTS = WALK.map((p) => p.join(",")).join(" ");
const RING_LEN = 2 * Math.PI * RING.r;

/** Each arrowhead's position, angle, and the walk length at which it appears while the walk draws. */
const HEADS = (() => {
  let total = 0;
  return HEAD_AT.map((f, i) => {
    const [x1, y1] = WALK[i];
    const [x2, y2] = WALK[i + 1];
    const len = Math.hypot(x2 - x1, y2 - y1);
    const head = {
      at: total + len * f,
      transform: `translate(${x1 + (x2 - x1) * f} ${y1 + (y2 - y1) * f}) rotate(${(Math.atan2(y2 - y1, x2 - x1) * 180) / Math.PI})`,
    };
    total += len;
    return head;
  });
})();
const WALK_LEN = WALK.slice(1).reduce((sum, [x, y], i) => sum + Math.hypot(x - WALK[i][0], y - WALK[i][1]), 0);

/** The launch timings in ms, from the approved prototype. */
export const LAUNCH = { ring: [0, 380], dot: [300, 460], walk: [420, 1500], word: 1450, wordFade: 320, hold: 2100 } as const;

interface MarkProps {
  /** Rendered width and height in px. */
  size: number;
  className?: string;
  /** Accessible name; the mark is decorative when left out. */
  title?: string;
}

/** The static mark. Ink is currentColor, so it follows the surrounding text color and theme.
 * Below 64 px it switches to the small mark (heavier strokes, no arrowheads), which stays legible at 16 to 32 px. */
export function StochasticMark({ size, className, title }: MarkProps) {
  const a11y = title ? { role: "img", "aria-label": title } : { "aria-hidden": true };
  if (size < 64) {
    return (
      <svg width={size} height={size} viewBox="230 230 840 840" className={className} {...a11y}>
        <circle {...RING} fill="none" stroke="currentColor" strokeWidth={40} />
        <polyline points={POINTS} fill="none" stroke="currentColor" strokeWidth={40} strokeLinejoin="round" />
        <circle cx={WALK[0][0]} cy={WALK[0][1]} r={45} fill="currentColor" />
      </svg>
    );
  }
  return (
    <svg width={size} height={size} viewBox={VIEWBOX} className={className} {...a11y}>
      <circle {...RING} fill="none" stroke="currentColor" strokeWidth={STROKE} />
      <polyline points={POINTS} fill="none" stroke="currentColor" strokeWidth={STROKE} strokeLinejoin="miter" />
      {HEADS.map((h) => <path key={h.transform} d={HEAD_PATH} transform={h.transform} fill="currentColor" />)}
      <circle cx={WALK[0][0]} cy={WALK[0][1]} r={DOT_R} fill="currentColor" />
    </svg>
  );
}

const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const clamp = (t: number) => Math.max(0, Math.min(1, t));
const span = (ms: number, [a, b]: readonly [number, number]) => clamp((ms - a) / (b - a));

/** The launch lockup: the mark drawing itself, then "stochastic" below it, with the exact prototype timings.
 * The ring draws clockwise from the top, the start dot pops with a slight overshoot, the walk draws and each
 * arrowhead appears as the line passes it, and the name fades up at 1450 ms. With reduced motion it shows
 * finished at once. Painted by direct DOM writes per frame, so React does not re-render 60 times a second. */
export function AnimatedStochasticLockup({ size, className }: { size: number; className?: string }) {
  const ring = useRef<SVGCircleElement>(null);
  const walk = useRef<SVGPolylineElement>(null);
  const dot = useRef<SVGCircleElement>(null);
  const heads = useRef<(SVGPathElement | null)[]>([]);
  const word = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const paint = (ringT: number, dotScale: number, walkT: number) => {
      ring.current?.style.setProperty("stroke-dashoffset", String(RING_LEN * (1 - ringT)));
      dot.current?.setAttribute("r", String(DOT_R * dotScale));
      const drawn = WALK_LEN * walkT;
      walk.current?.style.setProperty("stroke-dashoffset", String(WALK_LEN - drawn));
      heads.current.forEach((h, i) => h?.style.setProperty("opacity", drawn >= HEADS[i].at ? "1" : "0"));
    };
    const showWord = () => word.current?.classList.add("on");
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      paint(1, 1, 1);
      showWord();
      return;
    }
    let raf = 0;
    const t0 = performance.now();
    const frame = (now: number) => {
      const ms = now - t0;
      const d = span(ms, LAUNCH.dot);
      paint(ease(span(ms, LAUNCH.ring)), d < 1 ? 1.25 * Math.sin((d * Math.PI) / 2) - 0.25 * d : 1, ease(span(ms, LAUNCH.walk)));
      if (ms < LAUNCH.walk[1]) raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    const timer = setTimeout(showWord, LAUNCH.word);
    return () => { cancelAnimationFrame(raf); clearTimeout(timer); };
  }, []);

  return (
    <div className={`flex flex-col items-center gap-[14px] ${className ?? ""}`}>
      <svg width={size} height={size} viewBox={VIEWBOX} className="overflow-visible" aria-hidden="true">
        <circle
          ref={ring} {...RING} fill="none" stroke="currentColor" strokeWidth={STROKE}
          transform={`rotate(-90 ${RING.cx} ${RING.cy})`} style={{ strokeDasharray: RING_LEN, strokeDashoffset: RING_LEN }}
        />
        <polyline
          ref={walk} points={POINTS} fill="none" stroke="currentColor" strokeWidth={STROKE} strokeLinejoin="miter"
          style={{ strokeDasharray: WALK_LEN, strokeDashoffset: WALK_LEN }}
        />
        {HEADS.map((h, i) => (
          <path key={h.transform} ref={(el) => { heads.current[i] = el; }} d={HEAD_PATH} transform={h.transform} fill="currentColor" style={{ opacity: 0 }} />
        ))}
        <circle ref={dot} cx={WALK[0][0]} cy={WALK[0][1]} r={0} fill="currentColor" />
      </svg>
      <span ref={word} className="launch-word font-serif text-[48px] leading-none tracking-[0.01em]">stochastic</span>
    </div>
  );
}
