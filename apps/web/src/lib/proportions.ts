/** 写真の姿勢を保ったまま、頭身と体つきを別々に替える。 */

import type { Mannequin, MannequinJoint } from "@/lib/api";

export const HEAD_IDS = ["photo", "9", "8", "7", "6", "5", "4"] as const;
export type HeadId = (typeof HEAD_IDS)[number];

export const BUILD_IDS = ["photo", "slim", "standard", "sturdy", "broad_shoulder", "wide_hip"] as const;
export type BuildId = (typeof BUILD_IDS)[number];

type Ratios = {
  head: number;
  neck: number;
  torso: number;
  thigh: number;
  shin: number;
  upperArm: number;
  forearm: number;
  foot: number;
  hand: number;
  shoulder: number;
  hip: number;
};

type BuildFactor = { shoulder: number; hip: number; thickness: number };

const BUILD: Record<Exclude<BuildId, "photo">, BuildFactor> = {
  slim: { shoulder: 0.86, hip: 0.9, thickness: 0.75 },
  standard: { shoulder: 1, hip: 1, thickness: 1 },
  sturdy: { shoulder: 1.1, hip: 1.05, thickness: 1.32 },
  broad_shoulder: { shoulder: 1.24, hip: 0.88, thickness: 1.12 },
  wide_hip: { shoulder: 0.88, hip: 1.22, thickness: 0.96 },
};

const FINGERS = ["thumb", "index", "middle", "ring", "pinky"] as const;

type Pt = { x: number; y: number; z: number };

/** 頭の長さを 1 とした各部。頭から足までを足すと、その頭身になる。 */
const CANON: Record<number, Omit<Ratios, "head">> = {
  4: { neck: 0.2, torso: 1.2, thigh: 0.85, shin: 0.75, upperArm: 0.7, forearm: 0.55, foot: 0.4, hand: 0.45, shoulder: 1.7, hip: 1.45 },
  5: { neck: 0.25, torso: 1.5, thigh: 1.15, shin: 1.1, upperArm: 0.9, forearm: 0.75, foot: 0.45, hand: 0.55, shoulder: 1.8, hip: 1.5 },
  6: { neck: 0.3, torso: 1.75, thigh: 1.5, shin: 1.45, upperArm: 1.1, forearm: 0.9, foot: 0.5, hand: 0.65, shoulder: 1.9, hip: 1.5 },
  7: { neck: 0.33, torso: 2.0, thigh: 1.9, shin: 1.77, upperArm: 1.3, forearm: 1.1, foot: 0.55, hand: 0.72, shoulder: 2.0, hip: 1.55 },
  8: { neck: 0.35, torso: 2.2, thigh: 2.25, shin: 2.2, upperArm: 1.5, forearm: 1.25, foot: 0.6, hand: 0.8, shoulder: 2.05, hip: 1.55 },
  9: { neck: 0.33, torso: 2.3, thigh: 2.75, shin: 2.62, upperArm: 1.6, forearm: 1.35, foot: 0.65, hand: 0.85, shoulder: 1.95, hip: 1.45 },
};

/** 頭身 n。全身の高さを保ったまま、頭を 1/n にし、手足もその頭に合わせる。 */
function ratiosFor(heads: number): Ratios {
  const row = CANON[heads] ?? CANON[8];
  const unit = 1 / heads;
  return {
    head: unit,
    neck: row.neck * unit,
    torso: row.torso * unit,
    thigh: row.thigh * unit,
    shin: row.shin * unit,
    upperArm: row.upperArm * unit,
    forearm: row.forearm * unit,
    foot: row.foot * unit,
    hand: row.hand * unit,
    shoulder: row.shoulder * unit,
    hip: row.hip * unit,
  };
}

export function applyProportion(mannequin: Mannequin, head: HeadId, build: BuildId): Mannequin {
  if (!mannequin.joints.length || !mannequin.head) {
    return mannequin;
  }
  if (head === "photo") {
    if (build === "photo" || build === "standard") {
      return mannequin;
    }
    return scaleBuild(mannequin, BUILD[build]);
  }

  const height = measureHeight(mannequin);
  if (height < 1e-4) {
    return mannequin;
  }
  const ratios = ratiosFor(Number(head));
  const factor = build === "photo" ? photoFactor(mannequin, height) : BUILD[build];
  ratios.shoulder *= factor.shoulder;
  ratios.hip *= factor.hip;

  const orig = new Map(mannequin.joints.map((joint) => [joint.id, joint]));
  const pos = new Map<string, Pt>();
  const pelvis = orig.get("pelvis");
  if (!pelvis) {
    return mannequin;
  }
  pos.set("pelvis", { x: pelvis.x, y: pelvis.y, z: pelvis.z });

  place(orig, pos, "pelvis", "chest", ratios.torso * height);
  place(orig, pos, "pelvis", "hip_l", (ratios.hip * height) / 2);
  place(orig, pos, "pelvis", "hip_r", (ratios.hip * height) / 2);
  place(orig, pos, "chest", "shoulder_l", (ratios.shoulder * height) / 2);
  place(orig, pos, "chest", "shoulder_r", (ratios.shoulder * height) / 2);
  place(orig, pos, "chest", "neck", ratios.neck * height);
  place(orig, pos, "neck", "head", ratios.head * height * 0.45);
  place(orig, pos, "shoulder_l", "elbow_l", ratios.upperArm * height);
  place(orig, pos, "shoulder_r", "elbow_r", ratios.upperArm * height);
  place(orig, pos, "elbow_l", "wrist_l", ratios.forearm * height);
  place(orig, pos, "elbow_r", "wrist_r", ratios.forearm * height);
  place(orig, pos, "hip_l", "knee_l", ratios.thigh * height);
  place(orig, pos, "hip_r", "knee_r", ratios.thigh * height);
  place(orig, pos, "knee_l", "ankle_l", ratios.shin * height);
  place(orig, pos, "knee_r", "ankle_r", ratios.shin * height);
  place(orig, pos, "ankle_l", "foot_l", ratios.foot * height);
  place(orig, pos, "ankle_r", "foot_r", ratios.foot * height);

  for (const side of ["l", "r"] as const) {
    const span = handSpan(orig, side);
    const scale = span > 1e-4 ? (ratios.hand * height) / span : 1;
    for (const name of FINGERS) {
      let previous = `wrist_${side}`;
      for (let step = 1; step <= 4; step += 1) {
        const id = `${side}_${name}_${step}`;
        if (!orig.has(id) || !orig.has(previous)) {
          previous = orig.has(id) ? id : previous;
          continue;
        }
        const old = distance(orig.get(previous)!, orig.get(id)!);
        place(orig, pos, previous, id, old * scale);
        previous = id;
      }
    }
  }

  const oldHead = Math.max(mannequin.head.radius, 1e-4);
  const newHead = (ratios.head * height) / 2;
  const radiusScale = (newHead / oldHead) * factor.thickness;
  return withPositions(mannequin, pos, radiusScale, newHead);
}

function scaleBuild(mannequin: Mannequin, factor: BuildFactor): Mannequin {
  const orig = new Map(mannequin.joints.map((joint) => [joint.id, joint]));
  const pos = new Map<string, Pt>();
  for (const joint of mannequin.joints) {
    pos.set(joint.id, { x: joint.x, y: joint.y, z: joint.z });
  }
  moveWidth(orig, pos, "chest", "shoulder_l", "shoulder_r", factor.shoulder);
  moveWidth(orig, pos, "pelvis", "hip_l", "hip_r", factor.hip);
  return withPositions(mannequin, pos, factor.thickness, mannequin.head?.radius ?? 0);
}

function photoFactor(mannequin: Mannequin, height: number): BuildFactor {
  const byId = new Map(mannequin.joints.map((joint) => [joint.id, joint]));
  const shoulder = span(byId.get("shoulder_l"), byId.get("shoulder_r")) / height;
  const hip = span(byId.get("hip_l"), byId.get("hip_r")) / height;
  return {
    shoulder: clamp(shoulder / 0.22, 0.7, 1.45),
    hip: clamp(hip / 0.17, 0.7, 1.45),
    thickness: 1,
  };
}

function moveWidth(
  orig: Map<string, MannequinJoint>,
  pos: Map<string, Pt>,
  parentId: string,
  leftId: string,
  rightId: string,
  scale: number,
) {
  for (const id of [leftId, rightId]) {
    const parent = pos.get(parentId);
    const from = orig.get(parentId);
    const to = orig.get(id);
    if (!parent || !from || !to) {
      continue;
    }
    const next = {
      x: parent.x + (to.x - from.x) * scale,
      y: parent.y + (to.y - from.y) * scale,
      z: parent.z + (to.z - from.z) * scale,
    };
    const current = pos.get(id) ?? { x: to.x, y: to.y, z: to.z };
    const delta = { x: next.x - current.x, y: next.y - current.y, z: next.z - current.z };
    for (const node of [id, ...descendants(orig, id)]) {
      const point = pos.get(node);
      if (!point) {
        continue;
      }
      pos.set(node, { x: point.x + delta.x, y: point.y + delta.y, z: point.z + delta.z });
    }
  }
}

function descendants(orig: Map<string, MannequinJoint>, rootId: string): string[] {
  const children = new Map<string, string[]>();
  for (const joint of orig.values()) {
    if (!joint.parent) {
      continue;
    }
    const list = children.get(joint.parent) ?? [];
    list.push(joint.id);
    children.set(joint.parent, list);
  }
  const acc: string[] = [];
  const walk = (id: string) => {
    for (const child of children.get(id) ?? []) {
      acc.push(child);
      walk(child);
    }
  };
  walk(rootId);
  return acc;
}

function withPositions(mannequin: Mannequin, pos: Map<string, Pt>, radiusScale: number, headRadius: number): Mannequin {
  return {
    ...mannequin,
    joints: mannequin.joints.map((joint) => {
      const next = pos.get(joint.id);
      if (!next) {
        return joint;
      }
      return { ...joint, x: next.x, y: next.y, z: next.z };
    }),
    bones: mannequin.bones.map((bone) => ({ ...bone, radius: bone.radius * radiusScale })),
    head: mannequin.head ? { ...mannequin.head, radius: headRadius } : null,
  };
}

function measureHeight(mannequin: Mannequin): number {
  const byId = new Map(mannequin.joints.map((joint) => [joint.id, joint]));
  const head = byId.get(mannequin.head?.joint_id ?? "head");
  if (!head || !mannequin.head) {
    return 0;
  }
  let top = head.y - mannequin.head.radius;
  let bottom = head.y;
  for (const id of ["foot_l", "foot_r", "ankle_l", "ankle_r"]) {
    const point = byId.get(id);
    if (point && point.y > bottom) {
      bottom = point.y;
    }
  }
  if (top > bottom) {
    const swap = top;
    top = bottom;
    bottom = swap;
  }
  return Math.max(bottom - top, 0);
}

function place(orig: Map<string, MannequinJoint>, pos: Map<string, Pt>, parentId: string, childId: string, length: number) {
  const parent = pos.get(parentId);
  const from = orig.get(parentId);
  const to = orig.get(childId);
  if (!parent || !from || !to || length <= 0) {
    return;
  }
  let dx = to.x - from.x;
  let dy = to.y - from.y;
  let dz = to.z - from.z;
  let mag = Math.hypot(dx, dy, dz);
  if (mag < 1e-6) {
    dx = 0;
    dy = 1;
    dz = 0;
    mag = 1;
  }
  pos.set(childId, {
    x: parent.x + (dx / mag) * length,
    y: parent.y + (dy / mag) * length,
    z: parent.z + (dz / mag) * length,
  });
}

function handSpan(orig: Map<string, MannequinJoint>, side: string): number {
  const wrist = orig.get(`wrist_${side}`);
  if (!wrist) {
    return 0;
  }
  let reach = 0;
  for (const name of FINGERS) {
    const tip = orig.get(`${side}_${name}_4`);
    if (!tip) {
      continue;
    }
    reach = Math.max(reach, distance(wrist, tip));
  }
  return reach;
}

function span(a: MannequinJoint | undefined, b: MannequinJoint | undefined): number {
  if (!a || !b) {
    return 0.2;
  }
  return distance(a, b);
}

function distance(a: Pt, b: Pt): number {
  return Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
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
