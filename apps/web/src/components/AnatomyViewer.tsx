"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

import type { PoseData } from "@/lib/api";
import { buildFigure, type FigureBone, type FigurePart } from "@/lib/figure";

type Layer = "skeleton" | "muscle";

type Props = {
  pose: PoseData;
  hint: string;
  layerSkeleton: string;
  layerMuscle: string;
};

function toVec3(x: number, y: number, z: number): THREE.Vector3 {
  return new THREE.Vector3((x - 0.5) * 2, -(y - 0.5) * 2, z * 2);
}

function radiusFor(part: FigurePart, layer: Layer): number {
  if (layer === "skeleton") {
    if (part === "torso") {
      return 0.022;
    }
    if (part === "limb") {
      return 0.016;
    }
    return 0.012;
  }
  if (part === "torso") {
    return 0.11;
  }
  if (part === "limb") {
    return 0.055;
  }
  if (part === "neck") {
    return 0.028;
  }
  return 0.032;
}

function makeBone(bone: FigureBone, layer: Layer, color: number): THREE.Mesh {
  const a = toVec3(bone.x1, bone.y1, bone.z1);
  const b = toVec3(bone.x2, bone.y2, bone.z2);
  const direction = new THREE.Vector3().subVectors(b, a);
  const length = Math.max(direction.length(), 0.01);
  const mid = new THREE.Vector3().addVectors(a, b).multiplyScalar(0.5);
  const geometry = new THREE.CylinderGeometry(radiusFor(bone.part, layer), radiusFor(bone.part, layer), length, 10);
  const material = new THREE.MeshStandardMaterial({
    color,
    roughness: 0.55,
    metalness: 0.05,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.copy(mid);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.clone().normalize());
  return mesh;
}

export function AnatomyViewer({ pose, hint, layerSkeleton, layerMuscle }: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const [layer, setLayer] = useState<Layer>("muscle");
  const figure = useMemo(() => buildFigure(pose), [pose]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || !figure.bones.length) {
      return;
    }

    const width = host.clientWidth || 480;
    const height = Math.max(320, Math.round(width * 0.85));

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1d21);

    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
    camera.position.set(0, 0.15, 3.4);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    host.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.target.set(0, 0, 0);

    scene.add(new THREE.AmbientLight(0xffffff, 0.75));
    const key = new THREE.DirectionalLight(0xffffff, 0.8);
    key.position.set(2, 3, 4);
    scene.add(key);

    const root = new THREE.Group();
    scene.add(root);

    const boneColor = layer === "muscle" ? 0xb84a3a : 0xd7dbe0;
    for (const item of figure.bones) {
      root.add(makeBone(item, layer, boneColor));
    }

    if (figure.head) {
      const headRadius = Math.max(figure.head.radius * 2, layer === "muscle" ? 0.16 : 0.12);
      const head = new THREE.Mesh(
        new THREE.SphereGeometry(headRadius, 20, 16),
        new THREE.MeshStandardMaterial({
          color: layer === "muscle" ? 0xc46a58 : 0xf2f2f2,
          roughness: 0.45,
        }),
      );
      head.position.copy(toVec3(figure.head.x, figure.head.y, figure.head.z));
      root.add(head);
    }

    const jointRadius = layer === "muscle" ? 0.04 : 0.028;
    const jointGeo = new THREE.SphereGeometry(jointRadius, 12, 12);
    const jointMat = new THREE.MeshStandardMaterial({
      color: layer === "muscle" ? 0x8d3228 : 0xffffff,
      roughness: 0.4,
    });
    for (const point of figure.joints) {
      const sphere = new THREE.Mesh(jointGeo, jointMat);
      sphere.position.copy(toVec3(point.x, point.y, point.z));
      root.add(sphere);
    }

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
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", onResize);
      controls.dispose();
      renderer.dispose();
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
    };
  }, [figure, layer]);

  if (!figure.bones.length) {
    return <p className="hint">{hint}</p>;
  }

  return (
    <div className="anatomy-viewer">
      <div className="modes anatomy-layers">
        <button type="button" aria-pressed={layer === "skeleton"} onClick={() => setLayer("skeleton")}>
          {layerSkeleton}
        </button>
        <button type="button" aria-pressed={layer === "muscle"} onClick={() => setLayer("muscle")}>
          {layerMuscle}
        </button>
      </div>
      <p className="hint">{hint}</p>
      <div ref={hostRef} className="anatomy-canvas" />
    </div>
  );
}
