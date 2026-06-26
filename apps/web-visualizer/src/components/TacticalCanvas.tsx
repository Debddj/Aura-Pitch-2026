"use client";

import { useRef, useEffect } from "react";
import * as THREE from "three";

export default function TacticalCanvas() {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!mountRef.current) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a0a);

    const camera = new THREE.PerspectiveCamera(
      75,
      mountRef.current.clientWidth / mountRef.current.clientHeight,
      0.1,
      1000
    );
    camera.position.set(0, 40, 60);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    mountRef.current.appendChild(renderer.domElement);

    // Pitch
    const pitchGeometry = new THREE.PlaneGeometry(105, 68);
    const pitchMaterial = new THREE.MeshBasicMaterial({ color: 0x2d5a27 });
    const pitch = new THREE.Mesh(pitchGeometry, pitchMaterial);
    pitch.rotation.x = -Math.PI / 2;
    scene.add(pitch);

    // Grid lines
    const gridHelper = new THREE.GridHelper(105, 15, 0xffffff, 0xffffff);
    scene.add(gridHelper);

    // Animate
    const animate = () => {
      requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      renderer.dispose();
      mountRef.current?.removeChild(renderer.domElement);
    };
  }, []);

  return <div ref={mountRef} className="w-full h-screen" />;
}
