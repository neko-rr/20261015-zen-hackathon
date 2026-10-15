"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

import type { Mannequin } from "@/lib/api";
import type { GuideLine } from "@/lib/figureGuides";
import { clampBend } from "@/lib/mannequinPose";
import {
  applyMixamoPose,
  cloneDoll,
  disposeDoll,
  loadDollTemplate,
  markerPosition,
  prepareRig,
  type DollBodyId,
  type MixamoRig,
} from "@/lib/mixamoBody";
import { MannequinLegend } from "@/components/MannequinOverlay";

type ViewLabels = {
  front: string;
  threeQuarter: string;
  side: string;
  back: string;
};

export type CameraId = keyof ViewLabels;

export type DollView = {
  id: string;
  mannequin: Mannequin;
  posed: Mannequin;
  tone: number;
  active: boolean;
};

type Props = {
  figures: DollView[];
  hint: string;
  observedLabel: string;
  inferredLabel: string;
  camera: CameraId;
  guides: GuideLine[];
  photoFlip: boolean;
  bends: Record<string, number>;
  onBend: (id: string, angle: number) => void;
  onSelect: (id: string) => void;
  bodyId: DollBodyId;
  bodyLoading: string;
  bodyFailed: string;
};

const CAMERA_VIEWS: Record<keyof ViewLabels, [number, number, number]> = {
  front: [0, 0.2, 3.5],
  threeQuarter: [2.3, 0.45, 2.5],
  side: [3.5, 0.2, 0.15],
  back: [0, 0.2, -3.5],
};

const TONES = [0xc4a574, 0xd07a6a, 0x6a9a72, 0x7a8ec4];
const INFERRED = 0x3aa0e8;

function toneColor(tone: number): number {
  const index = ((tone % TONES.length) + TONES.length) % TONES.length;
  return TONES[index];
}

function paintActive(mesh: THREE.Mesh, active: boolean) {
  const material = mesh.material;
  if (Array.isArray(material) || !(material instanceof THREE.MeshStandardMaterial)) {
    return;
  }
  material.opacity = active ? 1 : 0.72;
  material.transparent = !active;
  material.depthWrite = active;
}
const DRAG_PER_PIXEL = 0.012;

/** MediaPipe の z は手前ほど小さい。3D のカメラは +Z なので符号を反転する。 */
function toVec3(x: number, y: number, z: number, aspect: number): THREE.Vector3 {
  const width = aspect > 0 ? aspect : 1;
  return new THREE.Vector3((x - width / 2) * 2, -(y - 0.5) * 2, -z * 2);
}

const FLESH: Record<string, number[]> = {
  upper_arm: [0.95, 1.2, 1.35, 1.05, 0.78],
  forearm: [0.78, 0.72, 0.64, 0.52],
  thigh: [1.15, 1.45, 1.4, 1.05, 0.78],
  shin: [0.78, 0.7, 0.58, 0.46],
  neck: [0.72, 0.58, 0.66],
};

const DRAG_JOINTS = new Set([
  "shoulder_l",
  "shoulder_r",
  "elbow_l",
  "elbow_r",
  "wrist_l",
  "wrist_r",
  "hip_l",
  "hip_r",
  "knee_l",
  "knee_r",
  "ankle_l",
  "ankle_r",
]);

function shapeFor(part: string, id: string): string {
  if (part === "clavicle") {
    return "shoulder";
  }
  if (part === "foot") {
    return "foot";
  }
  if (part === "torso") {
    return "chest";
  }
  if (part === "pelvis") {
    return "hip";
  }
  if (part === "finger" || part === "thumb") {
    return /_(index|middle|ring|pinky)_1$/.test(id) ? "palm" : "finger";
  }
  return "flesh";
}

/** 断面を積んで、胴や腰のボリュームにする。ローカル Y が長さ。 */
function createLoft(rings: { y: number; w: number; d: number }[]): THREE.BufferGeometry {
  const sides = 10;
  const rows = rings.map((ring) => {
    const pts: [number, number, number][] = [];
    for (let i = 0; i < sides; i += 1) {
      const angle = (i / sides) * Math.PI * 2;
      pts.push([(Math.cos(angle) * ring.w) / 2, ring.y, (Math.sin(angle) * ring.d) / 2]);
    }
    return pts;
  });
  const positions: number[] = [];
  const push = (p: [number, number, number]) => positions.push(p[0], p[1], p[2]);
  for (let row = 0; row < rows.length - 1; row += 1) {
    for (let i = 0; i < sides; i += 1) {
      const next = (i + 1) % sides;
      const a = rows[row][i];
      const b = rows[row][next];
      const c = rows[row + 1][next];
      const d = rows[row + 1][i];
      push(a);
      push(b);
      push(c);
      push(a);
      push(c);
      push(d);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.computeVertexNormals();
  return geometry;
}

function createFlesh(profile: number[]): THREE.BufferGeometry {
  const points = profile.map(
    (radius, index) => new THREE.Vector2(Math.max(radius, 0.05), -0.5 + index / (profile.length - 1)),
  );
  return new THREE.LatheGeometry(points, 14);
}

function drawGuides(group: THREE.Group, lines: GuideLine[], aspect: number) {
  clearGuideGroup(group);
  for (const line of lines) {
    const geometry = new THREE.BufferGeometry().setFromPoints([
      toVec3(line.x1, line.y1, line.z1, aspect),
      toVec3(line.x2, line.y2, line.z2, aspect),
    ]);
    const material = new THREE.LineBasicMaterial({
      color: line.kind === "balance" ? 0xe07070 : 0xffe08a,
    });
    group.add(new THREE.Line(geometry, material));
    if (line.label) {
      group.add(guideLabel(line.label, toVec3(line.x2, line.y2, line.z2, aspect)));
    }
  }
}

function guideLabel(label: string, position: THREE.Vector3): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 64;
  canvas.height = 64;
  const context = canvas.getContext("2d");
  if (context) {
    context.fillStyle = "#ffe08a";
    context.font = "42px sans-serif";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(label, 32, 34);
  }
  const material = new THREE.SpriteMaterial({
    map: new THREE.CanvasTexture(canvas),
    transparent: true,
    depthTest: false,
  });
  const sprite = new THREE.Sprite(material);
  sprite.position.copy(position);
  sprite.scale.set(0.1, 0.1, 1);
  return sprite;
}

function clearGuideGroup(group: THREE.Group | undefined) {
  if (!group) {
    return;
  }
  for (const child of [...group.children]) {
    group.remove(child);
    if (child instanceof THREE.Line) {
      child.geometry.dispose();
      const material = child.material;
      if (!Array.isArray(material)) {
        material.dispose();
      }
    }
    if (child instanceof THREE.Sprite) {
      const material = child.material;
      material.map?.dispose();
      material.dispose();
    }
  }
}

function lookFrom(
  rig: { camera: THREE.PerspectiveCamera; controls: OrbitControls } | null,
  id: keyof ViewLabels,
  flipped: boolean,
) {
  if (!rig) {
    return;
  }
  const [x, y, z] = CAMERA_VIEWS[id];
  rig.camera.position.set(flipped ? -x : x, y, z);
  rig.controls.target.set(0, 0.1, 0);
  rig.controls.update();
}

/** 足の甲。足首側が高く、爪先側が低い楔。ローカル Y が長さ。 */
function createFootWedge(): THREE.BufferGeometry {
  const y0 = -0.5;
  const y1 = 0.5;
  const heelW = 0.42;
  const toeW = 0.5;
  const sole = -0.32;
  const instepHeel = 0.58;
  const instepToe = 0.1;
  const v: [number, number, number][] = [
    [-heelW, y0, sole],
    [heelW, y0, sole],
    [-heelW, y0, instepHeel],
    [heelW, y0, instepHeel],
    [-toeW, y1, sole],
    [toeW, y1, sole],
    [-toeW, y1, instepToe],
    [toeW, y1, instepToe],
  ];
  const faces = [
    [0, 1, 3, 2],
    [4, 6, 7, 5],
    [0, 4, 5, 1],
    [2, 3, 7, 6],
    [0, 2, 6, 4],
    [1, 5, 7, 3],
  ];
  const positions: number[] = [];
  for (const face of faces) {
    for (const index of [face[0], face[1], face[2], face[0], face[2], face[3]]) {
      positions.push(...v[index]);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.computeVertexNormals();
  return geometry;
}

function orientMesh(mesh: THREE.Mesh, direction: THREE.Vector3, flat: boolean, side?: THREE.Vector3) {
  if (direction.lengthSq() < 1e-8) {
    return;
  }
  const yAxis = direction.clone().normalize();
  if (!flat) {
    mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), yAxis);
    return;
  }
  const xAxis = side ? side.clone() : new THREE.Vector3().crossVectors(new THREE.Vector3(0, 1, 0), yAxis);
  if (side) {
    xAxis.addScaledVector(yAxis, -xAxis.dot(yAxis));
  }
  if (xAxis.lengthSq() < 1e-8) {
    xAxis.crossVectors(new THREE.Vector3(0, 1, 0), yAxis);
  }
  if (xAxis.lengthSq() < 1e-8) {
    xAxis.crossVectors(new THREE.Vector3(1, 0, 0), yAxis);
  }
  xAxis.normalize();
  const zAxis = new THREE.Vector3().crossVectors(xAxis, yAxis).normalize();
  mesh.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(xAxis, yAxis, zAxis));
}

type SceneApi = {
  bones: Map<string, THREE.Mesh>;
  joints: Map<string, THREE.Mesh>;
  heads: Map<string, THREE.Mesh>;
  guides: THREE.Group;
};

export function AnatomyViewer({
  figures,
  hint,
  observedLabel,
  inferredLabel,
  bends,
  onBend,
  onSelect,
  camera: cameraId,
  guides,
  photoFlip,
  bodyId,
  bodyLoading,
  bodyFailed,
}: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const sceneRef = useRef<SceneApi | null>(null);
  const sceneObjRef = useRef<THREE.Scene | null>(null);
  const liveRef = useRef<{ id: string; rig: MixamoRig }[]>([]);
  const [bodyNote, setBodyNote] = useState<"loading" | "ready" | "error">("loading");
  const [mixamoEpoch, setMixamoEpoch] = useState(0);
  const rigRef = useRef<{ camera: THREE.PerspectiveCamera; controls: OrbitControls } | null>(null);
  const bendsRef = useRef(bends);
  const onBendRef = useRef(onBend);
  const onSelectRef = useRef(onSelect);
  const figuresRef = useRef(figures);
  const cameraRef = useRef(cameraId);
  const photoFlipRef = useRef(photoFlip);
  const seenFlipRef = useRef(photoFlip);
  bendsRef.current = bends;
  onBendRef.current = onBend;
  onSelectRef.current = onSelect;
  figuresRef.current = figures;
  cameraRef.current = cameraId;
  photoFlipRef.current = photoFlip;
  const structureKey = figures
    .map((figure) => `${figure.id}:${figure.mannequin.joints.length}:${figure.mannequin.bones.length}:${figure.tone}`)
    .join("|");

  useEffect(() => {
    const host = hostRef.current;
    const source = figuresRef.current.filter((figure) => figure.mannequin.joints.length);
    if (!host || !source.length) {
      return;
    }

    const width = host.clientWidth || 480;
    const height = Math.max(320, Math.round(width * 0.85));
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1d21);
    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
    const start = CAMERA_VIEWS[cameraRef.current];
    camera.position.set(start[0], start[1], start[2]);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    host.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.target.set(0, 0.1, 0);
    rigRef.current = { camera, controls };
    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    const key = new THREE.DirectionalLight(0xffffff, 0.85);
    key.position.set(2, 3, 4);
    scene.add(key);

    const root = new THREE.Group();
    scene.add(root);
    const bones = new Map<string, THREE.Mesh>();
    const joints = new Map<string, THREE.Mesh>();
    const heads = new Map<string, THREE.Mesh>();
    const pickables: THREE.Mesh[] = [];

    for (const figure of source) {
    for (const bone of figure.mannequin.bones) {
      const material = new THREE.MeshStandardMaterial({
        color: bone.inferred ? INFERRED : toneColor(figure.tone),
        roughness: 0.55,
        metalness: 0.04,
      });
      const finger = bone.part === "finger" || bone.part === "thumb";
      const shape = shapeFor(bone.part, bone.id);
      if (shape === "skip") {
        continue;
      }
      const geometry =
        shape === "foot"
          ? createFootWedge()
          : shape === "chest"
            ? createLoft([
                { y: -0.5, w: 0.62, d: 0.46 },
                { y: 0.05, w: 0.78, d: 0.52 },
                { y: 0.5, w: 1, d: 0.62 },
              ])
            : shape === "hip"
              ? createLoft([
                  { y: -0.5, w: 0.55, d: 0.5 },
                  { y: 0.5, w: 1, d: 0.82 },
                ])
              : shape === "finger" || shape === "palm" || shape === "shoulder"
                ? new THREE.BoxGeometry(1, 1, 1)
                : createFlesh(FLESH[bone.part] ?? [0.7, 0.62, 0.5]);
      const mesh = new THREE.Mesh(geometry, material);
      mesh.userData.radius = Math.max(bone.radius * 2, 0.02);
      mesh.userData.shape = shape;
      mesh.userData.part = bone.part;
      mesh.userData.personId = figure.id;
      if (finger) {
        mesh.userData.jointId = bone.end;
        pickables.push(mesh);
      }
      root.add(mesh);
      bones.set(`${figure.id}:${bone.id}`, mesh);
    }

    for (const joint of figure.mannequin.joints) {
      if (!DRAG_JOINTS.has(joint.id)) {
        continue;
      }
      const material = new THREE.MeshStandardMaterial({
        color: joint.inferred ? INFERRED : toneColor(figure.tone),
        roughness: 0.4,
      });
      const mesh = new THREE.Mesh(new THREE.SphereGeometry(1, 14, 12), material);
      mesh.userData.hit = 0.045;
      mesh.userData.jointId = joint.id;
      mesh.userData.personId = figure.id;
      root.add(mesh);
      joints.set(`${figure.id}:${joint.id}`, mesh);
      pickables.push(mesh);
    }

    if (figure.mannequin.head) {
      const head = new THREE.Mesh(
        new THREE.SphereGeometry(1, 20, 16),
        new THREE.MeshStandardMaterial({
          color: figure.mannequin.head.inferred ? INFERRED : toneColor(figure.tone),
          roughness: 0.45,
        }),
      );
      head.userData.radius = Math.max(figure.mannequin.head.radius * 2, 0.08);
      head.userData.personId = figure.id;
      root.add(head);
      heads.set(figure.id, head);
    }
    }

    const ground = new THREE.Mesh(
      new THREE.CircleGeometry(1.05, 40),
      new THREE.MeshStandardMaterial({ color: 0x2c323a, roughness: 1 }),
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -1.05;
    scene.add(ground);

    const guidesGroup = new THREE.Group();
    scene.add(guidesGroup);
    sceneRef.current = { bones, joints, heads, guides: guidesGroup };
    sceneObjRef.current = scene;

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let dragging: { id: string; startX: number; startAngle: number } | null = null;

    const onPointerDown = (event: PointerEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hits = raycaster.intersectObjects(pickables, false);
      const hit = hits.find((item) => item.object.userData.jointId);
      if (!hit) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      const personId = String(hit.object.userData.personId || "");
      const active = figuresRef.current.find((figure) => figure.id === personId);
      if (!active?.active) {
        if (personId) {
          onSelectRef.current(personId);
        }
        return;
      }
      const id = String(hit.object.userData.jointId);
      dragging = { id, startX: event.clientX, startAngle: bendsRef.current[id] ?? 0 };
      controls.enabled = false;
    };
    const onPointerMove = (event: PointerEvent) => {
      if (!dragging) {
        return;
      }
      onBendRef.current(
        dragging.id,
        clampBend(
          dragging.startAngle +
            (event.clientX - dragging.startX) * DRAG_PER_PIXEL * (photoFlipRef.current ? -1 : 1),
        ),
      );
    };
    const onPointerUp = () => {
      dragging = null;
      controls.enabled = true;
    };
    renderer.domElement.addEventListener("pointerdown", onPointerDown, true);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);

    let frame = 0;
    const tick = () => {
      frame = requestAnimationFrame(tick);
      controls.update();
      renderer.render(scene, camera);
    };
    tick();

    const onResize = () => {
      const nextW = host.clientWidth || width;
      const nextH = Math.max(320, Math.round(nextW * 0.85));
      camera.aspect = nextW / nextH;
      camera.updateProjectionMatrix();
      renderer.setSize(nextW, nextH);
    };
    window.addEventListener("resize", onResize);

    return () => {
      clearGuideGroup(guidesGroup);
      rigRef.current = null;
      sceneObjRef.current = null;
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", onResize);
      renderer.domElement.removeEventListener("pointerdown", onPointerDown, true);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      controls.dispose();
      renderer.dispose();
      sceneRef.current = null;
      if (renderer.domElement.parentElement === host) {
        host.removeChild(renderer.domElement);
      }
      root.traverse((obj) => {
        if (obj instanceof THREE.Mesh) {
          obj.geometry.dispose();
          const material = obj.material;
          if (Array.isArray(material)) {
            material.forEach((item) => item.dispose());
          } else {
            material.dispose();
          }
        }
      });
      ground.geometry.dispose();
      const groundMaterial = ground.material;
      if (!Array.isArray(groundMaterial)) {
        groundMaterial.dispose();
      }
    };
  }, [structureKey]);

  useEffect(() => {
    const scene = sceneObjRef.current;
    if (!scene) {
      return;
    }
    let cancelled = false;
    let dropped = false;
    const holder = new THREE.Group();
    holder.name = "mixamo-dolls";
    const drop = () => {
      if (dropped) {
        return;
      }
      dropped = true;
      holder.removeFromParent();
      disposeDoll(holder);
      liveRef.current = [];
    };
    setBodyNote("loading");
    loadDollTemplate(bodyId)
      .then(async (template) => {
        if (cancelled) {
          return;
        }
        const next: { id: string; rig: MixamoRig }[] = [];
        for (const figure of figuresRef.current) {
          if (!figure.mannequin.joints.length || cancelled) {
            continue;
          }
          const copy = await cloneDoll(template);
          if (cancelled) {
            disposeDoll(copy);
            continue;
          }
          const rig = prepareRig(copy, figure.mannequin);
          if (!rig) {
            disposeDoll(copy);
            continue;
          }
          holder.add(copy);
          next.push({ id: figure.id, rig });
        }
        if (cancelled || !next.length) {
          drop();
          if (!cancelled) {
            setBodyNote("error");
          }
          return;
        }
        scene.add(holder);
        liveRef.current = next;
        setBodyNote("ready");
        setMixamoEpoch((value) => value + 1);
      })
      .catch(() => {
        if (!cancelled) {
          drop();
          setBodyNote("error");
        }
      });
    return () => {
      cancelled = true;
      drop();
    };
  }, [bodyId, structureKey]);

  useEffect(() => {
    lookFrom(rigRef.current, cameraId, photoFlipRef.current);
  }, [cameraId]);

  useEffect(() => {
    if (seenFlipRef.current === photoFlip) {
      return;
    }
    seenFlipRef.current = photoFlip;
    const rig = rigRef.current;
    if (!rig) {
      return;
    }
    rig.camera.position.x = -rig.camera.position.x;
    rig.controls.update();
  }, [photoFlip]);

  useEffect(() => {
    const api = sceneRef.current;
    if (!api) {
      return;
    }
    const mixamoOn = liveRef.current.length > 0;
    for (const mesh of api.bones.values()) {
      mesh.visible = !mixamoOn;
    }
    for (const mesh of api.heads.values()) {
      mesh.visible = !mixamoOn;
    }
    const marker = new THREE.Vector3();
    for (const figure of figures) {
    const posed = figure.posed;
    const points = new Map(posed.joints.map((joint) => [joint.id, joint]));
    const aspect = posed.aspect && posed.aspect > 0 ? posed.aspect : 1;
    const rig = liveRef.current.find((item) => item.id === figure.id)?.rig;
    if (rig) {
      applyMixamoPose(rig, figure.mannequin, posed, figure.active);
    }
    if (mixamoOn) {
      for (const joint of posed.joints) {
        const mesh = api.joints.get(`${figure.id}:${joint.id}`);
        if (!mesh) {
          continue;
        }
        const hit = Math.max((posed.head?.radius ?? 0.05) * 0.42, 0.02);
        mesh.scale.setScalar(hit);
        if (!rig || !markerPosition(rig, joint.id, marker)) {
          const point = points.get(joint.id);
          if (!point) {
            continue;
          }
          mesh.position.copy(toVec3(point.x, point.y, point.z, aspect));
        } else {
          mesh.position.copy(marker);
        }
        paintActive(mesh, figure.active);
      }
      if (figure.active) {
        drawGuides(api.guides, guides, aspect);
      }
      continue;
    }
    for (const bone of posed.bones) {
      const mesh = api.bones.get(`${figure.id}:${bone.id}`);
      const start = points.get(bone.start);
      const end = points.get(bone.end);
      if (!mesh || !start || !end) {
        continue;
      }
      const a = toVec3(start.x, start.y, start.z, aspect);
      const b = toVec3(end.x, end.y, end.z, aspect);
      const direction = new THREE.Vector3().subVectors(b, a);
      const length = Math.max(direction.length(), 0.01);
      const radius = Math.max(bone.radius * 2, 0.02);
      const shape = String(mesh.userData.shape || "flesh");
      if (shape === "foot") {
        mesh.scale.set(Math.max(length * 0.55, 0.08), length, Math.max(length * 0.42, 0.06));
      } else if (shape === "palm") {
        const side = Math.max(radius * 0.7, 0.02);
        mesh.scale.set(side * 2.4, Math.max(length * 0.94, side * 1.3), side * 0.7);
      } else if (shape === "finger") {
        const side = Math.max(radius * 0.85, 0.014);
        mesh.scale.set(side, Math.max(length * 0.92, side * 1.8), side * 0.6);
      } else if (shape === "chest") {
        const wide = Math.max(radius * 3.1, length * 0.9);
        mesh.scale.set(wide, Math.max(length * 1.05, wide * 0.42), Math.max(radius * 1.7, length * 0.55));
      } else if (shape === "hip") {
        const wide = Math.max(radius * 2.4, length * 0.85);
        mesh.scale.set(wide, Math.max(length * 1.15, wide * 0.35), Math.max(radius * 1.8, length * 0.7));
      } else if (shape === "shoulder") {
        mesh.scale.set(Math.max(radius * 0.9, 0.04), length, Math.max(radius * 1.6, 0.05));
      } else {
        mesh.scale.set(radius * 1.15, length, radius * 1.15);
      }
      mesh.position.copy(a).add(b).multiplyScalar(0.5);
      const left = points.get("shoulder_l");
      const right = points.get("shoulder_r");
      const shoulder =
        bone.id === "torso" && left && right
          ? toVec3(right.x, right.y, right.z, aspect).sub(toVec3(left.x, left.y, left.z, aspect))
          : undefined;
      orientMesh(mesh, direction, shape !== "flesh", shoulder);
      paintActive(mesh, figure.active);
    }
    for (const joint of posed.joints) {
      const mesh = api.joints.get(`${figure.id}:${joint.id}`);
      if (!mesh) {
        continue;
      }
      const point = points.get(joint.id);
      if (!point) {
        continue;
      }
      const hit = Math.max((posed.head?.radius ?? 0.05) * 0.42, 0.02);
      mesh.scale.setScalar(hit);
      mesh.position.copy(toVec3(point.x, point.y, point.z, aspect));
      paintActive(mesh, figure.active);
    }
    const head = api.heads.get(figure.id);
    if (head && posed.head) {
      const point = points.get(posed.head.joint_id);
      if (point) {
        const radius = Math.max(posed.head.radius * 2, 0.08);
        head.scale.setScalar(radius);
        head.position.copy(toVec3(point.x, point.y, point.z, aspect));
        paintActive(head, figure.active);
      }
    }
    if (figure.active) {
      drawGuides(api.guides, guides, aspect);
    }
    }
  }, [figures, guides, mixamoEpoch]);

  if (!figures.some((figure) => figure.mannequin.joints.length)) {
    return <p className="hint">{hint}</p>;
  }

  return (
    <div className="anatomy-viewer">
      <div className="mannequin-tools">
        <MannequinLegend observed={observedLabel} inferred={inferredLabel} />
      </div>
      <p className="hint">{hint}</p>
      {bodyNote === "loading" ? <p className="hint">{bodyLoading}</p> : null}
      {bodyNote === "error" ? <p className="hint">{bodyFailed}</p> : null}
      <div ref={hostRef} className="anatomy-canvas" />
    </div>
  );
}
