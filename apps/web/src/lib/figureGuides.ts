/** 頭身の目盛りと、首の付け根から床までの重心線。 */

import type { Mannequin } from "@/lib/api";
import type { HeadId } from "@/lib/proportions";

export type GuideLine = {
  kind: "ruler" | "balance";
  x1: number;
  y1: number;
  z1: number;
  x2: number;
  y2: number;
  z2: number;
  label?: string;
};

export function buildGuides(
  mannequin: Mannequin,
  head: HeadId,
  showRuler: boolean,
  showBalance: boolean,
): GuideLine[] {
  if (!mannequin.joints.length) {
    return [];
  }
  const lines: GuideLine[] = [];
  const span = bodySpan(mannequin);
  if (!span) {
    return lines;
  }
  if (showRuler) {
    lines.push(...rulerLines(mannequin, head, span));
  }
  if (showBalance) {
    const balance = balanceLine(mannequin, span.bottom);
    if (balance) {
      lines.push(balance);
    }
  }
  return lines;
}

type Span = { top: number; bottom: number; unit: number; minX: number; maxX: number; z: number };

function bodySpan(mannequin: Mannequin): Span | null {
  const head = mannequin.head;
  const byId = new Map(mannequin.joints.map((joint) => [joint.id, joint]));
  const headPoint = byId.get(head?.joint_id ?? "head");
  if (!head || !headPoint || head.radius < 1e-5) {
    return null;
  }
  let bottom = headPoint.y;
  for (const id of ["foot_l", "foot_r", "ankle_l", "ankle_r"]) {
    const point = byId.get(id);
    if (point && point.y > bottom) {
      bottom = point.y;
    }
  }
  let top = headPoint.y - head.radius;
  if (top > bottom) {
    const swap = top;
    top = bottom;
    bottom = swap;
  }
  const height = bottom - top;
  if (height < 1e-4) {
    return null;
  }
  let minX = Infinity;
  let maxX = -Infinity;
  for (const joint of mannequin.joints) {
    minX = Math.min(minX, joint.x);
    maxX = Math.max(maxX, joint.x);
  }
  const chest = byId.get("chest");
  return {
    top,
    bottom,
    unit: head.radius * 2,
    minX,
    maxX,
    z: chest?.z ?? 0,
  };
}

function rulerLines(mannequin: Mannequin, head: HeadId, span: Span): GuideLine[] {
  const height = span.bottom - span.top;
  const unit = head === "photo" ? span.unit : height / Number(head);
  if (unit < 1e-4) {
    return [];
  }
  const aspect = mannequin.aspect && mannequin.aspect > 0 ? mannequin.aspect : 1;
  const gap = Math.max(unit * 0.35, 0.02);
  const right = span.maxX + gap;
  const useRight = right <= aspect - 0.012 || span.minX - gap < 0.012;
  const x = useRight ? Math.min(right, aspect - 0.012) : Math.max(span.minX - gap, 0.012);
  const sign = useRight ? 1 : -1;
  const tick = Math.min(unit * 0.42, 0.04) * sign;
  const lines: GuideLine[] = [
    {
      kind: "ruler",
      x1: x,
      y1: span.top,
      z1: span.z,
      x2: x,
      y2: span.bottom,
      z2: span.z,
    },
  ];
  const steps = Math.max(Math.floor(height / unit + 1e-3), 0);
  let last = span.top;
  for (let index = 0; index <= steps; index += 1) {
    const y = span.top + index * unit;
    if (y > span.bottom + unit * 0.02) {
      break;
    }
    last = y;
    lines.push(tickLine(x, y, tick, span.z, String(index)));
  }
  if (span.bottom - last > unit * 0.12) {
    const count = height / unit;
    lines.push(tickLine(x, span.bottom, tick, span.z, count.toFixed(1)));
  }
  return lines;
}

function tickLine(x: number, y: number, tick: number, z: number, label: string): GuideLine {
  return {
    kind: "ruler",
    x1: x,
    y1: y,
    z1: z,
    x2: x + tick,
    y2: y,
    z2: z,
    label,
  };
}

function balanceLine(mannequin: Mannequin, sole: number): GuideLine | null {
  const neck = mannequin.joints.find((joint) => joint.id === "neck");
  if (!neck) {
    return null;
  }
  return {
    kind: "balance",
    x1: neck.x,
    y1: neck.y,
    z1: neck.z,
    x2: neck.x,
    y2: sole,
    z2: neck.z,
  };
}
