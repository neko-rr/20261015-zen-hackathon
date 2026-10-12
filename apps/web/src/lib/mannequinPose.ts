/** サーバが組んだ人形に、画面で付けた曲げを足す。2D と 3D で同じ計算。 */

import type { Mannequin, MannequinJoint } from "@/lib/api";

export const EMPTY_MANNEQUIN: Mannequin = { joints: [], bones: [], head: null };

const BEND_LIMIT = 2.6;

export function clampBend(angle: number): number {
  if (Number.isNaN(angle)) {
    return 0;
  }
  if (angle < -BEND_LIMIT) {
    return -BEND_LIMIT;
  }
  if (angle > BEND_LIMIT) {
    return BEND_LIMIT;
  }
  return angle;
}

type Vec3 = { x: number; y: number; z: number };

export function applyBends(mannequin: Mannequin, bends: Record<string, number>): Mannequin {
  if (!mannequin.joints.length) {
    return mannequin;
  }
  const active = Object.values(bends).some((value) => Math.abs(value) > 1e-6);
  if (!active) {
    return mannequin;
  }

  const byId = new Map(mannequin.joints.map((joint) => [joint.id, joint]));
  const children = new Map<string, string[]>();
  const roots: string[] = [];
  for (const joint of mannequin.joints) {
    if (!joint.parent || !byId.has(joint.parent)) {
      roots.push(joint.id);
      continue;
    }
    const list = children.get(joint.parent) ?? [];
    list.push(joint.id);
    children.set(joint.parent, list);
  }

  const pos = new Map<string, Vec3>();
  for (const joint of mannequin.joints) {
    pos.set(joint.id, { x: joint.x, y: joint.y, z: joint.z });
  }

  const descendants = new Map<string, string[]>();
  const collect = (id: string): string[] => {
    const cached = descendants.get(id);
    if (cached) {
      return cached;
    }
    const acc: string[] = [];
    for (const child of children.get(id) ?? []) {
      acc.push(child, ...collect(child));
    }
    descendants.set(id, acc);
    return acc;
  };

  const walk = (id: string, parentRot: number[]) => {
    const joint = byId.get(id);
    if (!joint) {
      return;
    }
    const angle = bends[id] ?? 0;
    const hinge = applyMat(parentRot, joint.hinge);
    let next = parentRot;
    if (Math.abs(angle) > 1e-8) {
      const origin = pos.get(id);
      if (origin) {
        for (const desc of collect(id)) {
          const current = pos.get(desc);
          if (current) {
            pos.set(desc, rotateAround(current, origin, hinge, angle));
          }
        }
      }
      next = mul(axisAngle(hinge, angle), parentRot);
    }
    for (const child of children.get(id) ?? []) {
      walk(child, next);
    }
  };

  for (const root of roots) {
    walk(root, [1, 0, 0, 0, 1, 0, 0, 0, 1]);
  }

  return {
    ...mannequin,
    joints: mannequin.joints.map((joint) => {
      const next = pos.get(joint.id) ?? joint;
      return { ...joint, x: next.x, y: next.y, z: next.z };
    }),
  };
}

export function posedJointMap(joints: MannequinJoint[]): Map<string, MannequinJoint> {
  return new Map(joints.map((joint) => [joint.id, joint]));
}

function mul(a: number[], b: number[]): number[] {
  const out = [0, 0, 0, 0, 0, 0, 0, 0, 0];
  for (let row = 0; row < 3; row += 1) {
    for (let col = 0; col < 3; col += 1) {
      out[row * 3 + col] =
        a[row * 3] * b[col] + a[row * 3 + 1] * b[3 + col] + a[row * 3 + 2] * b[6 + col];
    }
  }
  return out;
}

function applyMat(matrix: number[], vector: [number, number, number]): [number, number, number] {
  return [
    matrix[0] * vector[0] + matrix[1] * vector[1] + matrix[2] * vector[2],
    matrix[3] * vector[0] + matrix[4] * vector[1] + matrix[5] * vector[2],
    matrix[6] * vector[0] + matrix[7] * vector[1] + matrix[8] * vector[2],
  ];
}

function axisAngle(axis: [number, number, number], angle: number): number[] {
  const length = Math.hypot(axis[0], axis[1], axis[2]) || 1;
  const x = axis[0] / length;
  const y = axis[1] / length;
  const z = axis[2] / length;
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  const tilt = 1 - cosine;
  return [
    tilt * x * x + cosine,
    tilt * x * y - sine * z,
    tilt * x * z + sine * y,
    tilt * x * y + sine * z,
    tilt * y * y + cosine,
    tilt * y * z - sine * x,
    tilt * x * z - sine * y,
    tilt * y * z + sine * x,
    tilt * z * z + cosine,
  ];
}

function rotateAround(point: Vec3, origin: Vec3, axis: [number, number, number], angle: number): Vec3 {
  const turned = applyMat(axisAngle(axis, angle), [
    point.x - origin.x,
    point.y - origin.y,
    point.z - origin.z,
  ]);
  return { x: origin.x + turned[0], y: origin.y + turned[1], z: origin.z + turned[2] };
}

const HINGE_CHILD: Record<string, string> = {
  elbow_l: "wrist_l",
  elbow_r: "wrist_r",
  knee_l: "ankle_l",
  knee_r: "ankle_r",
};

/** 肘と膝は、写真の曲がりから逆側へ大きく折らない。 */
export function limitHingeBend(
  base: Mannequin,
  bends: Record<string, number>,
  jointId: string,
  next: number,
): number {
  const childId = HINGE_CHILD[jointId];
  if (!childId) {
    return clampBend(next);
  }
  const sign = flexionSign(base, jointId, childId);
  const flexed = sign * 2.2;
  const extended = -sign * 0.4;
  const min = Math.min(flexed, extended);
  const max = Math.max(flexed, extended);
  const clamped = clampBend(Math.min(max, Math.max(min, next)));
  const current = bends[jointId] ?? 0;
  let best = current;
  const steps = 10;
  for (let step = 1; step <= steps; step += 1) {
    const angle = current + ((clamped - current) * step) / steps;
    const posed = applyBends(base, { ...bends, [jointId]: angle });
    if (!hingeStillFlexed(base, posed, jointId, childId)) {
      break;
    }
    best = angle;
  }
  return best;
}

function flexionSign(base: Mannequin, jointId: string, childId: string): number {
  const rest = limbSpan(base, jointId, childId);
  const plus = limbSpan(applyBends(base, { [jointId]: 0.25 }), jointId, childId);
  const minus = limbSpan(applyBends(base, { [jointId]: -0.25 }), jointId, childId);
  if (plus < rest && plus <= minus) {
    return 1;
  }
  if (minus < rest) {
    return -1;
  }
  return 1;
}

function hingeStillFlexed(rest: Mannequin, posed: Mannequin, jointId: string, childId: string): boolean {
  const before = segmentCross(rest, jointId, childId);
  const after = segmentCross(posed, jointId, childId);
  if (!before || !after) {
    return true;
  }
  const align = dot(after.along, after.out) / (lengthOf(after.along) * lengthOf(after.out) || 1);
  const restAlign = dot(before.along, before.out) / (lengthOf(before.along) * lengthOf(before.out) || 1);
  if (align < -0.88 && align < restAlign - 0.02) {
    return false;
  }
  if (limbSpan(posed, jointId, childId) > limbSpan(rest, jointId, childId) * 1.02) {
    return false;
  }
  if (lengthOf(before.cross) < 1e-4) {
    return true;
  }
  return dot(before.cross, after.cross) >= 0;
}

function limbSpan(mannequin: Mannequin, jointId: string, childId: string): number {
  const byId = posedJointMap(mannequin.joints);
  const joint = byId.get(jointId);
  const child = byId.get(childId);
  const parent = joint?.parent ? byId.get(joint.parent) : undefined;
  if (!parent || !child) {
    return 0;
  }
  return Math.hypot(child.x - parent.x, child.y - parent.y, child.z - parent.z);
}

function segmentCross(mannequin: Mannequin, jointId: string, childId: string) {
  const byId = posedJointMap(mannequin.joints);
  const joint = byId.get(jointId);
  const child = byId.get(childId);
  const parent = joint?.parent ? byId.get(joint.parent) : undefined;
  if (!joint || !child || !parent) {
    return null;
  }
  const along = { x: joint.x - parent.x, y: joint.y - parent.y, z: joint.z - parent.z };
  const out = { x: child.x - joint.x, y: child.y - joint.y, z: child.z - joint.z };
  return {
    along,
    out,
    cross: {
      x: along.y * out.z - along.z * out.y,
      y: along.z * out.x - along.x * out.z,
      z: along.x * out.y - along.y * out.x,
    },
  };
}

function dot(a: Vec3, b: Vec3): number {
  return a.x * b.x + a.y * b.y + a.z * b.z;
}

function lengthOf(value: Vec3): number {
  return Math.hypot(value.x, value.y, value.z);
}

const TWIST_LIMIT = 1.22;

export function clampTwist(angle: number): number {
  if (Number.isNaN(angle)) {
    return 0;
  }
  if (angle < -TWIST_LIMIT) {
    return -TWIST_LIMIT;
  }
  if (angle > TWIST_LIMIT) {
    return TWIST_LIMIT;
  }
  return angle;
}

/** 肩と腰を、背骨を軸に別々に回す。曲げた後の姿勢に足す。 */
export function applyTwist(mannequin: Mannequin, upper: number, lower: number): Mannequin {
  const upperAngle = clampTwist(upper);
  const lowerAngle = clampTwist(lower);
  if (!mannequin.joints.length || (Math.abs(upperAngle) < 1e-6 && Math.abs(lowerAngle) < 1e-6)) {
    return mannequin;
  }
  const byId = new Map(mannequin.joints.map((joint) => [joint.id, joint]));
  const pelvis = byId.get("pelvis");
  const chest = byId.get("chest");
  if (!pelvis || !chest) {
    return mannequin;
  }
  let axis: [number, number, number] = [chest.x - pelvis.x, chest.y - pelvis.y, chest.z - pelvis.z];
  if (Math.hypot(axis[0], axis[1], axis[2]) < 1e-5) {
    axis = [0, -1, 0];
  }
  const pivot = { x: pelvis.x, y: pelvis.y, z: pelvis.z };
  const pos = new Map<string, Vec3>();
  for (const joint of mannequin.joints) {
    pos.set(joint.id, { x: joint.x, y: joint.y, z: joint.z });
  }
  const spin = (ids: string[], angle: number) => {
    if (Math.abs(angle) < 1e-6) {
      return;
    }
    for (const id of ids) {
      const point = pos.get(id);
      if (!point) {
        continue;
      }
      pos.set(id, rotateAround(point, pivot, axis, angle));
    }
  };
  spin(subtreeIds(byId, "chest").filter((id) => id !== "chest"), upperAngle);
  spin([...subtreeIds(byId, "hip_l"), ...subtreeIds(byId, "hip_r")], lowerAngle);
  return {
    ...mannequin,
    joints: mannequin.joints.map((joint) => {
      const next = pos.get(joint.id);
      if (!next) {
        return joint;
      }
      return { ...joint, x: next.x, y: next.y, z: next.z };
    }),
  };
}

/** 左右を入れ替える。曲がり方はそのまま、画面の向きだけ逆にする。 */
export function applyMirror(mannequin: Mannequin, enabled: boolean): Mannequin {
  if (!enabled || !mannequin.joints.length) {
    return mannequin;
  }
  const pelvis = mannequin.joints.find((joint) => joint.id === "pelvis");
  const mid =
    pelvis?.x ?? mannequin.joints.reduce((sum, joint) => sum + joint.x, 0) / mannequin.joints.length;
  return {
    ...mannequin,
    joints: mannequin.joints.map((joint) => ({
      ...joint,
      x: mid * 2 - joint.x,
      hinge: [-joint.hinge[0], joint.hinge[1], joint.hinge[2]],
    })),
  };
}

function subtreeIds(byId: Map<string, MannequinJoint>, rootId: string): string[] {
  const children = new Map<string, string[]>();
  for (const joint of byId.values()) {
    if (!joint.parent) {
      continue;
    }
    const list = children.get(joint.parent) ?? [];
    list.push(joint.id);
    children.set(joint.parent, list);
  }
  const acc: string[] = [];
  const walk = (id: string) => {
    acc.push(id);
    for (const child of children.get(id) ?? []) {
      walk(child);
    }
  };
  if (byId.has(rootId)) {
    walk(rootId);
  }
  return acc;
}
