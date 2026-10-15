"use client";

import { useEffect, useRef, useState } from "react";

type Props = {
  title: string;
  note: string;
  takeLabel: string;
  closeLabel: string;
  deniedLabel: string;
  onShot: (file: File) => void;
  onClose: () => void;
};

/** 頭から足が収まる枠を出し、その大きさで1枚撮る。 */
export function CaptureGuide({ title, note, takeLabel, closeLabel, deniedLabel, onShot, onClose }: Props) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    let stream: MediaStream | null = null;
    let stopped = false;
    void navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "environment" }, audio: false })
      .then((next) => {
        if (stopped) {
          next.getTracks().forEach((track) => track.stop());
          return;
        }
        stream = next;
        if (videoRef.current) {
          videoRef.current.srcObject = next;
          void videoRef.current.play();
        }
      })
      .catch((error) => {
        console.error("camera open failed", error);
        if (!stopped) {
          setDenied(true);
        }
      });
    return () => {
      stopped = true;
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  function shoot() {
    const video = videoRef.current;
    if (!video || video.videoWidth <= 0) {
      return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }
    context.drawImage(video, 0, 0);
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          return;
        }
        onShot(new File([blob], "camera.jpg", { type: "image/jpeg" }));
      },
      "image/jpeg",
      0.92,
    );
  }

  return (
    <div className="capture-guide" role="dialog" aria-label={title}>
      <div className="capture-stage">
        <video ref={videoRef} playsInline muted />
        <div className="guide-frame" aria-hidden="true">
          <span className="guide-head" />
        </div>
        <p className="guide-note">{denied ? deniedLabel : note}</p>
      </div>
      <div className="guide-actions">
        <button type="button" onClick={shoot} disabled={denied}>
          {takeLabel}
        </button>
        <button type="button" onClick={onClose}>
          {closeLabel}
        </button>
      </div>
    </div>
  );
}
