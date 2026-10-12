"use client";

import { useRef, type PointerEvent as ReactPointerEvent } from "react";

import type { Mannequin } from "@/lib/api";
import type { GuideLine } from "@/lib/figureGuides";
import { clampBend, posedJointMap } from "@/lib/mannequinPose";

type Props = {
  mannequin: Mannequin;
  bends: Record<string, number>;
  guides: GuideLine[];
  opacity: number;
  photoFlip: boolean;
  tone?: number;
  active?: boolean;
  onBend: (id: string, angle: number) => void;
  onSelect?: () => void;
};

const DRAG_PER_PIXEL = 0.012;

function strokeClass(part: string): string {
  if (part === "torso" || part === "pelvis") {
    return "pose-bone-torso";
  }
  if (part === "neck" || part === "clavicle") {
    return "pose-bone-thin";
  }
  return "pose-bone-limb";
}

function isFingerJoint(id: string): boolean {
  return /^[lr]_(thumb|index|middle|ring|pinky)_/.test(id);
}

/** 骨に沿った台形。w0 が始点側、w1 が終点側の半幅。 */
function wedgePoints(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  w0: number,
  w1: number,
): string {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const length = Math.hypot(dx, dy) || 1;
  const px = -dy / length;
  const py = dx / length;
  return [
    [x1 + px * w0, y1 + py * w0],
    [x2 + px * w1, y2 + py * w1],
    [x2 - px * w1, y2 - py * w1],
    [x1 - px * w0, y1 - py * w0],
  ]
    .map(([x, y]) => `${x},${y}`)
    .join(" ");
}

export function MannequinLegend({ observed, inferred }: { observed: string; inferred: string }) {
  return (
    <div className="mannequin-legend">
      <span>
        <i className="swatch is-observed" />
        {observed}
      </span>
      <span>
        <i className="swatch is-inferred" />
        {inferred}
      </span>
    </div>
  );
}

export function MannequinOverlay({
  mannequin,
  bends,
  guides,
  opacity,
  photoFlip,
  tone = 0,
  active = true,
  onBend,
  onSelect,
}: Props) {
  const dragRef = useRef<{ id: string; startX: number; startAngle: number } | null>(null);
  const aspect = mannequin.aspect && mannequin.aspect > 0 ? mannequin.aspect : 1;
  const points = posedJointMap(mannequin.joints);

  function beginDrag(event: ReactPointerEvent<SVGCircleElement>, id: string) {
    event.preventDefault();
    event.stopPropagation();
    if (!active) {
      onSelect?.();
      return;
    }
    dragRef.current = { id, startX: event.clientX, startAngle: bends[id] ?? 0 };
    const target = event.currentTarget;
    target.setPointerCapture(event.pointerId);

    const move = (ev: PointerEvent) => {
      const drag = dragRef.current;
      if (!drag) {
        return;
      }
      const direction = photoFlip ? -1 : 1;
      onBend(drag.id, clampBend(drag.startAngle + (ev.clientX - drag.startX) * DRAG_PER_PIXEL * direction));
    };
    const up = () => {
      dragRef.current = null;
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  return (
    <svg
      className={`contour pose-lines mannequin-svg tone-${tone % 4}${active ? " is-active" : ""}`}
      viewBox={`0 0 ${aspect} 1`}
      preserveAspectRatio="none"
    >
      <g opacity={opacity}>
      {mannequin.bones.map((bone) => {
        const start = points.get(bone.start);
        const end = points.get(bone.end);
        if (!start || !end || bone.part === "clavicle") {
          return null;
        }
        if (bone.part === "finger" || bone.part === "thumb" || bone.part === "foot") {
          const width =
            bone.part === "foot" ? [0.012, 0.034] : bone.part === "thumb" ? [0.008, 0.007] : [0.0065, 0.0055];
          return (
            <polygon
              key={bone.id}
              points={wedgePoints(start.x, start.y, end.x, end.y, width[0], width[1])}
              className={`pose-shape${bone.inferred ? " is-inferred" : " is-observed"}`}
            />
          );
        }
        return (
          <line
            key={bone.id}
            x1={start.x}
            y1={start.y}
            x2={end.x}
            y2={end.y}
            className={`pose-bone ${strokeClass(bone.part)}${bone.inferred ? " is-inferred" : " is-observed"}`}
          />
        );
      })}
      {mannequin.head && points.get(mannequin.head.joint_id) ? (
        <circle
          cx={points.get(mannequin.head.joint_id)!.x}
          cy={points.get(mannequin.head.joint_id)!.y}
          r={mannequin.head.radius}
          className={`pose-head${mannequin.head.inferred ? " is-inferred" : " is-observed"}`}
        />
      ) : null}
      {mannequin.joints.map((joint) => {
        const point = points.get(joint.id);
        if (!point || !joint.parent) {
          return null;
        }
        const showBall = !isFingerJoint(joint.id) && joint.id !== "foot_l" && joint.id !== "foot_r";
        if (!showBall) {
          return null;
        }
        return (
          <circle
            key={joint.id}
            cx={point.x}
            cy={point.y}
            r={0.01}
            className={`pose-joint${joint.inferred ? " is-inferred" : " is-observed"}`}
          />
        );
      })}
      </g>
      {guides.map((line, index) => (
        <g key={`${line.kind}-${index}`} className="pose-guide" pointerEvents="none">
          <line
            x1={line.x1}
            y1={line.y1}
            x2={line.x2}
            y2={line.y2}
            className={line.kind === "balance" ? "pose-guide-balance" : "pose-guide-ruler"}
          />
          {line.label ? (
            <text x={line.x2} y={line.y2} className="pose-guide-label" fontSize={0.028}>
              {line.label}
            </text>
          ) : null}
        </g>
      ))}
      {mannequin.joints.map((joint) => {
        const point = points.get(joint.id);
        if (!point || !joint.parent) {
          return null;
        }
        return (
          <circle
            key={joint.id}
            cx={point.x}
            cy={point.y}
            r={0.02}
            className="pose-hit"
            onPointerDown={(event) => beginDrag(event, joint.id)}
          />
        );
      })}
    </svg>
  );
}
