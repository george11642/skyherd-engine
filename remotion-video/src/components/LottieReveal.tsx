/**
 * LottieReveal — phase E2 wrapper around @remotion/lottie.
 *
 * Loads a Lottie JSON from staticFile() and renders the animation in a
 * positioned, optionally-scaled box. Used by Main.tsx to drop in:
 *
 *   * stat-counter at the cost-ticker beat ("$4.17/week")
 *   * map-pin-drop at scenario triggers
 *   * hash-chip-slide at attestation moments
 *   * pulse-wave for sensor activity
 *   * check-complete for scenario resolution
 *
 * Fail-soft: if the JSON 404s the component renders nothing rather than
 * crashing the composition.
 */
import { Lottie, type LottieAnimationData } from "@remotion/lottie";
import { staticFile } from "remotion";
import { useEffect, useState } from "react";

export type LottieRevealProps = {
  /** Filename inside public/lottie/, e.g. "stat-counter.json" */
  asset: string;
  /** Box width in px (height auto-scales) */
  size?: number;
  /** Top in px from composition top (or use bottom). */
  top?: number;
  bottom?: number;
  /** Left in px from composition left (or use right). */
  left?: number;
  right?: number;
  /** Loop animation; default false. */
  loop?: boolean;
};

export const LottieReveal = ({
  asset,
  size = 220,
  top,
  bottom,
  left,
  right,
  loop = false,
}: LottieRevealProps) => {
  const [data, setData] = useState<LottieAnimationData | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(staticFile(`lottie/${asset}`))
      .then((r) => r.json() as Promise<LottieAnimationData>)
      .then((j) => {
        if (!cancelled) setData(j);
      })
      .catch(() => {
        // decorative — never crash render on 404
      });
    return () => {
      cancelled = true;
    };
  }, [asset]);

  if (!data) return null;

  return (
    <div
      style={{
        position: "absolute",
        top,
        bottom,
        left,
        right,
        width: size,
        height: size,
        pointerEvents: "none",
      }}
    >
      <Lottie animationData={data} loop={loop} playbackRate={1} />
    </div>
  );
};
