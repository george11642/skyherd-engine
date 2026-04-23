/**
 * Sparkline — dependency-free SVG sparkline.
 *
 * Extracted from CostTicker (Plan v1.1 Part B / B3) so AgentLane can reuse
 * the exact same aesthetic. Values are normalized to their own max per render;
 * when `values.length < 2` the component returns null so empty-state lanes
 * stay clean rather than rendering a single dot.
 */

export interface SparklineProps {
  values: number[];
  width?: number;
  height?: number;
  stroke?: string;
  className?: string;
}

export function Sparkline({
  values,
  width = 80,
  height = 24,
  stroke = "rgb(148 176 136)",
  className,
}: SparklineProps) {
  if (values.length < 2) return null;
  const max = Math.max(...values, 0.001);
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width;
    const y = height - (v / max) * height;
    return `${x},${y}`;
  });
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      aria-hidden="true"
      className={className ?? "shrink-0 opacity-60"}
    >
      <polyline
        points={pts.join(" ")}
        fill="none"
        stroke={stroke}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
