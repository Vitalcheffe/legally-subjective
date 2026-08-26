"use client";

/**
 * Behavioral Matrix — WebGL force-directed graph (three.js).
 * Renders real graph payloads (nodes/edges computed from the corpus index)
 * at 60 FPS. Layout is deterministic: initial positions follow an indexed
 * spiral and the force simulation is fully deterministic (no RNG).
 */
import { useEffect, useRef } from "react";
import * as THREE from "three";

export interface GraphNode {
  id: string | number;
  label: string;
  size: number;
  color: string;
}

export interface GraphEdge {
  source: string | number;
  target: string | number;
  weight: number;
}

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedId?: string | number | null;
  hoveredId?: string | number | null;
  onSelect?: (id: string | number | null) => void;
  onHover?: (id: string | number | null) => void;
  height?: number;
  className?: string;
}

const VERTEX_SHADER = `
  attribute float size;
  varying vec3 vColor;
  void main() {
    vColor = color;
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = size * (240.0 / -mv.z);
    gl_Position = projectionMatrix * mv;
  }
`;

const FRAGMENT_SHADER = `
  varying vec3 vColor;
  void main() {
    vec2 c = gl_PointCoord - vec2(0.5);
    float d = length(c);
    if (d > 0.5) discard;
    float alpha = smoothstep(0.5, 0.38, d);
    gl_FragColor = vec4(vColor, alpha);
  }
`;

export default function ForceGraph3D({
  nodes,
  edges,
  selectedId = null,
  onSelect,
  onHover,
  height = 520,
  className,
}: Props) {
  const mountRef = useRef<HTMLDivElement>(null);
  const labelRef = useRef<HTMLDivElement>(null);
  const fpsRef = useRef<HTMLSpanElement>(null);

  // mutable refs shared with the render loop
  const stateRef = useRef({
    nodes,
    edges,
    selectedId,
    onSelect,
    onHover,
  });
  useEffect(() => {
    stateRef.current = { nodes, edges, selectedId, onSelect, onHover };
  });

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || nodes.length === 0) return;

    // ------------------------------------------------------------------
    // scene setup
    // ------------------------------------------------------------------
    const width = mount.clientWidth || 800;
    const heightPx = height;
    const scene = new THREE.Scene();
    // Paper-fog: distant nodes recede toward the ivory page, not into black.
    scene.fog = new THREE.FogExp2(0xf4f2ec, 0.0016);
    const camera = new THREE.PerspectiveCamera(55, width / heightPx, 1, 4000);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, heightPx);
    renderer.setClearColor(0x000000, 0);
    mount.appendChild(renderer.domElement);
    renderer.domElement.style.touchAction = "none";
    renderer.domElement.style.cursor = "grab";

    // ------------------------------------------------------------------
    // deterministic layout state
    // ------------------------------------------------------------------
    const n = nodes.length;
    const idToIdx = new Map<string | number, number>();
    nodes.forEach((node, i) => idToIdx.set(node.id, i));

    const positions = new Float32Array(n * 3);
    const velocities = new Float32Array(n * 3);
    // indexed golden-spiral on a sphere — deterministic start
    for (let i = 0; i < n; i++) {
      const t = i / n;
      const phi = Math.acos(1 - 2 * t);
      const theta = Math.PI * (1 + Math.sqrt(5)) * i;
      const r = 320 * Math.cbrt(n) / 6.5;
      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = r * Math.cos(phi);
    }

    // physics edge list (index pairs)
    const physEdges = edges
      .map((e) => ({
        a: idToIdx.get(e.source),
        b: idToIdx.get(e.target),
        w: e.weight,
      }))
      .filter((e): e is { a: number; b: number; w: number } =>
        e.a !== undefined && e.b !== undefined,
      ) as { a: number; b: number; w: number }[];

    // ------------------------------------------------------------------
    // points (nodes)
    // ------------------------------------------------------------------
    const baseColors = new Float32Array(n * 3);
    const sizes = new Float32Array(n);
    const displayColors = new Float32Array(n * 3);
    const tmpColor = new THREE.Color();
    nodes.forEach((node, i) => {
      tmpColor.set(node.color);
      baseColors[i * 3] = tmpColor.r;
      baseColors[i * 3 + 1] = tmpColor.g;
      baseColors[i * 3 + 2] = tmpColor.b;
      sizes[i] = node.size;
    });

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(displayColors, 3));
    geometry.setAttribute("size", new THREE.BufferAttribute(sizes, 1));
    const material = new THREE.ShaderMaterial({
      vertexShader: VERTEX_SHADER,
      fragmentShader: FRAGMENT_SHADER,
      transparent: true,
      depthWrite: false,
      vertexColors: true,
      blending: THREE.NormalBlending,
    });
    const points = new THREE.Points(geometry, material);
    scene.add(points);

    // ------------------------------------------------------------------
    // edges
    // ------------------------------------------------------------------
    const m = physEdges.length;
    const edgePositions = new Float32Array(m * 6);
    const edgeColors = new Float32Array(m * 6);
    const edgeGeometry = new THREE.BufferGeometry();
    edgeGeometry.setAttribute("position", new THREE.BufferAttribute(edgePositions, 3));
    edgeGeometry.setAttribute("color", new THREE.BufferAttribute(edgeColors, 3));
    const edgeMaterial = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.55,
      blending: THREE.NormalBlending,
      depthWrite: false,
    });
    const lines = new THREE.LineSegments(edgeGeometry, edgeMaterial);
    scene.add(lines);

    // ------------------------------------------------------------------
    // camera orbit control (custom, dependency-free)
    // ------------------------------------------------------------------
    const cam = { theta: 0.6, phi: 1.05, radius: 640, target: new THREE.Vector3(0, 0, 0) };
    let dragging = false;
    let lastX = 0, lastY = 0;
    let lastInteraction = performance.now();
    let pointerX = -1, pointerY = -1;
    const projected = new Float32Array(n * 2);

    const applyCamera = () => {
      const sinPhi = Math.sin(cam.phi);
      camera.position.set(
        cam.target.x + cam.radius * sinPhi * Math.cos(cam.theta),
        cam.target.y + cam.radius * Math.cos(cam.phi),
        cam.target.z + cam.radius * sinPhi * Math.sin(cam.theta),
      );
      camera.lookAt(cam.target);
    };
    applyCamera();

    const onPointerDown = (e: PointerEvent) => {
      dragging = true;
      lastX = e.clientX;
      lastY = e.clientY;
      lastInteraction = performance.now();
      renderer.domElement.style.cursor = "grabbing";
    };
    const onPointerMove = (e: PointerEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointerX = e.clientX - rect.left;
      pointerY = e.clientY - rect.top;
      lastInteraction = performance.now();
      if (dragging) {
        cam.theta -= (e.clientX - lastX) * 0.005;
        cam.phi = Math.max(0.15, Math.min(Math.PI - 0.15, cam.phi - (e.clientY - lastY) * 0.005));
        lastX = e.clientX;
        lastY = e.clientY;
      }
    };
    const onPointerUp = () => {
      dragging = false;
      renderer.domElement.style.cursor = "grab";
    };
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      cam.radius = Math.max(180, Math.min(2400, cam.radius * (1 + e.deltaY * 0.001)));
      lastInteraction = performance.now();
    };
    renderer.domElement.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    renderer.domElement.addEventListener("wheel", onWheel, { passive: false });

    let downX = 0, downY = 0;
    renderer.domElement.addEventListener("pointerdown", (e) => {
      downX = e.clientX;
      downY = e.clientY;
    });
    const onClick = (e: MouseEvent) => {
      // ignore drags
      if (Math.abs(e.clientX - downX) > 4 || Math.abs(e.clientY - downY) > 4) return;
      const rect = renderer.domElement.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const hit = pick(mx, my);
      stateRef.current.onSelect?.(hit !== -1 ? nodes[hit].id : null);
    };
    renderer.domElement.addEventListener("click", onClick);

    const pick = (mx: number, my: number): number => {
      let best = -1, bestDist = 14;
      for (let i = 0; i < n; i++) {
        const dx = projected[i * 2] - mx;
        const dy = projected[i * 2 + 1] - my;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d < bestDist) {
          bestDist = d;
          best = i;
        }
      }
      return best;
    };

    // resize handling
    const resizeObserver = new ResizeObserver(() => {
      const w = mount.clientWidth || 800;
      camera.aspect = w / heightPx;
      camera.updateProjectionMatrix();
      renderer.setSize(w, heightPx);
    });
    resizeObserver.observe(mount);

    // ------------------------------------------------------------------
    // render loop
    // ------------------------------------------------------------------
    let alpha = 1;
    let raf = 0;
    let frame = 0;
    let fpsCount = 0;
    let fpsTime = performance.now();
    let hoverIdx = -1;

    const tmpVec = new THREE.Vector3();

    const simulate = () => {
      if (alpha < 0.004) return;
      const repulsion = 2600 * alpha;
      // pairwise repulsion
      for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
          let dx = positions[i * 3] - positions[j * 3];
          let dy = positions[i * 3 + 1] - positions[j * 3 + 1];
          let dz = positions[i * 3 + 2] - positions[j * 3 + 2];
          let d2 = dx * dx + dy * dy + dz * dz;
          if (d2 < 1) {
            dx = (i % 7) - 3 + 0.5;
            dy = (j % 5) - 2 + 0.5;
            dz = ((i + j) % 9) - 4 + 0.5;
            d2 = dx * dx + dy * dy + dz * dz + 1;
          }
          const f = repulsion / d2;
          const d = Math.sqrt(d2);
          const fx = (dx / d) * f, fy = (dy / d) * f, fz = (dz / d) * f;
          velocities[i * 3] += fx;
          velocities[i * 3 + 1] += fy;
          velocities[i * 3 + 2] += fz;
          velocities[j * 3] -= fx;
          velocities[j * 3 + 1] -= fy;
          velocities[j * 3 + 2] -= fz;
        }
      }
      // springs
      for (const e of physEdges) {
        const a = e.a * 3, b = e.b * 3;
        const dx = positions[a] - positions[b];
        const dy = positions[a + 1] - positions[b + 1];
        const dz = positions[a + 2] - positions[b + 2];
        const d = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1;
        const rest = 130 / (1 + Math.log2(1 + e.w));
        const f = (d - rest) * 0.012 * alpha;
        const fx = (dx / d) * f, fy = (dy / d) * f, fz = (dz / d) * f;
        velocities[a] -= fx; velocities[a + 1] -= fy; velocities[a + 2] -= fz;
        velocities[b] += fx; velocities[b + 1] += fy; velocities[b + 2] += fz;
      }
      // centering + integrate
      for (let i = 0; i < n; i++) {
        velocities[i * 3] -= positions[i * 3] * 0.0025 * alpha;
        velocities[i * 3 + 1] -= positions[i * 3 + 1] * 0.0025 * alpha;
        velocities[i * 3 + 2] -= positions[i * 3 + 2] * 0.0025 * alpha;
        velocities[i * 3] *= 0.86;
        velocities[i * 3 + 1] *= 0.86;
        velocities[i * 3 + 2] *= 0.86;
        positions[i * 3] += velocities[i * 3];
        positions[i * 3 + 1] += velocities[i * 3 + 1];
        positions[i * 3 + 2] += velocities[i * 3 + 2];
      }
      alpha *= 0.988;
    };

    // Paper-tone constants: receded elements fade toward the page, never to black.
    const PAPER = new THREE.Color(0xf4f2ec);
    const EDGE_BASE = new THREE.Color(0x9a948a);   // warm gray
    const EDGE_FOCUS = new THREE.Color(0x33497a);  // ink navy (selection)

    const applyColors = () => {
      const sel = stateRef.current.selectedId;
      const selIdx = sel != null ? idToIdx.get(sel) : undefined;
      if (selIdx === undefined) {
        displayColors.set(baseColors);
        for (let i = 0; i < n; i++) sizes[i] = nodes[i].size;
      } else {
        const neighbors = new Set<number>();
        for (const e of physEdges) {
          if (e.a === selIdx) neighbors.add(e.b);
          if (e.b === selIdx) neighbors.add(e.a);
        }
        for (let i = 0; i < n; i++) {
          const isSel = i === selIdx;
          const isNeighbor = neighbors.has(i);
          // fade factor toward paper: selected 1.0, neighbor 0.92, others 0.22
          const factor = isSel ? 1.0 : isNeighbor ? 0.92 : 0.22;
          displayColors[i * 3] = PAPER.r + (baseColors[i * 3] - PAPER.r) * factor;
          displayColors[i * 3 + 1] = PAPER.g + (baseColors[i * 3 + 1] - PAPER.g) * factor;
          displayColors[i * 3 + 2] = PAPER.b + (baseColors[i * 3 + 2] - PAPER.b) * factor;
          sizes[i] = nodes[i].size * (isSel ? 1.7 : isNeighbor ? 1.15 : 0.85);
        }
      }
      // edges — strength fades toward paper
      if (selIdx === undefined) {
        for (let e = 0; e < physEdges.length; e++) {
          const w = Math.min(1, 0.25 + physEdges[e].w / 40);
          edgeColors[e * 6] = PAPER.r + (EDGE_BASE.r - PAPER.r) * w;
          edgeColors[e * 6 + 1] = PAPER.g + (EDGE_BASE.g - PAPER.g) * w;
          edgeColors[e * 6 + 2] = PAPER.b + (EDGE_BASE.b - PAPER.b) * w;
          edgeColors[e * 6 + 3] = edgeColors[e * 6];
          edgeColors[e * 6 + 4] = edgeColors[e * 6 + 1];
          edgeColors[e * 6 + 5] = edgeColors[e * 6 + 2];
        }
      } else {
        for (let e = 0; e < physEdges.length; e++) {
          const a = physEdges[e].a, b = physEdges[e].b;
          const connected = a === selIdx || b === selIdx;
          const w = connected ? Math.min(1, 0.5 + physEdges[e].w / 30) : 0.06;
          const base = connected ? EDGE_FOCUS : EDGE_BASE;
          edgeColors[e * 6] = PAPER.r + (base.r - PAPER.r) * w;
          edgeColors[e * 6 + 1] = PAPER.g + (base.g - PAPER.g) * w;
          edgeColors[e * 6 + 2] = PAPER.b + (base.b - PAPER.b) * w;
          edgeColors[e * 6 + 3] = edgeColors[e * 6];
          edgeColors[e * 6 + 4] = edgeColors[e * 6 + 1];
          edgeColors[e * 6 + 5] = edgeColors[e * 6 + 2];
        }
      }
      geometry.attributes.color.needsUpdate = true;
      geometry.attributes.size.needsUpdate = true;
      edgeGeometry.attributes.color.needsUpdate = true;
    };

    const loop = () => {
      raf = requestAnimationFrame(loop);
      frame += 1;

      simulate();

      // slow idle auto-rotation
      if (!dragging && performance.now() - lastInteraction > 5000) {
        cam.theta += 0.0012;
      }
      applyCamera();

      // project for picking + label
      const rect = renderer.domElement.getBoundingClientRect();
      for (let i = 0; i < n; i++) {
        tmpVec.set(positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2]);
        tmpVec.project(camera);
        projected[i * 2] = (tmpVec.x * 0.5 + 0.5) * rect.width;
        projected[i * 2 + 1] = (-tmpVec.y * 0.5 + 0.5) * rect.height;
      }

      // hover detection (mouse only moved)
      if (pointerX >= 0 && frame % 2 === 0) {
        const hit = pick(pointerX, pointerY);
        if (hit !== hoverIdx) {
          hoverIdx = hit;
          stateRef.current.onHover?.(hit !== -1 ? nodes[hit].id : null);
          renderer.domElement.style.cursor = hit !== -1 ? "pointer" : dragging ? "grabbing" : "grab";
        }
      }

      // label overlay (direct DOM, no React re-render)
      const label = labelRef.current;
      if (label) {
        const sel = stateRef.current.selectedId;
        const selIdx = sel != null ? idToIdx.get(sel) : undefined;
        const showIdx = hoverIdx !== -1 ? hoverIdx : selIdx !== undefined ? selIdx : -1;
        if (showIdx !== -1) {
          const node = nodes[showIdx];
          label.textContent = `${node.label} · ${Math.round(node.size * 10) / 10}`;
          label.style.opacity = "1";
          label.style.left = `${projected[showIdx * 2] + 14}px`;
          label.style.top = `${projected[showIdx * 2 + 1] - 10}px`;
        } else {
          label.style.opacity = "0";
        }
      }

      if (frame % 20 === 0) applyColors();

      // fps meter
      fpsCount += 1;
      const now = performance.now();
      if (now - fpsTime >= 1000) {
        if (fpsRef.current) {
          fpsRef.current.textContent = `${Math.round((fpsCount * 1000) / (now - fpsTime))} FPS`;
        }
        fpsCount = 0;
        fpsTime = now;
      }

      geometry.attributes.position.needsUpdate = true;
      edgeGeometry.attributes.position.needsUpdate = true;
      renderer.render(scene, camera);
    };
    applyColors();
    loop();

    return () => {
      cancelAnimationFrame(raf);
      resizeObserver.disconnect();
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      renderer.domElement.removeEventListener("wheel", onWheel);
      renderer.domElement.removeEventListener("click", onClick);
      geometry.dispose();
      edgeGeometry.dispose();
      material.dispose();
      edgeMaterial.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === mount) {
        mount.removeChild(renderer.domElement);
      }
    };
  }, [nodes, edges, height]);

  if (nodes.length === 0) return null;

  return (
    <div className={className} style={{ position: "relative", height }} ref={mountRef}>
      <div
        ref={labelRef}
        aria-hidden
        style={{
          position: "absolute",
          opacity: 0,
          pointerEvents: "none",
          transition: "opacity 120ms",
          zIndex: 10,
        }}
        className="mono text-[10px] px-2 py-1 rounded-sm bg-card border border-pos text-pos whitespace-nowrap"
      />
      <div className="absolute bottom-2 right-2 z-10 flex items-center gap-2">
        <span className="mono text-[9px] text-muted-foreground/60" ref={fpsRef}>
          — FPS
        </span>
      </div>
      <div className="absolute bottom-2 left-2 z-10">
        <span className="mono text-[9px] text-muted-foreground/60">
          Glisser : orbite · Molette : zoom · Clic : sélection
        </span>
      </div>
    </div>
  );
}
