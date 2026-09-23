/** デッサン用の簡略人体。顔の細部・指は描かない。 */

import type { PoseData, PoseLandmark } from "@/lib/api";

export type FigurePart = "torso" | "limb" | "thin" | "neck";

export type FigureBone = {
  id: string;
  part: FigurePart;
  x1: number;
  y1: number;
  z1: number;
  x2: number;
  y2: number;
  z2: number;
};

export type FigurePoint = {
  x: number;
  y: number;
  z: number;
};

export type Figure = {
  bones: FigureBone[];
  head: (FigurePoint & { radius: number }) | null;
  joints: FigurePoint[];
};

type Pt = FigurePoint;

const FACE = [0, 2, 5, 7, 8];
const BODY = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28];

function byIndex(landmarks: PoseLandmark[]): Map<number, PoseLandmark> {
  const map = new Map<number, PoseLandmark>();
  for (const item of landmarks) {
    map.set(item.index, item);
  }
  return map;
}

function xy(a: Pt, b: Pt): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function mid(a: Pt, b: Pt): Pt {
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, z: (a.z + b.z) / 2 };
}

function clamp01(value: number): number {
  if (value < 0) {
    return 0;
  }
  if (value > 1) {
    return 1;
  }
  return value;
}

/** MediaPipe の z は画像座標と単位が違うので、肩幅に対して浅く正規化する。 */
function scaledPoints(landmarks: PoseLandmark[]): Map<number, Pt> {
  const raw = byIndex(landmarks);
  const used = [...FACE, ...BODY].filter((index) => raw.has(index));
  const points = used.map((index) => raw.get(index)!);
  const left = raw.get(11);
  const right = raw.get(12);
  const shoulder =
    left && right
      ? Math.hypot(left.x - right.x, left.y - right.y)
      : 0.18;
  const zs = points.map((item) => item.z);
  const zMid = zs.length ? zs.reduce((sum, value) => sum + value, 0) / zs.length : 0;
  const zReach = Math.max(...zs.map((value) => Math.abs(value - zMid)), 0.001);
  const zScale = (shoulder * 0.35) / zReach;

  const map = new Map<number, Pt>();
  for (const item of points) {
    map.set(item.index, {
      x: item.x,
      y: item.y,
      z: (item.z - zMid) * zScale,
    });
  }
  return map;
}

function bone(
  id: string,
  part: FigurePart,
  a: Pt | undefined,
  b: Pt | undefined,
): FigureBone | null {
  if (!a || !b) {
    return null;
  }
  if (xy(a, b) < 0.01) {
    return null;
  }
  return { id, part, x1: a.x, y1: a.y, z1: a.z, x2: b.x, y2: b.y, z2: b.z };
}

export function buildFigure(pose: PoseData): Figure {
  const pts = scaledPoints(pose.landmarks ?? []);
  const bones: FigureBone[] = [];
  const push = (item: FigureBone | null) => {
    if (item) {
      bones.push(item);
    }
  };

  const ls = pts.get(11);
  const rs = pts.get(12);
  const lh = pts.get(23);
  const rh = pts.get(24);
  const shoulderMid = ls && rs ? mid(ls, rs) : undefined;
  const hipMid = lh && rh ? mid(lh, rh) : undefined;

  const face = FACE.map((index) => pts.get(index)).filter((item): item is Pt => Boolean(item));
  let head: Figure["head"] = null;
  if (face.length) {
    const center = face.reduce(
      (acc, item) => ({ x: acc.x + item.x, y: acc.y + item.y, z: acc.z + item.z }),
      { x: 0, y: 0, z: 0 },
    );
    const count = face.length;
    const ears = pts.get(7) && pts.get(8) ? xy(pts.get(7)!, pts.get(8)!) : 0;
    const shoulderSpan = ls && rs ? xy(ls, rs) : 0.2;
    const radius = Math.min(Math.max(ears * 0.55, 0.02), shoulderSpan * 0.42);
    head = {
      x: clamp01(center.x / count),
      y: clamp01(center.y / count),
      z: center.z / count,
      radius,
    };
  }

  if (head && shoulderMid) {
    const neckStart = {
      x: head.x,
      y: clamp01(head.y + head.radius * 0.85),
      z: head.z,
    };
    push(bone("neck", "neck", neckStart, shoulderMid));
  }

  push(bone("shoulders", "limb", ls, rs));
  push(bone("hips", "limb", lh, rh));
  push(bone("torso", "torso", shoulderMid, hipMid));
  push(bone("lua", "limb", ls, pts.get(13)));
  push(bone("rua", "limb", rs, pts.get(14)));
  push(bone("lfa", "thin", pts.get(13), pts.get(15)));
  push(bone("rfa", "thin", pts.get(14), pts.get(16)));
  push(bone("lth", "limb", lh, pts.get(25)));
  push(bone("rth", "limb", rh, pts.get(26)));
  push(bone("lsh", "thin", pts.get(25), pts.get(27)));
  push(bone("rsh", "thin", pts.get(26), pts.get(28)));

  const joints: FigurePoint[] = [];
  for (const index of BODY) {
    const point = pts.get(index);
    if (point) {
      joints.push(point);
    }
  }

  return { bones, head, joints };
}
