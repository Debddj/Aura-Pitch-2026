"use client";

import React, { useRef, useMemo, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Text, Line, Ring } from "@react-three/drei";
import * as THREE from "three";
import { useTelemetryStore, PlayerNode, BallNode } from "../hooks/useTelemetryStore";

// ---------------------------------------------------------------------------
// 3D Pitch Lines Component
// ---------------------------------------------------------------------------
function PitchMarkings() {
  const pitchWidth = 68;
  const pitchLength = 105;
  const wHalf = pitchWidth / 2;
  const lHalf = pitchLength / 2;

  // Compile lines
  const lines = useMemo(() => {
    const strokeWidth = 0.15;
    const items = [];

    // Outer Boundary
    items.push([
      [-lHalf, 0, -wHalf],
      [lHalf, 0, -wHalf],
      [lHalf, 0, wHalf],
      [-lHalf, 0, wHalf],
      [-lHalf, 0, -wHalf],
    ]);

    // Halfway Line
    items.push([
      [0, 0, -wHalf],
      [0, 0, wHalf],
    ]);

    // Penalty Box - Left (Home)
    items.push([
      [-lHalf, 0, -20.16],
      [-lHalf + 16.5, 0, -20.16],
      [-lHalf + 16.5, 0, 20.16],
      [-lHalf, 0, 20.16],
    ]);

    // Goal Box - Left (Home)
    items.push([
      [-lHalf, 0, -9.16],
      [-lHalf + 5.5, 0, -9.16],
      [-lHalf + 5.5, 0, 9.16],
      [-lHalf, 0, 9.16],
    ]);

    // Penalty Box - Right (Away)
    items.push([
      [lHalf, 0, -20.16],
      [lHalf - 16.5, 0, -20.16],
      [lHalf - 16.5, 0, 20.16],
      [lHalf, 0, 20.16],
    ]);

    // Goal Box - Right (Away)
    items.push([
      [lHalf, 0, -9.16],
      [lHalf - 5.5, 0, -9.16],
      [lHalf - 5.5, 0, 9.16],
      [lHalf, 0, 9.16],
    ]);

    return items;
  }, [lHalf, wHalf]);

  // Center Circle points
  const centerCirclePoints = useMemo(() => {
    const pts = [];
    const radius = 9.15;
    for (let i = 0; i <= 64; i++) {
      const theta = (i / 64) * Math.PI * 2;
      pts.push([Math.cos(theta) * radius, 0, Math.sin(theta) * radius]);
    }
    return pts;
  }, []);

  return (
    <group>
      {/* Grass Pitch Plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]} receiveShadow>
        <planeGeometry args={[pitchLength + 10, pitchWidth + 10]} />
        <meshStandardMaterial color="#141416" roughness={0.9} metalness={0.1} />
      </mesh>

      {/* Regulation Field area */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
        <planeGeometry args={[pitchLength, pitchWidth]} />
        <meshStandardMaterial color="#1a2e1d" roughness={0.8} />
      </mesh>

      {/* Render line segments */}
      {lines.map((pts, idx) => (
        <Line
          key={`mark-${idx}`}
          points={pts as [number, number, number][]}
          color="#a1a1aa"
          lineWidth={1.5}
        />
      ))}

      {/* Center Circle */}
      <Line points={centerCirclePoints as [number, number, number][]} color="#a1a1aa" lineWidth={1.5} />

      {/* Center Spot */}
      <mesh position={[0, 0.01, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.3, 16]} />
        <meshBasicMaterial color="#a1a1aa" />
      </mesh>
    </group>
  );
}

// ---------------------------------------------------------------------------
// Dynamic Team Compactness Convex Hull Poly Overlay
// ---------------------------------------------------------------------------
function ConvexHullOverlay({ players, team, color }: { players: PlayerNode[]; team: string; color: string }) {
  const shape = useMemo(() => {
    // Filter outfield players
    const outfield = players.filter((p) => p.team === team && p.role !== "GK");
    if (outfield.length < 3) return null;

    // Graham Scan convex hull
    const pts = outfield.map((p) => new THREE.Vector2(p.position.x, p.position.y));
    
    // Find bottom-most point (lowest Y, then lowest X)
    let startIdx = 0;
    for (let i = 1; i < pts.length; i++) {
      if (pts[i].y < pts[startIdx].y || (pts[i].y === pts[startIdx].y && pts[i].x < pts[startIdx].x)) {
        startIdx = i;
      }
    }
    const start = pts[startIdx];
    
    // Sort other points by polar angle with start point
    const remaining = pts.filter((_, idx) => idx !== startIdx);
    remaining.sort((a, b) => {
      const angleA = Math.atan2(a.y - start.y, a.x - start.x);
      const angleB = Math.atan2(b.y - start.y, b.x - start.x);
      if (angleA < angleB) return -1;
      if (angleA > angleB) return 1;
      // return closest if collinear
      const distA = (a.x - start.x)**2 + (a.y - start.y)**2;
      const distB = (b.x - start.x)**2 + (b.y - start.y)**2;
      return distA - distB;
    });

    const hull = [start];
    for (const p of remaining) {
      while (hull.length >= 2) {
        const top = hull[hull.length - 1];
        const nextToTop = hull[hull.length - 2];
        const cross = (top.x - nextToTop.x) * (p.y - nextToTop.y) - (top.y - nextToTop.y) * (p.x - nextToTop.x);
        if (cross > 0) break;
        hull.pop();
      }
      hull.push(p);
    }

    if (hull.length < 3) return null;

    // Create 3D Shape geometry
    const threeShape = new THREE.Shape();
    threeShape.moveTo(hull[0].x, hull[0].y);
    for (let i = 1; i < hull.length; i++) {
      threeShape.lineTo(hull[i].x, hull[i].y);
    }
    threeShape.closePath();

    return threeShape;
  }, [players, team]);

  if (!shape) return null;

  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, 0]}>
      <shapeGeometry args={[shape]} />
      <meshBasicMaterial color={color} opacity={0.08} transparent side={THREE.DoubleSide} depthWrite={false} />
    </mesh>
  );
}

// ---------------------------------------------------------------------------
// Selected Player 29-Point Skeleton Rig Component
// ---------------------------------------------------------------------------
function PlayerSkeleton({ skeleton }: { skeleton: NonNullable<PlayerNode["skeleton"]> }) {
  // Connect joints together to draw bones
  const bones = useMemo(() => {
    const list: [string, string][] = [
      ["head", "neck"], ["neck", "spine_chest"], ["spine_chest", "chest_mid"],
      ["chest_mid", "spine_navel"], ["spine_navel", "pelvis"],
      // Left Arm
      ["spine_chest", "left_clavicle"], ["left_clavicle", "left_shoulder"],
      ["left_shoulder", "left_elbow"], ["left_elbow", "left_wrist"], ["left_wrist", "left_hand"],
      // Right Arm
      ["spine_chest", "right_clavicle"], ["right_clavicle", "right_shoulder"],
      ["right_shoulder", "right_elbow"], ["right_elbow", "right_wrist"], ["right_wrist", "right_hand"],
      // Left Leg
      ["pelvis", "left_hip"], ["left_hip", "left_knee"], ["left_knee", "left_ankle"], ["left_ankle", "left_foot"],
      // Right Leg
      ["pelvis", "right_hip"], ["right_hip", "right_knee"], ["right_knee", "right_ankle"], ["right_ankle", "right_foot"],
      // Face
      ["neck", "nose"], ["nose", "left_eye"], ["nose", "right_eye"],
      ["left_eye", "left_ear"], ["right_eye", "right_ear"]
    ];
    return list;
  }, []);

  return (
    <group>
      {/* Draw joint markers */}
      {skeleton.map((joint, idx) => (
        <mesh key={`joint-${idx}`} position={[joint.x, joint.z, joint.y]}>
          <sphereGeometry args={[0.08, 8, 8]} />
          <meshBasicMaterial color="#06b6d4" />
        </mesh>
      ))}

      {/* Draw connecting bone lines */}
      {bones.map(([j1Name, j2Name], idx) => {
        const j1 = skeleton.find((j) => j.joint === j1Name);
        const j2 = skeleton.find((j) => j.joint === j2Name);
        if (!j1 || !j2) return null;

        return (
          <Line
            key={`bone-${idx}`}
            points={[
              [j1.x, j1.z, j1.y],
              [j2.x, j2.z, j2.y],
            ]}
            color="#06b6d4"
            lineWidth={1.0}
            opacity={0.8}
            transparent
          />
        );
      })}
    </group>
  );
}

// ---------------------------------------------------------------------------
// Interactive Player Node Component
// ---------------------------------------------------------------------------
function PlayerMesh({
  player,
  isSelected,
  onClick,
}: {
  player: PlayerNode;
  isSelected: boolean;
  onClick: () => void;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const color = player.team === "home" ? "#06b6d4" : "#f59e0b"; // Cyan vs Amber

  // Smooth position interpolation (lerp)
  useFrame(() => {
    if (!meshRef.current) return;
    const targetX = player.position.x;
    const targetY = player.position.y;
    const targetZ = player.position.z;
    
    // Smoothly lerp towards data coordinates
    meshRef.current.position.x = THREE.MathUtils.lerp(meshRef.current.position.x, targetX, 0.35);
    meshRef.current.position.z = THREE.MathUtils.lerp(meshRef.current.position.z, targetY, 0.35);
    meshRef.current.position.y = THREE.MathUtils.lerp(meshRef.current.position.y, targetZ, 0.35);
  });

  return (
    <group>
      {/* Lerping mesh group wrapper */}
      <mesh ref={meshRef} onClick={(e) => { e.stopPropagation(); onClick(); }}>
        {/* Core Cylinder Jersey Marker */}
        <cylinderGeometry args={[0.6, 0.6, 1.4, 16]} />
        <meshStandardMaterial color={color} roughness={0.4} metalness={0.2} />

        {/* Selected Highlight Ring */}
        {isSelected && (
          <Ring args={[0.9, 1.0, 32]} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.68, 0]}>
            <meshBasicMaterial color="#06b6d4" />
          </Ring>
        )}

        {/* Floating Jersey Number */}
        <Text
          position={[0, 1.2, 0]}
          fontSize={0.65}
          color="#ffffff"
          font="monospace"
          anchorX="center"
          anchorY="middle"
          rotation={[0, 0, 0]}
        >
          {player.jersey_number.toString()}
        </Text>
      </mesh>
    </group>
  );
}

// ---------------------------------------------------------------------------
// Dynamic Match Ball Component
// ---------------------------------------------------------------------------
function BallMesh({ ball }: { ball: BallNode }) {
  const meshRef = useRef<THREE.Mesh>(null);

  // Smooth position interpolation (lerp)
  useFrame(() => {
    if (!meshRef.current) return;
    meshRef.current.position.x = THREE.MathUtils.lerp(meshRef.current.position.x, ball.position.x, 0.4);
    meshRef.current.position.z = THREE.MathUtils.lerp(meshRef.current.position.y, ball.position.y, 0.4);
    meshRef.current.position.y = THREE.MathUtils.lerp(meshRef.current.position.y, ball.position.z, 0.4);
    
    // Rotate ball based on spin angular velocity
    meshRef.current.rotation.x += ball.angular_velocity.x * 0.01;
    meshRef.current.rotation.y += ball.angular_velocity.y * 0.01;
    meshRef.current.rotation.z += ball.angular_velocity.z * 0.01;
  });

  // Calculate subtick trail points
  const trailPoints = useMemo(() => {
    if (!ball.subticks || ball.subticks.length === 0) return [];
    return ball.subticks.map((t) => [t.x, t.z, t.y] as [number, number, number]);
  }, [ball.subticks]);

  return (
    <group>
      {/* 500Hz Sub-tick Trajectory Trail */}
      {trailPoints.length > 1 && (
        <Line points={trailPoints} color="#06b6d4" lineWidth={1.5} opacity={0.6} transparent />
      )}

      {/* Sphere Mesh */}
      <mesh ref={meshRef} castShadow>
        <sphereGeometry args={[0.35, 16, 16]} />
        <meshStandardMaterial color="#ffffff" roughness={0.3} metalness={0.1} />
      </mesh>
    </group>
  );
}

// ---------------------------------------------------------------------------
// Main Canvas Component
// ---------------------------------------------------------------------------
export default function TacticalCanvas() {
  const { state, dispatch } = useTelemetryStore();
  const frame = state.latestFrame;

  const players = frame?.players || [];
  const ball = frame?.ball;
  const passingLanes = frame?.analytics?.passing_lanes || [];
  const selectedPlayerId = state.selectedPlayerId;

  // Selected player's skeletal details
  const selectedPlayer = players.find((p) => p.player_id === selectedPlayerId);

  const handleSelectPlayer = (id: string) => {
    dispatch({ type: "SET_SELECTED_PLAYER", payload: id });
  };

  const handleCanvasClick = () => {
    dispatch({ type: "SET_SELECTED_PLAYER", payload: null });
  };

  return (
    <div className="w-full h-full relative" onClick={handleCanvasClick}>
      <Canvas
        camera={{ position: [0, 45, 65], fov: 50 }}
        shadows
        className="w-full h-full bg-cyber-bg"
      >
        <ambientLight intensity={0.5} />
        <directionalLight
          position={[0, 50, 20]}
          intensity={0.8}
          castShadow
          shadow-mapSize-width={1024}
          shadow-mapSize-height={1024}
        />

        {/* 3D Regulations Field */}
        <PitchMarkings />

        {/* Convex Hull Areas */}
        {players.length > 0 && (
          <>
            <ConvexHullOverlay players={players} team="home" color="#06b6d4" />
            <ConvexHullOverlay players={players} team="away" color="#f59e0b" />
          </>
        )}

        {/* Passing Lanes */}
        {passingLanes.map((lane, idx) => (
          <Line
            key={`lane-${idx}`}
            points={[
              [lane.start.x, 0.05, lane.start.y],
              [lane.end.x, 0.05, lane.end.y],
            ]}
            color={lane.open ? "#10b981" : "#ef4444"} // Green vs Red
            lineWidth={lane.open ? 2.5 : 1.0}
            opacity={lane.open ? 0.75 : 0.2}
            transparent
          />
        ))}

        {/* Dynamic Skeleton for Selected Player */}
        {selectedPlayer && selectedPlayer.skeleton && (
          <PlayerSkeleton skeleton={selectedPlayer.skeleton} />
        )}

        {/* Player JERSEY nodes */}
        {players.map((p) => (
          <PlayerMesh
            key={p.player_id}
            player={p}
            isSelected={selectedPlayerId === p.player_id}
            onClick={() => handleSelectPlayer(p.player_id)}
          />
        ))}

        {/* Dynamic Ball node */}
        {ball && <BallMesh ball={ball} />}

        {/* Orbit Controls */}
        <OrbitControls maxPolarAngle={Math.PI / 2 - 0.05} minDistance={10} maxDistance={150} />
      </Canvas>
    </div>
  );
}
