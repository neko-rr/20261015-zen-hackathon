"use client";

import type { PointerEvent as ReactPointerEvent } from "react";

export const PERSPECTIVE_IDS = ["off", "horizon", "one", "two"] as const;
export type PerspectiveMode = (typeof PERSPECTIVE_IDS)[number];

type Props = {
  mode: PerspectiveMode;
  horizonY: number;
  vpOne: number;
  vpLeft: number;
  vpRight: number;
  onHorizon: (y: number) => void;
  onVpOne: (x: number) => void;
  onVpLeft: (x: number) => void;
  onVpRight: (x: number) => void;
  photoFlip: boolean;
};

const RAY_DEGREES = [30, 55, 90, 125, 150];

export function PerspectiveGuide({
  mode,
  horizonY,
  vpOne,
  vpLeft,
  vpRight,
  onHorizon,
  onVpOne,
  onVpLeft,
  onVpRight,
  photoFlip,
}: Props) {
  if (mode === "off") {
    return null;
  }
  const points =
    mode === "one" ? [vpOne] : mode === "two" ? [vpLeft, vpRight] : [];

  function drag(event: ReactPointerEvent<SVGElement>, apply: (x: number, y: number) => void) {
    event.preventDefault();
    event.stopPropagation();
    const svg = event.currentTarget.ownerSVGElement;
    if (!svg) {
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    const move = (ev: PointerEvent) => {
      const rect = svg.getBoundingClientRect();
      if (rect.width < 1 || rect.height < 1) {
        return;
      }
      const visualX = (ev.clientX - rect.left) / rect.width;
      apply(photoFlip ? 1 - visualX : visualX, (ev.clientY - rect.top) / rect.height);
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  return (
    <svg className="perspective-svg" viewBox="0 0 1 1" preserveAspectRatio="none">
      {points.flatMap((x, index) =>
        RAY_DEGREES.map((degrees) => {
          const line = lineAcross(x, horizonY, degrees);
          if (!line) {
            return null;
          }
          return (
            <line
              key={`${index}-${degrees}`}
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              className="perspective-ray"
            />
          );
        }),
      )}
      <line x1={0} y1={horizonY} x2={1} y2={horizonY} className="perspective-horizon" />
      <line
        x1={0}
        y1={horizonY}
        x2={1}
        y2={horizonY}
        className="perspective-hit"
        onPointerDown={(event) => drag(event, (_x, y) => onHorizon(clamp(y, 0.04, 0.96)))}
      />
      {mode === "one" ? (
        <circle
          cx={vpOne}
          cy={horizonY}
          r={0.018}
          className="perspective-vp"
          onPointerDown={(event) => drag(event, (x) => onVpOne(clamp(x, 0.04, 0.96)))}
        />
      ) : null}
      {mode === "two" ? (
        <>
          <circle
            cx={vpLeft}
            cy={horizonY}
            r={0.018}
            className="perspective-vp"
            onPointerDown={(event) => drag(event, (x) => onVpLeft(clamp(x, 0.04, 0.96)))}
          />
          <circle
            cx={vpRight}
            cy={horizonY}
            r={0.018}
            className="perspective-vp is-second"
            onPointerDown={(event) => drag(event, (x) => onVpRight(clamp(x, 0.04, 0.96)))}
          />
        </>
      ) : null}
    </svg>
  );
}

function lineAcross(x: number, y: number, degrees: number): { x1: number; y1: number; x2: number; y2: number } | null {
  const rad = (degrees * Math.PI) / 180;
  const dx = Math.cos(rad);
  const dy = Math.sin(rad);
  const hits: { t: number; x: number; y: number }[] = [];
  const push = (t: number, px: number, py: number) => {
    if (px < -0.001 || px > 1.001 || py < -0.001 || py > 1.001) {
      return;
    }
    hits.push({ t, x: clamp(px, 0, 1), y: clamp(py, 0, 1) });
  };
  if (Math.abs(dx) > 1e-6) {
    push((0 - x) / dx, 0, y + ((0 - x) / dx) * dy);
    push((1 - x) / dx, 1, y + ((1 - x) / dx) * dy);
  }
  if (Math.abs(dy) > 1e-6) {
    push((0 - y) / dy, x + ((0 - y) / dy) * dx, 0);
    push((1 - y) / dy, x + ((1 - y) / dy) * dx, 1);
  }
  if (hits.length < 2) {
    return null;
  }
  hits.sort((a, b) => a.t - b.t);
  const start = hits[0];
  const end = hits[hits.length - 1];
  if (Math.hypot(start.x - end.x, start.y - end.y) < 0.02) {
    return null;
  }
  return { x1: start.x, y1: start.y, x2: end.x, y2: end.y };
}

function clamp(value: number, min: number, max: number): number {
  if (value < min) {
    return min;
  }
  if (value > max) {
    return max;
  }
  return value;
}
