import * as THREE from "three";

import type { Mannequin } from "@/lib/api";

export const DOLL_BODIES = ["x-bot", "ch36"] as const;
export type DollBodyId = (typeof DOLL_BODIES)[number];

const URLS: Record<DollBodyId, string> = {
  "x-bot": "/dolls/x-bot.fbx",
  ch36: "/dolls/ch36.fbx",
};

const loads = new Map<DollBodyId, Promise<THREE.Group>>();

/** Mixamo の体を1回だけ読み、パネルごとに複製する。 */
export function loadDollTemplate(id: DollBodyId): Promise<THREE.Group> {
  const cached = loads.get(id);
  if (cached) {
    return cached;
  }
  const pending = import("three/examples/jsm/loaders/FBXLoader.js").then(
    ({ FBXLoader }) =>
      new Promise<THREE.Group>((resolve, reject) => {
        const loader = new FBXLoader();
        loader.load(URLS[id], (group) => resolve(group), undefined, () => reject(new Error("fbx")));
      }),
  );
  pending.catch(() => {
    loads.delete(id);
  });
  loads.set(id, pending);
  return pending;
}

export async function cloneDoll(template: THREE.Group): Promise<THREE.Group> {
  const { clone } = await import("three/examples/jsm/utils/SkeletonUtils.js");
  const copy = clone(template) as THREE.Group;
  copy.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (!mesh.isMesh || !mesh.geometry) {
      return;
    }
    mesh.geometry = mesh.geometry.clone();
    if (Array.isArray(mesh.material)) {
      mesh.material = mesh.material.map((item) => item.clone());
    } else if (mesh.material) {
      mesh.material = mesh.material.clone();
    }
  });
  return copy;
}

type Stretch = "length" | "width" | "none";
type Thick = "segment" | "head" | "none";
type Twist = "forward" | "up" | "none";

type MixamoLink = {
  bone: THREE.Bone;
  from: string;
  to: string;
  localDir: THREE.Vector3;
  localPole: THREE.Vector3;
  bindQuat: THREE.Quaternion;
  stretch: Stretch;
  thick: Thick;
  twist: Twist;
};

export type MixamoRig = {
  root: THREE.Group;
  hips: THREE.Bone;
  links: MixamoLink[];
  markers: Map<string, THREE.Bone>;
};

const _parentQ = new THREE.Quaternion();
const _target = new THREE.Vector3();
const _targetLocal = new THREE.Vector3();
const _bindDir = new THREE.Vector3();
const _delta = new THREE.Quaternion();
const _axis = new THREE.Vector3();
const _hip = new THREE.Vector3();
const _pelvis = new THREE.Vector3();
const _pole = new THREE.Vector3();
const _guide = new THREE.Vector3();
const _worldQ = new THREE.Quaternion();
const _parentWorld = new THREE.Quaternion();

/** MediaPipe の z は手前ほど小さい。カメラは +Z なので、手前を体の正面に置く。 */
function posePoint(x: number, y: number, z: number, aspect: number): THREE.Vector3 {
  const width = aspect > 0 ? aspect : 1;
  return new THREE.Vector3((x - width / 2) * 2, -(y - 0.5) * 2, -z * 2);
}

function shortName(name: string): string {
  return name.replace(/^mixamorig\d*:?/, "");
}

function indexBones(root: THREE.Object3D): Map<string, THREE.Bone> {
  const map = new Map<string, THREE.Bone>();
  root.traverse((obj) => {
    const bone = obj as THREE.Bone;
    if (!bone.isBone) {
      return;
    }
    const name = shortName(bone.name);
    if (bone.parent && shortName(bone.parent.name) === name) {
      return;
    }
    map.set(name, bone);
  });
  return map;
}

function childAxis(bone: THREE.Bone): THREE.Vector3 {
  const mine = shortName(bone.name);
  for (const child of bone.children) {
    const asBone = child as THREE.Bone;
    if (!asBone.isBone || shortName(child.name) === mine) {
      continue;
    }
    if (child.position.lengthSq() < 1e-8) {
      continue;
    }
    return child.position.clone().normalize();
  }
  return new THREE.Vector3(0, 1, 0);
}

function spanOf(mannequin: Mannequin): number {
  const joints = new Map(mannequin.joints.map((joint) => [joint.id, joint]));
  const aspect = mannequin.aspect && mannequin.aspect > 0 ? mannequin.aspect : 1;
  const headId = mannequin.head?.joint_id || "head";
  const head = joints.get(headId);
  const ankleL = joints.get("ankle_l");
  const ankleR = joints.get("ankle_r");
  const foot = ankleL && ankleR ? (ankleL.y > ankleR.y ? ankleL : ankleR) : ankleL || ankleR;
  if (!head || !foot) {
    return 1.6;
  }
  return Math.max(
    posePoint(head.x, head.y, head.z, aspect).distanceTo(posePoint(foot.x, foot.y, foot.z, aspect)),
    0.4,
  );
}

function modelHeight(root: THREE.Object3D): number {
  root.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(root);
  return Math.max(box.max.y - box.min.y, 1);
}

type LinkSpec = {
  bone: string;
  from: string;
  to: string;
  stretch: Stretch;
  thick: Thick;
  twist: Twist;
};

function fingerSpecs(side: "Left" | "Right", our: "l" | "r"): LinkSpec[] {
  const names = [
    ["Thumb", "thumb"],
    ["Index", "index"],
    ["Middle", "middle"],
    ["Ring", "ring"],
    ["Pinky", "pinky"],
  ] as const;
  const rows: LinkSpec[] = [];
  for (const [mixamo, local] of names) {
    for (let step = 1; step <= 3; step += 1) {
      rows.push({
        bone: `${side}Hand${mixamo}${step}`,
        from: `${our}_${local}_${step}`,
        to: `${our}_${local}_${step + 1}`,
        stretch: "length",
        thick: "segment",
        twist: "none",
      });
    }
  }
  return rows;
}

const BODY_LINKS: LinkSpec[] = [
  { bone: "Spine", from: "pelvis", to: "chest", stretch: "length", thick: "segment", twist: "forward" },
  { bone: "Spine1", from: "pelvis", to: "chest", stretch: "none", thick: "segment", twist: "forward" },
  { bone: "Spine2", from: "pelvis", to: "chest", stretch: "none", thick: "segment", twist: "forward" },
  { bone: "Neck", from: "chest", to: "neck", stretch: "length", thick: "segment", twist: "forward" },
  { bone: "Head", from: "neck", to: "head", stretch: "none", thick: "head", twist: "forward" },
  { bone: "LeftShoulder", from: "chest", to: "shoulder_l", stretch: "length", thick: "segment", twist: "none" },
  { bone: "RightShoulder", from: "chest", to: "shoulder_r", stretch: "length", thick: "segment", twist: "none" },
  { bone: "LeftArm", from: "shoulder_l", to: "elbow_l", stretch: "length", thick: "segment", twist: "none" },
  { bone: "RightArm", from: "shoulder_r", to: "elbow_r", stretch: "length", thick: "segment", twist: "none" },
  { bone: "LeftForeArm", from: "elbow_l", to: "wrist_l", stretch: "length", thick: "segment", twist: "none" },
  { bone: "RightForeArm", from: "elbow_r", to: "wrist_r", stretch: "length", thick: "segment", twist: "none" },
  { bone: "LeftHand", from: "wrist_l", to: "l_middle_1", stretch: "none", thick: "none", twist: "none" },
  { bone: "RightHand", from: "wrist_r", to: "r_middle_1", stretch: "none", thick: "none", twist: "none" },
  ...fingerSpecs("Left", "l"),
  ...fingerSpecs("Right", "r"),
  { bone: "LeftUpLeg", from: "hip_l", to: "knee_l", stretch: "length", thick: "segment", twist: "none" },
  { bone: "RightUpLeg", from: "hip_r", to: "knee_r", stretch: "length", thick: "segment", twist: "none" },
  { bone: "LeftLeg", from: "knee_l", to: "ankle_l", stretch: "length", thick: "segment", twist: "none" },
  { bone: "RightLeg", from: "knee_r", to: "ankle_r", stretch: "length", thick: "segment", twist: "none" },
  { bone: "LeftFoot", from: "ankle_l", to: "foot_l", stretch: "length", thick: "segment", twist: "none" },
  { bone: "RightFoot", from: "ankle_r", to: "foot_r", stretch: "length", thick: "segment", twist: "none" },
];

const MARKERS: [string, string][] = [
  ["shoulder_l", "LeftArm"],
  ["shoulder_r", "RightArm"],
  ["elbow_l", "LeftForeArm"],
  ["elbow_r", "RightForeArm"],
  ["wrist_l", "LeftHand"],
  ["wrist_r", "RightHand"],
  ["hip_l", "LeftUpLeg"],
  ["hip_r", "RightUpLeg"],
  ["knee_l", "LeftLeg"],
  ["knee_r", "RightLeg"],
  ["ankle_l", "LeftFoot"],
  ["ankle_r", "RightFoot"],
];

function pushLink(
  links: MixamoLink[],
  bone: THREE.Bone,
  spec: LinkSpec,
  localDir: THREE.Vector3,
) {
  if (localDir.lengthSq() < 1e-8) {
    return;
  }
  links.push({
    bone,
    from: spec.from,
    to: spec.to,
    localDir: localDir.normalize(),
    localPole: bindPole(bone, spec.twist),
    bindQuat: bone.quaternion.clone(),
    stretch: spec.stretch,
    thick: spec.thick,
    twist: spec.twist,
  });
}

/** バインド時の正面、または上方向を、骨のローカル軸で覚える。 */
function bindPole(bone: THREE.Bone, twist: Twist): THREE.Vector3 {
  if (twist === "none") {
    return new THREE.Vector3();
  }
  bone.updateWorldMatrix(true, false);
  bone.getWorldQuaternion(_worldQ);
  const source = twist === "up" ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(0, 0, 1);
  return source.applyQuaternion(_worldQ.clone().invert());
}

/** 読み込んだ直後の T ポーズを覚え、写真の人形の大きさに合わせる。 */
export function prepareRig(root: THREE.Group, base: Mannequin): MixamoRig | null {
  const bones = indexBones(root);
  const hips = bones.get("Hips");
  if (!hips) {
    return null;
  }
  const height = modelHeight(root);
  const scale = spanOf(base) / height;
  root.scale.setScalar(scale);
  root.updateMatrixWorld(true);
  const links: MixamoLink[] = [];
  const leftLeg = bones.get("LeftUpLeg");
  const rightLeg = bones.get("RightUpLeg");
  if (leftLeg && rightLeg) {
    pushLink(
      links,
      hips,
      { bone: "Hips", from: "hip_r", to: "hip_l", stretch: "width", thick: "none", twist: "up" },
      leftLeg.position.clone().sub(rightLeg.position),
    );
  }
  for (const spec of BODY_LINKS) {
    const bone = bones.get(spec.bone);
    if (!bone) {
      continue;
    }
    pushLink(links, bone, spec, childAxis(bone));
  }
  const markers = new Map<string, THREE.Bone>();
  for (const [jointId, boneName] of MARKERS) {
    const bone = bones.get(boneName);
    if (bone) {
      markers.set(jointId, bone);
    }
  }
  return { root, hips, links, markers };
}

function jointMap(mannequin: Mannequin) {
  return new Map(mannequin.joints.map((joint) => [joint.id, joint]));
}

function distance(mannequin: Mannequin, from: string, to: string): number {
  const joints = jointMap(mannequin);
  const a = joints.get(from);
  const b = joints.get(to);
  if (!a || !b) {
    return 0;
  }
  const aspect = mannequin.aspect && mannequin.aspect > 0 ? mannequin.aspect : 1;
  return posePoint(a.x, a.y, a.z, aspect).distanceTo(posePoint(b.x, b.y, b.z, aspect));
}

function segmentRadius(mannequin: Mannequin, from: string, to: string): number {
  const bone = mannequin.bones.find((item) => item.start === from && item.end === to);
  return bone?.radius ?? 0;
}

function clampRatio(value: number): number {
  if (!Number.isFinite(value) || value <= 0) {
    return 1;
  }
  return THREE.MathUtils.clamp(value, 0.35, 2.6);
}

function parentScale(bone: THREE.Object3D): { along: number; thick: number } {
  let current = bone.parent;
  while (current) {
    const saved = current.userData.mixamoScale as { along: number; thick: number } | undefined;
    if (saved) {
      return saved;
    }
    current = current.parent;
  }
  return { along: 1, thick: 1 };
}

function aimBone(
  bone: THREE.Bone,
  targetWorld: THREE.Vector3,
  bindQuat: THREE.Quaternion,
  localDir: THREE.Vector3,
  localPole: THREE.Vector3 | null,
  guideWorld: THREE.Vector3 | null,
) {
  const parent = bone.parent;
  if (!parent || targetWorld.lengthSq() < 1e-10) {
    return;
  }
  parent.updateWorldMatrix(true, false);
  parent.getWorldQuaternion(_parentQ);
  _targetLocal.copy(targetWorld).normalize().applyQuaternion(_parentQ.invert());
  _bindDir.copy(localDir).applyQuaternion(bindQuat).normalize();
  const dot = _bindDir.dot(_targetLocal);
  if (dot > 0.9995) {
    bone.quaternion.copy(bindQuat);
  } else {
    if (dot < -0.9995) {
      _axis.set(1, 0, 0);
      if (Math.abs(_bindDir.x) > 0.9) {
        _axis.set(0, 1, 0);
      }
      _delta.setFromAxisAngle(_axis, Math.PI);
    } else {
      _delta.setFromUnitVectors(_bindDir, _targetLocal);
    }
    bone.quaternion.copy(_delta).multiply(bindQuat);
  }
  if (!localPole || !guideWorld || guideWorld.lengthSq() < 1e-8) {
    return;
  }
  bone.updateWorldMatrix(true, false);
  bone.getWorldQuaternion(_worldQ);
  _axis.copy(localDir).applyQuaternion(_worldQ);
  if (_axis.lengthSq() < 1e-8) {
    return;
  }
  _axis.normalize();
  _pole.copy(localPole).applyQuaternion(_worldQ).addScaledVector(_axis, -_pole.dot(_axis));
  _guide.copy(guideWorld).addScaledVector(_axis, -_guide.dot(_axis));
  if (_pole.lengthSq() < 1e-8 || _guide.lengthSq() < 1e-8) {
    return;
  }
  _pole.normalize();
  _guide.normalize();
  if (_pole.dot(_guide) > 0.9995) {
    return;
  }
  _delta.setFromUnitVectors(_pole, _guide);
  parent.getWorldQuaternion(_parentWorld);
  _delta.multiply(_worldQ);
  bone.quaternion.copy(_parentWorld.invert()).multiply(_delta);
}

function safeScale(value: number): number {
  if (!Number.isFinite(value) || value <= 0) {
    return 1;
  }
  return THREE.MathUtils.clamp(value, 0.2, 4);
}

function applyScale(bone: THREE.Bone, localDir: THREE.Vector3, along: number, thick: number) {
  const ax = Math.abs(localDir.x);
  const ay = Math.abs(localDir.y);
  const az = Math.abs(localDir.z);
  const scale = new THREE.Vector3(safeScale(thick), safeScale(thick), safeScale(thick));
  along = safeScale(along);
  if (ay >= ax && ay >= az) {
    scale.y = along;
  } else if (ax >= az) {
    scale.x = along;
  } else {
    scale.z = along;
  }
  bone.scale.copy(scale);
}

function setOpacity(root: THREE.Object3D, active: boolean) {
  root.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (!mesh.isMesh) {
      return;
    }
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const material of materials) {
      material.transparent = !active;
      material.opacity = active ? 1 : 0.55;
      material.depthWrite = active;
    }
  });
}

const _forward = new THREE.Vector3();
const _up = new THREE.Vector3();

/** 腰の左右と胴の上方向から、お腹と顔が向く側を決める。 */
function poseFacing(joints: Map<string, { x: number; y: number; z: number }>, aspect: number) {
  const hipL = joints.get("hip_l");
  const hipR = joints.get("hip_r");
  const chest = joints.get("chest");
  const pelvis = joints.get("pelvis");
  _forward.set(0, 0, 1);
  _up.set(0, 1, 0);
  if (!hipL || !hipR || !chest || !pelvis) {
    return;
  }
  const across = posePoint(hipL.x, hipL.y, hipL.z, aspect).sub(posePoint(hipR.x, hipR.y, hipR.z, aspect));
  _up.copy(posePoint(chest.x, chest.y, chest.z, aspect)).sub(posePoint(pelvis.x, pelvis.y, pelvis.z, aspect));
  _forward.crossVectors(across, _up);
  if (_forward.lengthSq() < 1e-8) {
    _forward.set(0, 0, 1);
  } else {
    _forward.normalize();
  }
}

/** ポーズ済みの関節方向と、頭身・体つきの長さを Mixamo の骨へ渡す。 */
export function applyMixamoPose(rig: MixamoRig, base: Mannequin, posed: Mannequin, active: boolean) {
  const joints = jointMap(posed);
  const aspect = posed.aspect && posed.aspect > 0 ? posed.aspect : 1;
  poseFacing(joints, aspect);
  for (const link of rig.links) {
    const start = joints.get(link.from);
    const end = joints.get(link.to);
    if (!start || !end) {
      link.bone.quaternion.copy(link.bindQuat);
      link.bone.scale.set(1, 1, 1);
      continue;
    }
    _target.copy(posePoint(end.x, end.y, end.z, aspect)).sub(posePoint(start.x, start.y, start.z, aspect));
    const guide = link.twist === "forward" ? _forward : link.twist === "up" ? _up : null;
    aimBone(link.bone, _target, link.bindQuat, link.localDir, guide ? link.localPole : null, guide);
    const baseLen = distance(base, link.from, link.to);
    const posedLen = _target.length();
    const lengthRatio = clampRatio(baseLen > 1e-6 ? posedLen / baseLen : 1);
    let thick = 1;
    if (link.thick === "head" && base.head && posed.head && base.head.radius > 1e-6) {
      thick = clampRatio(posed.head.radius / base.head.radius);
    } else if (link.thick === "segment") {
      const baseRadius = segmentRadius(base, link.from, link.to);
      const posedRadius = segmentRadius(posed, link.from, link.to);
      thick = clampRatio(baseRadius > 1e-6 ? posedRadius / baseRadius : 1);
    }
    const inherited = parentScale(link.bone);
    if (link.thick === "head") {
      link.bone.scale.set(
        safeScale(thick / inherited.thick),
        safeScale(thick / inherited.along),
        safeScale(thick / inherited.thick),
      );
      link.bone.userData.mixamoScale = { along: thick, thick };
    } else if (link.stretch === "width") {
      link.bone.scale.set(safeScale(lengthRatio), 1, 1);
      link.bone.userData.mixamoScale = { along: 1, thick: 1 };
    } else {
      const desiredAlong = link.stretch === "length" ? lengthRatio : inherited.along;
      const desiredThick = link.thick === "segment" ? thick : inherited.thick;
      applyScale(link.bone, link.localDir, desiredAlong / inherited.along, desiredThick / inherited.thick);
      link.bone.userData.mixamoScale = { along: desiredAlong, thick: desiredThick };
    }
    link.bone.updateMatrixWorld(true);
  }
  const pelvis = joints.get("pelvis");
  if (pelvis) {
    rig.root.updateMatrixWorld(true);
    rig.hips.getWorldPosition(_hip);
    _pelvis.copy(posePoint(pelvis.x, pelvis.y, pelvis.z, aspect));
    rig.root.position.add(_pelvis.sub(_hip));
  }
  setOpacity(rig.root, active);
}

export function markerPosition(rig: MixamoRig, jointId: string, target: THREE.Vector3): boolean {
  const bone = rig.markers.get(jointId);
  if (!bone) {
    return false;
  }
  bone.getWorldPosition(target);
  return true;
}

export function disposeDoll(root: THREE.Object3D) {
  root.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (!mesh.isMesh) {
      return;
    }
    mesh.geometry?.dispose();
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const material of materials) {
      material.dispose();
    }
  });
}
