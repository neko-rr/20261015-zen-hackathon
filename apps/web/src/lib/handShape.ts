/** 開く・自然・握る。自然は写真の指のまま。 */

import type { Mannequin, MannequinJoint } from "@/lib/api";

export const HAND_IDS = ["natural", "open", "fist"] as const;
export type HandId = (typeof HAND_IDS)[number];

const FINGERS = ["thumb", "index", "middle", "ring", "pinky"] as const;

type Pt = { x: number; y: number; z: number };

export function applyHandShape(mannequin: Mannequin, shape: HandId): Mannequin {
  if (shape === "natural" || !mannequin.joints.length) {
    return mannequin;
  }
  const pos = new Map<string, Pt>();
  for (const joint of mannequin.joints) {
    pos.set(joint.id, { x: joint.x, y: joint.y, z: joint.z });
  }
  for (const side of ["l", "r"] as const) {
    if (shape === "open") {
      straighten(pos, side);
    } else {
      curlFist(pos, side);
    }
  }
  const joints: MannequinJoint[] = mannequin.joints.map((joint) => {
    const next = pos.get(joint.id);
    if (!next) {
      return joint;
    }
    return { ...joint, x: next.x, y: next.y, z: next.z };
  });
  return { ...mannequin, joints };
}

function straighten(pos: Map<string, Pt>, side: string) {
  const wrist = pos.get(`wrist_${side}`);
  if (!wrist) {
    return;
  }
  for (const name of FINGERS) {
    const first = pos.get(`${side}_${name}_1`);
    if (!first) {
      continue;
    }
    const direction = unit(sub(first, wrist), { x: 0, y: 1, z: 0 });
    let previous = first;
    for (let step = 2; step <= 4; step += 1) {
      const id = `${side}_${name}_${step}`;
      const current = pos.get(id);
      if (!current) {
        continue;
      }
      const length = Math.max(distance(previous, current), 0.004);
      const next = add(previous, direction, length);
      pos.set(id, next);
      previous = next;
    }
  }
}

function curlFist(pos: Map<string, Pt>, side: string) {
  const wrist = pos.get(`wrist_${side}`);
  const middle = pos.get(`${side}_middle_1`);
  const index = pos.get(`${side}_index_1`);
  if (!wrist || !middle) {
    return;
  }
  const across = index ? sub(index, middle) : { x: 1, y: 0, z: 0 };
  const forward = sub(middle, wrist);
  let axis = unit(cross(forward, across), { x: 1, y: 0, z: 0 });
  for (const name of FINGERS) {
    const ids = [1, 2, 3, 4]
      .map((step) => `${side}_${name}_${step}`)
      .filter((id) => pos.has(id));
    if (ids.length < 2) {
      continue;
    }
    const angles = name === "thumb" ? [0.6, 0.5] : [0.9, 1.15, 0.9];
    for (let joint = 0; joint < ids.length - 1 && joint < angles.length; joint += 1) {
      const origin = pos.get(ids[joint]);
      const onward = ids.slice(joint + 1);
      if (!origin) {
        continue;
      }
      const sign = curlSign(pos, wrist, origin, onward[0], axis);
      for (const id of onward) {
        const point = pos.get(id);
        if (!point) {
          continue;
        }
        pos.set(id, rotate(point, origin, axis, sign * angles[joint]));
      }
    }
  }
}

function curlSign(pos: Map<string, Pt>, wrist: Pt, origin: Pt, sampleId: string, axis: Pt): number {
  const sample = pos.get(sampleId);
  if (!sample) {
    return 1;
  }
  const plus = rotate(sample, origin, axis, 0.35);
  const minus = rotate(sample, origin, axis, -0.35);
  return distance(plus, wrist) < distance(minus, wrist) ? 1 : -1;
}

function rotate(point: Pt, origin: Pt, axis: Pt, angle: number): Pt {
  const n = unit(axis, { x: 1, y: 0, z: 0 });
  const x = point.x - origin.x;
  const y = point.y - origin.y;
  const z = point.z - origin.z;
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  const dot = x * n.x + y * n.y + z * n.z;
  const cx = n.y * z - n.z * y;
  const cy = n.z * x - n.x * z;
  const cz = n.x * y - n.y * x;
  return {
    x: origin.x + x * cosine + cx * sine + n.x * dot * (1 - cosine),
    y: origin.y + y * cosine + cy * sine + n.y * dot * (1 - cosine),
    z: origin.z + z * cosine + cz * sine + n.z * dot * (1 - cosine),
  };
}

function sub(a: Pt, b: Pt): Pt {
  return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z };
}

function add(origin: Pt, direction: Pt, length: number): Pt {
  return {
    x: origin.x + direction.x * length,
    y: origin.y + direction.y * length,
    z: origin.z + direction.z * length,
  };
}

function cross(a: Pt, b: Pt): Pt {
  return {
    x: a.y * b.z - a.z * b.y,
    y: a.z * b.x - a.x * b.z,
    z: a.x * b.y - a.y * b.x,
  };
}

function unit(value: Pt, fallback: Pt): Pt {
  const length = Math.hypot(value.x, value.y, value.z);
  if (length < 1e-6) {
    return fallback;
  }
  return { x: value.x / length, y: value.y / length, z: value.z / length };
}

function distance(a: Pt, b: Pt): number {
  return Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
}
