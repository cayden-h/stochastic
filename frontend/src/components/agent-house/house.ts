/**
 * The Agent House: a two-storey clay office, one room per agent, rendered live with three.js.
 *
 * Ported from the team's Figma Make prototype ("The Agent House · 3D V2", frame V3-6 Agents) with the same rooms,
 * props, lighting, camera, materials, and label styling. What changed:
 * - it mounts in a container instead of the window, and cleans up everything it made in `dispose()`;
 * - the agents play the keyframed clips authored in Blender (art/blender/build_agents.py) through an AnimationMixer,
 *   crossfading between states, instead of the prototype's procedural bob; the pointer glance and hop stay;
 * - `message()` sends a glowing note along an arc from one agent's room to another (or out to the controller);
 * - the prototype's STEPS loop runs only when `demo` is on.
 * Pure DOM and three.js: no React here.
 */
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { GTAOPass } from "three/addons/postprocessing/GTAOPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import type { AgentKey, AgentState } from "@/lib/conversation";

export interface HouseOptions {
  /** Run the prototype's canned STEPS loop (the pitch preview). */
  demo?: boolean;
  /** A still scene: no clips, no hop, no travelling notes; it renders only when something changes. */
  reducedMotion?: boolean;
  /** Ambient occlusion pass, on by default as in the prototype. */
  ao?: boolean;
  /** Where the models live; the prototype's public/agents. */
  modelBase?: string;
  /** Called when the demo is paused or played, so the button label can follow. */
  onDemoChange?: (on: boolean) => void;
  /** Called with an agent's key when it is clicked. */
  onAgentClick?: (key: AgentKey) => void;
  /** Called once every model has loaded and the first frame is drawn. */
  onReady?: () => void;
}

export interface House {
  setState(key: AgentKey, state: AgentState, text?: string, opts?: { to?: string }): void;
  /** A note travels from one actor to another. `to`/`from` are scene keys, or "controller" / "gateway". */
  message(from: AgentKey | "controller" | "gateway", to: AgentKey | "controller" | "gateway", seconds?: number): Promise<void>;
  /** A small hop, as when the pointer first touches an agent. */
  hop(key: AgentKey): void;
  demo(on?: boolean): void;
  dispose(): void;
}

export const ROOMS = [
  { key: "brief-reader", name: "Brief Reader", role: "Credit agreement", wall: "#F3DCE8", glow: "#E7A6C9", level: 1, col: 0 },
  { key: "mapper", name: "Mapper", role: "Mapping", wall: "#D3ECEF", glow: "#7FCAD5", level: 1, col: 1 },
  { key: "preparer", name: "Preparer", role: "Draft books", wall: "#DCE3F9", glow: "#93ABF0", level: 0, col: 0 },
  { key: "reviewer", name: "Reviewer", role: "Tie-out + limit", wall: "#E4DCF8", glow: "#B09EEB", level: 0, col: 1 },
] as const satisfies readonly { key: AgentKey; name: string; role: string; wall: string; glow: string; level: number; col: number }[];

const NAMES: Record<string, string> = { controller: "you", gateway: "the gateway" };
for (const r of ROOMS) NAMES[r.key] = r.name;

/** The prototype's demo: walk the pipeline, one agent at a time. */
const STEPS: [AgentKey, AgentState, string][] = [
  ["brief-reader", "working", "Reading the credit agreement"],
  ["brief-reader", "done", "Covenant definitions found"],
  ["mapper", "working", "Mapping the target lines"],
  ["mapper", "asking", "Unsure on \"Financing liability\"."],
  ["preparer", "working", "Drafting the combined books"],
  ["reviewer", "working", "Tie-out and limit test"],
  ["reviewer", "done", "Checks pass"],
];

interface Agent {
  key: AgentKey; name: string; glow: string;
  m: THREE.Group; pl: THREE.PointLight; baseY: number; baseYaw: number;
  state: AgentState; since: number; hop: number; glowNow: number;
  label: HTMLDivElement; title: HTMLElement; text: HTMLElement;
  mixer: THREE.AnimationMixer | null; clips: Map<string, THREE.AnimationClip>; current: THREE.AnimationAction | null;
  root: THREE.Object3D | null; rootRestY: number; scale: number;
}

interface Flight {
  sprite: THREE.Sprite; trail: THREE.Sprite[]; line: THREE.Line; curve: THREE.QuadraticBezierCurve3;
  start: number; seconds: number; resolve: () => void;
}

export function createHouse(container: HTMLElement, options: HouseOptions = {}): House {
  const { reducedMotion = false, ao: useAO = true, modelBase = "/agents" } = options;
  let W = Math.max(1, container.clientWidth), H = Math.max(1, container.clientHeight);
  const disposables: { dispose(): void }[] = [];
  const track = <T extends { dispose(): void }>(x: T): T => { disposables.push(x); return x; };

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setClearColor(0xffffff, 1);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(W, H);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.NoToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.domElement.className = "agent-house-canvas";
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = null;
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  const envRT = pmrem.fromScene(room, 0.04);
  scene.environment = envRT.texture;
  scene.environmentIntensity = 0.42;
  disposables.push(envRT, pmrem, { dispose: () => room.dispose() });

  // ---------- palette ----------
  const C = { trim: "#F7F4EE", wood: "#E9D5AA", woodEdge: "#DDC497", woodDark: "#CDB07D", white: "#F8F6F1", sage: "#CBD8CB", ink: "#2F4237", leaf: ["#5E8250", "#6E9459", "#7FA466", "#8DB273"] };
  type MatOpts = THREE.MeshPhysicalMaterialParameters;
  const clay = (color: THREE.ColorRepresentation, o: MatOpts = {}) => new THREE.MeshPhysicalMaterial({ color, roughness: 0.72, metalness: 0, sheen: 0.35, sheenRoughness: 0.8, sheenColor: new THREE.Color("#ffffff"), ...o });
  const matte = (color: THREE.ColorRepresentation, o: THREE.MeshStandardMaterialParameters = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.92, metalness: 0, ...o });
  function add<T extends THREE.Object3D>(mesh: T, parent: THREE.Object3D = scene): T { mesh.castShadow = true; mesh.receiveShadow = true; parent.add(mesh); return mesh; }
  function box(w: number, h: number, d: number, r: number, mat: THREE.Material, x: number, y: number, z: number, parent?: THREE.Object3D) { const m = new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 5, Math.min(r, w / 2 - 1e-3, h / 2 - 1e-3, d / 2 - 1e-3)), mat); m.position.set(x, y, z); return add(m, parent); }
  function cyl(rt: number, rb: number, h: number, mat: THREE.Material, x: number, y: number, z: number, parent?: THREE.Object3D, seg = 32) { const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), mat); m.position.set(x, y, z); return add(m, parent); }

  // ---------- textures ----------
  function woodTexture() {
    const c = document.createElement("canvas"); c.width = 1024; c.height = 1024; const g = c.getContext("2d")!;
    const n = 8, pw = 1024 / n;
    for (let i = 0; i < n; i++) {
      const v = [0, 6, -4, 3, -7, 5, -2, 4][i];
      g.fillStyle = `rgb(${236 + v},${218 + v},${178 + v})`; g.fillRect(i * pw, 0, pw, 1024);
      for (let k = 0; k < 40; k++) { g.strokeStyle = `rgba(170,130,70,${0.02 + Math.random() * 0.03})`; g.lineWidth = 1 + Math.random() * 2; const x = i * pw + Math.random() * pw; g.beginPath(); g.moveTo(x, 0); g.bezierCurveTo(x + 6, 300, x - 6, 700, x + 3, 1024); g.stroke(); }
      const cut = (i * 397) % 1024; g.fillStyle = "rgba(150,115,60,0.18)"; g.fillRect(i * pw, cut, pw, 3);
      g.fillStyle = "rgba(150,115,60,0.22)"; g.fillRect(i * pw, 0, 3, 1024);
    }
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8; return t;
  }
  function radial(color: THREE.ColorRepresentation, inner = 0.0) {
    const c = document.createElement("canvas"); c.width = c.height = 256; const g = c.getContext("2d")!;
    const gr = g.createRadialGradient(128, 128, 0, 128, 128, 128); const col = new THREE.Color(color);
    const rgb = `${Math.round(col.r * 255)},${Math.round(col.g * 255)},${Math.round(col.b * 255)}`;
    gr.addColorStop(inner, `rgba(${rgb},1)`); gr.addColorStop(0.45, `rgba(${rgb},0.45)`); gr.addColorStop(1, `rgba(${rgb},0)`);
    g.fillStyle = gr; g.fillRect(0, 0, 256, 256); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
  }
  const WOOD = woodTexture();

  // ---------- dimensions ----------
  const RW = 4.2, RD = 3.3, T = 0.16, SLAB = 0.24;
  const RHS = [3.1, 2.35];                  // ground floor is taller so it reads under the slab
  const LV = [0, RHS[0] + SLAB];           // floor top of each level
  const colX = (c: number) => c * (RW + T); // left interior edge of each column
  const BW = 2 * RW + T;                    // building interior width
  const DOOR = { z0: 1.95, z1: 2.85, h: 2.05 };

  // ground + base
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), new THREE.ShadowMaterial({ opacity: 0.10 }));
  ground.rotation.x = -Math.PI / 2; ground.position.y = -0.3; ground.receiveShadow = true; scene.add(ground);
  box(BW + 2 * T + 0.1, 0.3, RD + T + 0.1, 0.06, clay(C.woodEdge), BW / 2, -0.15, (RD - T) / 2);
  box(BW + 2 * T, SLAB, RD + T, 0.06, clay(C.woodEdge), BW / 2, LV[1] - SLAB / 2, (RD - T) / 2);

  function floorPlane(x0: number, y: number, w: number, d: number) {
    const t = WOOD.clone(); t.needsUpdate = true; t.repeat.set(w / 2.2, d / 2.2);
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), new THREE.MeshStandardMaterial({ map: t, roughness: 0.7, color: "#FFFFFF" }));
    m.rotation.x = -Math.PI / 2; m.position.set(x0 + w / 2, y + 0.002, d / 2); m.receiveShadow = true; scene.add(m);
  }

  // ---------- more textures ----------
  function canvasTex(w: number, h: number, draw: (g: CanvasRenderingContext2D, w: number, h: number) => void) { const c = document.createElement("canvas"); c.width = w; c.height = h; draw(c.getContext("2d")!, w, h); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t; }
  const rr = (g: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) => { g.beginPath(); g.roundRect(x, y, w, h, r); g.fill(); };
  const TEX = {
    cork: canvasTex(512, 360, (g, w, h) => {
      g.fillStyle = "#E2C79C"; g.fillRect(0, 0, w, h);
      for (let i = 0; i < 900; i++) { g.fillStyle = `rgba(150,110,60,${Math.random() * 0.12})`; g.fillRect(Math.random() * w, Math.random() * h, 2, 2); }
      const papers: [number, number, number, number, string, number][] = [[40, 40, 120, 150, "#FFFFFF", -4], [190, 30, 130, 100, "#F7DDE9", 3], [345, 50, 120, 140, "#FFFFFF", -2], [70, 210, 150, 110, "#FDF3D6", 2], [260, 170, 110, 150, "#FFFFFF", -3], [390, 220, 90, 100, "#E5F0E3", 4]];
      for (const [x, y, pw, ph, c, r] of papers) {
        g.save(); g.translate(x + pw / 2, y + ph / 2); g.rotate(r * Math.PI / 180);
        g.fillStyle = "rgba(80,60,30,0.18)"; g.fillRect(-pw / 2 + 4, -ph / 2 + 5, pw, ph);
        g.fillStyle = c; g.fillRect(-pw / 2, -ph / 2, pw, ph);
        g.fillStyle = "rgba(70,80,75,0.35)"; for (let l = 0; l < 6; l++) g.fillRect(-pw / 2 + 12, -ph / 2 + 18 + l * 16, pw * (0.5 + ((l * 37) % 40) / 100), 4);
        g.fillStyle = "#D87BA6"; g.beginPath(); g.arc(0, -ph / 2 + 8, 6, 0, 7); g.fill(); g.restore();
      }
    }),
    map: canvasTex(640, 420, (g, w, h) => {
      g.fillStyle = "#F5F0E4"; g.fillRect(0, 0, w, h);
      g.fillStyle = "#CFE2C2";
      ([[120, 130, 90, 70], [300, 110, 120, 60], [470, 160, 80, 90], [200, 290, 110, 60], [430, 320, 90, 50]] as const).forEach(([x, y, a, b]) => { g.beginPath(); g.ellipse(x, y, a, b, 0.3, 0, 7); g.fill(); });
      g.strokeStyle = "rgba(120,140,130,0.25)"; g.lineWidth = 1; for (let i = 1; i < 8; i++) { g.beginPath(); g.moveTo(i * 80, 0); g.lineTo(i * 80, h); g.stroke(); } for (let i = 1; i < 6; i++) { g.beginPath(); g.moveTo(0, i * 70); g.lineTo(w, i * 70); g.stroke(); }
      const pts: [number, number][] = [[90, 120], [210, 200], [330, 100], [460, 170], [520, 320], [250, 300], [120, 330]];
      g.strokeStyle = "#3F98A6"; g.lineWidth = 5; g.setLineDash([14, 10]);
      ([[0, 1], [1, 2], [2, 3], [3, 4], [1, 5], [5, 6], [5, 4]] as const).forEach(([a, b]) => { g.beginPath(); g.moveTo(...pts[a]); g.lineTo(...pts[b]); g.stroke(); });
      g.setLineDash([]);
      pts.forEach(([x, y], i) => { g.fillStyle = i === 3 ? "#E79BC0" : "#3F98A6"; g.beginPath(); g.arc(x, y, 12, 0, 7); g.fill(); g.fillStyle = "#fff"; g.beginPath(); g.arc(x, y, 5, 0, 7); g.fill(); });
    }),
    chart: canvasTex(560, 380, (g) => {
      g.fillStyle = "#FFFFFF"; g.fillRect(0, 0, 560, 380);
      g.strokeStyle = "#B7C0CF"; g.lineWidth = 3; g.beginPath(); g.moveTo(50, 40); g.lineTo(50, 320); g.lineTo(520, 320); g.stroke();
      const bars = [90, 130, 120, 170, 200, 240]; bars.forEach((v, i) => { g.fillStyle = i === 5 ? "#7F98E6" : "#BCCBF4"; rr(g, 80 + i * 72, 320 - v, 44, v, 8); });
      g.strokeStyle = "#E79BC0"; g.lineWidth = 5; g.beginPath(); bars.forEach((v, i) => { const x = 102 + i * 72, y = 300 - v - 20; if (i) g.lineTo(x, y); else g.moveTo(x, y); }); g.stroke();
      g.fillStyle = "rgba(70,80,100,0.35)"; rr(g, 60, 345, 160, 10, 5); rr(g, 330, 345, 120, 10, 5);
    }),
    gauge: canvasTex(400, 400, (g) => {
      g.fillStyle = "#FBF8F1"; g.beginPath(); g.arc(200, 200, 196, 0, 7); g.fill();
      const seg: [string, number, number][] = [["#BFE2C6", Math.PI * 0.8, Math.PI * 1.55], ["#F5E2A8", Math.PI * 1.55, Math.PI * 1.9], ["#F2BACF", Math.PI * 1.9, Math.PI * 2.2]];
      g.lineWidth = 34; seg.forEach(([c, a, b]) => { g.strokeStyle = c; g.beginPath(); g.arc(200, 210, 135, a, b); g.stroke(); });
      g.strokeStyle = "#8C948D"; g.lineWidth = 4; for (let i = 0; i <= 10; i++) { const a = Math.PI * 0.8 + i * (Math.PI * 1.4 / 10); g.beginPath(); g.moveTo(200 + Math.cos(a) * 100, 210 + Math.sin(a) * 100); g.lineTo(200 + Math.cos(a) * 112, 210 + Math.sin(a) * 112); g.stroke(); }
      const na = Math.PI * 1.32; g.strokeStyle = "#2F4237"; g.lineWidth = 9; g.lineCap = "round"; g.beginPath(); g.moveTo(200, 210); g.lineTo(200 + Math.cos(na) * 120, 210 + Math.sin(na) * 120); g.stroke();
      g.fillStyle = "#2F4237"; g.beginPath(); g.arc(200, 210, 16, 0, 7); g.fill();
    }),
    clock: canvasTex(300, 300, (g) => {
      g.fillStyle = "#FFFFFF"; g.beginPath(); g.arc(150, 150, 148, 0, 7); g.fill();
      g.fillStyle = "#9AA59C"; for (let i = 0; i < 12; i++) { const a = i * Math.PI / 6; g.beginPath(); g.arc(150 + Math.cos(a) * 118, 150 + Math.sin(a) * 118, i % 3 ? 4 : 8, 0, 7); g.fill(); }
      g.strokeStyle = "#2F4237"; g.lineCap = "round"; g.lineWidth = 10; g.beginPath(); g.moveTo(150, 150); g.lineTo(150 + 55, 150 - 40); g.stroke();
      g.lineWidth = 6; g.beginPath(); g.moveTo(150, 150); g.lineTo(150 - 20, 150 - 95); g.stroke();
      g.fillStyle = "#B09EEB"; g.beginPath(); g.arc(150, 150, 10, 0, 7); g.fill();
    }),
    checklist: canvasTex(300, 400, (g, w, h) => {
      g.fillStyle = "#FFFFFF"; g.fillRect(0, 0, w, h);
      for (let i = 0; i < 6; i++) {
        const y = 70 + i * 52; g.strokeStyle = "#B9C2BB"; g.lineWidth = 4; g.strokeRect(30, y - 16, 30, 30);
        if (i < 4) { g.strokeStyle = "#6DB487"; g.lineWidth = 7; g.beginPath(); g.moveTo(34, y); g.lineTo(44, y + 10); g.lineTo(62, y - 18); g.stroke(); }
        g.fillStyle = "rgba(70,80,75,0.35)"; rr(g, 80, y - 6, 120 + ((i * 41) % 70), 12, 6);
      }
    }),
    globe: canvasTex(512, 256, (g, w, h) => {
      g.fillStyle = "#BFDDE7"; g.fillRect(0, 0, w, h); g.fillStyle = "#BFD9A8";
      ([[80, 90, 60, 45], [150, 170, 35, 50], [270, 80, 70, 40], [300, 160, 40, 45], [420, 110, 55, 35], [440, 200, 30, 20]] as const).forEach(([x, y, a, b]) => { g.beginPath(); g.ellipse(x, y, a, b, 0.4, 0, 7); g.fill(); });
    }),
  };

  // ---------- props ----------
  function windowOnWall(cx: number, cy: number, z: number, w = 1.4, h = 0.95) {
    const g = new THREE.Group(); g.position.set(cx, cy, z); scene.add(g);
    box(w + 0.12, h + 0.12, 0.08, 0.04, clay(C.white), 0, 0, 0.02, g);
    const glass = new THREE.Mesh(new THREE.BoxGeometry(w - 0.04, h - 0.04, 0.02), new THREE.MeshPhysicalMaterial({ color: "#DCEBE4", emissive: "#F2F8F5", emissiveIntensity: 0.55, roughness: 0.15, metalness: 0 }));
    glass.position.z = 0.055; g.add(glass);
    box(0.05, h - 0.04, 0.03, 0.012, clay(C.white), 0, 0, 0.075, g);
    box(w - 0.04, 0.05, 0.03, 0.012, clay(C.white), 0, 0, 0.075, g);
    box(w + 0.3, 0.06, 0.2, 0.025, clay("#EFE6D2"), 0, -h / 2 - 0.08, 0.1, g);
    return g;
  }
  // something flat hung on a wall: side = 'back' (faces +z) or 'side' (faces +x)
  function wallPanel(x: number, y: number, z: number, w: number, h: number, tex: THREE.Texture, side = "back", frameColor = "#D9B582", depth = 0.05) {
    const g = new THREE.Group(); g.position.set(x, y, z); if (side === "side") g.rotation.y = Math.PI / 2; scene.add(g);
    box(w, h, depth, 0.025, clay(frameColor), 0, 0, depth / 2, g);
    const p = new THREE.Mesh(new THREE.PlaneGeometry(w - 0.08, h - 0.08), new THREE.MeshStandardMaterial({ map: tex, roughness: 0.85 })); p.position.z = depth + 0.002; p.receiveShadow = true; g.add(p);
    return g;
  }
  function roundPanel(x: number, y: number, z: number, r: number, tex: THREE.Texture, side = "back", rim = "#F4F1EA") {
    const g = new THREE.Group(); g.position.set(x, y, z); if (side === "side") g.rotation.y = Math.PI / 2; scene.add(g);
    const body = cyl(r, r, 0.07, clay(rim), 0, 0, 0.035, g, 48); body.rotation.x = Math.PI / 2;
    const face = new THREE.Mesh(new THREE.CircleGeometry(r * 0.88, 48), new THREE.MeshStandardMaterial({ map: tex, roughness: 0.6 })); face.position.z = 0.072; g.add(face);
    return g;
  }
  function deskPod(cx: number, y: number, cz: number) {
    box(1.9, 0.3, 0.86, 0.15, clay("#FBFAF6", { sheen: 0.5 }), cx, y + 0.74, cz);
    for (const s of [-0.62, 0.62]) box(0.16, 0.62, 0.5, 0.075, clay("#EEEAE1"), cx + s, y + 0.31, cz);
  }
  const TOP = 0.89;  // desk top height
  const alu = () => new THREE.MeshPhysicalMaterial({ color: "#DADFE5", roughness: 0.32, metalness: 0.35, clearcoat: 0.4 });
  function laptop(cx: number, y: number, cz: number) {
    box(0.6, 0.035, 0.42, 0.015, alu(), cx, y + TOP, cz);
    const lid = box(0.6, 0.4, 0.028, 0.015, alu(), cx, y + TOP + 0.19, cz + 0.2); lid.rotation.x = 0.18;
    const logo = new THREE.Mesh(new THREE.CircleGeometry(0.028, 24), new THREE.MeshStandardMaterial({ color: "#F4F6F8", roughness: 0.3 }));
    logo.position.set(0, 0.02, 0.016); lid.add(logo);
  }
  function monitor(cx: number, y: number, cz: number, rotY = 0) {
    const g = new THREE.Group(); g.position.set(cx, y + TOP, cz); g.rotation.y = rotY; scene.add(g);
    box(0.3, 0.025, 0.2, 0.01, alu(), 0, 0.012, 0, g);
    box(0.06, 0.38, 0.04, 0.02, alu(), 0, 0.2, 0.02, g);
    box(0.85, 0.5, 0.05, 0.03, clay("#E7E9EE"), 0, 0.48, 0.05, g);
  }
  function mug(x: number, y: number, z: number, color = "#FFFFFF") {
    const m = clay(color); cyl(0.065, 0.06, 0.15, m, x, y + 0.075, z);
    const h = new THREE.Mesh(new THREE.TorusGeometry(0.045, 0.014, 12, 24), m); h.position.set(x + 0.075, y + 0.08, z); add(h);
  }
  function paperStack(x: number, y: number, z: number, n = 6, rot = 0) {
    for (let i = 0; i < n; i++) { const p = box(0.32, 0.012, 0.42, 0.004, clay(i % 3 ? "#FFFFFF" : "#F7F1E4"), x + (i % 2) * 0.01, y + 0.006 + i * 0.013, z, scene); p.rotation.y = rot + (i * 0.37 % 0.16) - 0.08; }
  }
  function binders(x: number, y: number, z: number, colors: string[], rotY = 0) {
    const g = new THREE.Group(); g.position.set(x, y, z); g.rotation.y = rotY; scene.add(g);
    colors.forEach((c, i) => { box(0.07, 0.32, 0.26, 0.015, clay(c), i * 0.075, 0.16, 0, g); box(0.035, 0.05, 0.005, 0.002, clay("#FFFFFF"), i * 0.075, 0.24, 0.132, g); });
  }
  function bookPile(x: number, y: number, z: number, colors: string[]) { let h = 0; colors.forEach((c, i) => { const t = 0.05 + (i % 2) * 0.015; const b = box(0.36 - i * 0.02, t, 0.26, 0.012, clay(c), x, y + h + t / 2, z); b.rotation.y = (i * 0.5) % 0.4 - 0.2; h += t; }); }
  function stickyNotes(x: number, y: number, z: number, colors: string[]) { colors.forEach((c, i) => { const s = box(0.1, 0.008, 0.1, 0.003, clay(c), x + i * 0.12, y + 0.004, z + (i % 2) * 0.05); s.rotation.y = i * 0.3; }); }
  function calculator(x: number, y: number, z: number) { box(0.17, 0.03, 0.24, 0.02, clay("#DCE1EA"), x, y + 0.015, z); box(0.13, 0.004, 0.05, 0.002, clay("#BFD0C6"), x, y + 0.032, z - 0.07); for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) box(0.03, 0.012, 0.03, 0.006, clay("#F6F7F9"), x - 0.045 + i * 0.045, y + 0.036, z + j * 0.045); }
  function stamp(x: number, y: number, z: number) { box(0.12, 0.04, 0.08, 0.012, clay("#C9BFEF"), x, y + 0.02, z); cyl(0.015, 0.015, 0.09, clay("#EDE8F7"), x, y + 0.085, z, scene, 10); const k = new THREE.Mesh(new THREE.SphereGeometry(0.04, 20, 14), clay("#B09EEB")); k.position.set(x, y + 0.14, z); add(k); }
  const leafGeo = new THREE.SphereGeometry(1, 24, 16);
  function leaf(parent: THREE.Object3D, x: number, y: number, z: number, sx: number, sy: number, rx: number, ry: number, rz: number, color: string) {
    const m = new THREE.Mesh(leafGeo, clay(color, { roughness: 0.55, sheen: 0.6, sheenColor: new THREE.Color("#E6F2D8") }));
    m.scale.set(sx, sy, sx * 0.35); m.position.set(x, y, z); m.rotation.set(rx, ry, rz); return add(m, parent);
  }
  function pot(parent: THREE.Object3D, r: number, h: number, x: number, y: number, z: number, color = "#F4F1EA") {
    const pts: THREE.Vector2[] = []; for (let i = 0; i <= 10; i++) { const t = i / 10; pts.push(new THREE.Vector2(r * (0.78 + 0.22 * t) + (t > 0.92 ? 0.02 : 0), h * t)); }
    pts.push(new THREE.Vector2(r * 0.9, h));
    const m = new THREE.Mesh(new THREE.LatheGeometry(pts, 40), clay(color, { side: THREE.DoubleSide })); m.position.set(x, y, z); add(m, parent);
    const soil = new THREE.Mesh(new THREE.CircleGeometry(r * 0.92, 32), matte("#8C7458")); soil.rotation.x = -Math.PI / 2; soil.position.set(x, y + h - 0.03, z); parent.add(soil);
  }
  function bigPlant(x: number, y: number, z: number, s = 1, potColor?: string) {
    const g = new THREE.Group(); g.position.set(x, y, z); g.scale.setScalar(s); scene.add(g);
    pot(g, 0.26, 0.5, 0, 0, 0, potColor);
    const stem = matte("#6B7F5B");
    for (let i = 0; i < 13; i++) {
      const a = i * 2.39996, tilt = 0.25 + (i % 4) * 0.12, len = 0.55 + (i % 5) * 0.12;
      const tip = new THREE.Vector3(Math.sin(a) * Math.sin(tilt) * len, 0.5 + Math.cos(tilt) * len, Math.cos(a) * Math.sin(tilt) * len);
      const st = cyl(0.012, 0.016, tip.length(), stem, 0, 0, 0, g, 8);
      st.position.set(tip.x / 2, 0.48 + (tip.y - 0.48) / 2, tip.z / 2); st.lookAt(g.localToWorld(tip.clone())); st.rotateX(Math.PI / 2);
      leaf(g, tip.x * 1.08, tip.y + 0.12, tip.z * 1.08, 0.14, 0.26, Math.sin(a) * tilt * 1.2, a, -Math.cos(a) * tilt * 0.9, C.leaf[i % 4]);
    }
  }
  function tallGrass(x: number, y: number, z: number, potColor = "#EFE7DA") {   // snake plant: upright blades
    const g = new THREE.Group(); g.position.set(x, y, z); scene.add(g);
    pot(g, 0.2, 0.42, 0, 0, 0, potColor);
    for (let i = 0; i < 9; i++) { const a = i * 2.4, r = 0.06 + (i % 3) * 0.03; leaf(g, Math.sin(a) * r, 0.42 + 0.35 + (i % 3) * 0.08, Math.cos(a) * r, 0.06, 0.42 + (i % 3) * 0.08, Math.sin(a) * 0.12, a, -Math.cos(a) * 0.12, C.leaf[(i + 1) % 4]); }
  }
  function cactus(x: number, y: number, z: number) {
    const g = new THREE.Group(); g.position.set(x, y, z); scene.add(g);
    pot(g, 0.08, 0.12, 0, 0, 0, "#F3D2E1");
    const m = clay("#7FA466", { roughness: 0.6 }); const b = new THREE.Mesh(new THREE.CapsuleGeometry(0.05, 0.12, 8, 16), m); b.position.y = 0.22; add(b, g);
    const a = new THREE.Mesh(new THREE.CapsuleGeometry(0.025, 0.05, 6, 12), m); a.position.set(0.06, 0.24, 0); a.rotation.z = -0.6; add(a, g);
  }
  function smallPlant(x: number, y: number, z: number, potColor?: string) {
    const g = new THREE.Group(); g.position.set(x, y, z); scene.add(g);
    pot(g, 0.1, 0.16, 0, 0, 0, potColor);
    for (let i = 0; i < 6; i++) { const a = i * 1.05; leaf(g, Math.sin(a) * 0.06, 0.26, Math.cos(a) * 0.06, 0.05, 0.12, Math.sin(a) * 0.5, a, -Math.cos(a) * 0.5, C.leaf[i % 4]); }
  }
  function hangingPlant(x: number, ceilY: number, z: number, cord = 0.75) {
    const g = new THREE.Group(); g.position.set(x, ceilY, z); scene.add(g);
    cyl(0.008, 0.008, cord, matte("#B79E72"), 0, -cord / 2, 0, g, 6);
    pot(g, 0.13, 0.17, 0, -cord - 0.17, 0);
    for (let v = 0; v < 5; v++) { const a = v * 1.26; for (let k = 0; k < 7; k++) leaf(g, Math.sin(a) * (0.13 + k * 0.012), -cord - 0.05 - k * 0.11, Math.cos(a) * (0.13 + k * 0.012), 0.045, 0.07, 0.3, a + k, 0.4, C.leaf[(v + k) % 4]); }
  }
  function bookshelf(x: number, y: number, z: number, rotY = 0, tall = 1.6) {
    const g = new THREE.Group(); g.position.set(x, y, z); g.rotation.y = rotY; scene.add(g);
    const frame = clay("#F6F2EA");
    for (const sx of [-0.47, 0.47]) box(0.06, tall, 0.36, 0.025, frame, sx, tall / 2, 0, g);
    box(1.0, 0.06, 0.36, 0.025, frame, 0, tall - 0.03, 0, g); box(1.0, 0.1, 0.36, 0.03, frame, 0, 0.05, 0, g);
    const back = new THREE.Mesh(new THREE.BoxGeometry(0.9, tall - 0.1, 0.03), matte("#E6DFD1")); back.position.set(0, tall / 2, -0.16); g.add(back); back.receiveShadow = true;
    const BK = ["#D9CFF3", "#CDE6D6", "#F3D2E1", "#D6E2CC", "#F1E2C2", "#CFDDF2"];
    const shelves: number[] = []; for (let sy = 0.12; sy < tall - 0.4; sy += 0.48) shelves.push(sy);
    shelves.forEach((sy, s) => {
      if (s) box(0.92, 0.04, 0.3, 0.01, frame, 0, sy - 0.02, 0.04, g);
      let bx = -0.42;
      for (let i = 0; i < 9; i++) {
        const w = 0.06 + ((i + s) % 3) * 0.02, h = 0.28 + ((i * 7 + s * 3) % 10) * 0.012; if (bx + w > 0.42) break;
        const b = box(w, h, 0.22, 0.012, clay(BK[(i + s * 2) % 6]), bx + w / 2, sy + h / 2, 0.05, g); if (i === 5 && s === 1) b.rotation.z = 0.25; bx += w + 0.01;
      }
    });
  }
  function cabinet(x: number, y: number, z: number, color = C.sage, h = 0.78) {
    box(0.55, h, 0.5, 0.06, clay(color), x, y + h / 2, z);
    const hd = clay("#F2F5F1"); for (let i = 0; i < 3; i++) box(0.16, 0.03, 0.03, 0.012, hd, x, y + h * (0.25 + i * 0.3), z + 0.255);
  }
  function lowCabinet(x: number, y: number, z: number, w = 1.0, color = "#F3EFE7") { box(w, 0.62, 0.5, 0.06, clay(color), x, y + 0.31, z); box(0.012, 0.5, 0.01, 0.004, clay("#DDD6C8"), x, y + 0.31, z + 0.252); [-0.08, 0.08].forEach((s) => box(0.03, 0.12, 0.03, 0.012, clay("#D9B582"), x + s, y + 0.4, z + 0.26)); }
  function printer(x: number, y: number, z: number) {
    box(0.62, 0.26, 0.46, 0.06, clay("#EEF0F3"), x, y + 0.13, z);
    box(0.5, 0.02, 0.06, 0.008, clay("#C9CED6"), x, y + 0.2, z + 0.23);
    const sheet = box(0.34, 0.006, 0.36, 0.002, clay("#FFFFFF"), x, y + 0.3, z - 0.05); sheet.rotation.x = -0.35;
    box(0.08, 0.02, 0.04, 0.008, clay("#A9D7B4"), x + 0.22, y + 0.265, z + 0.12);
  }
  function floorLamp(x: number, y: number, z: number) {
    const m = clay(C.ink, { roughness: 0.45 });
    cyl(0.16, 0.18, 0.04, m, x, y + 0.02, z);
    cyl(0.018, 0.018, 1.75, m, x, y + 0.9, z, scene, 12);
    const arm = cyl(0.016, 0.016, 0.5, m, x + 0.18, y + 1.86, z + 0.06, scene, 12); arm.rotation.z = -1.05; arm.rotation.y = -0.3;
    const shade = new THREE.Mesh(new THREE.ConeGeometry(0.17, 0.24, 32, 1, true), clay(C.ink, { roughness: 0.45, side: THREE.DoubleSide }));
    shade.position.set(x + 0.4, y + 1.95, z + 0.12); shade.rotation.z = 0.5; add(shade);
    const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.05, 16, 12), new THREE.MeshBasicMaterial({ color: "#FFF4D6" })); bulb.position.set(x + 0.43, y + 1.86, z + 0.12); scene.add(bulb);
    const pl = new THREE.PointLight("#FFE7B8", 1.6, 2.4, 2); pl.position.copy(bulb.position); scene.add(pl);
  }
  function readingLamp(x: number, y: number, z: number) {
    const m = clay("#F2D7E4"); cyl(0.09, 0.1, 0.03, m, x, y + 0.015, z); cyl(0.012, 0.012, 0.42, clay("#E8E3D8"), x, y + 0.22, z, scene, 10);
    const sh = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.15, 0.17, 32, 1, true), clay("#FBF3EA", { side: THREE.DoubleSide, emissive: "#FFF0D6", emissiveIntensity: 0.25 })); sh.position.set(x, y + 0.48, z); add(sh);
    const pl = new THREE.PointLight("#FFE7C4", 0.9, 1.8, 2); pl.position.set(x, y + 0.42, z); scene.add(pl);
  }
  function armchair(x: number, y: number, z: number, rotY: number, color: string) {
    const g = new THREE.Group(); g.position.set(x, y, z); g.rotation.y = rotY; scene.add(g);
    const m = clay(color, { sheen: 0.8, roughness: 0.85 });
    box(0.86, 0.26, 0.78, 0.12, m, 0, 0.3, 0, g);
    box(0.86, 0.62, 0.22, 0.11, m, 0, 0.55, -0.3, g);
    for (const s of [-0.38, 0.38]) box(0.16, 0.42, 0.74, 0.08, m, s, 0.38, 0.02, g);
    box(0.66, 0.1, 0.56, 0.05, clay("#FFFFFF", { sheen: 0.8 }), 0, 0.48, 0.08, g);
    for (const sx of [-0.34, 0.34]) for (const sz of [-0.28, 0.3]) cyl(0.025, 0.02, 0.18, clay("#D9B582"), sx, 0.09, sz, g, 10);
  }
  function sideTable(x: number, y: number, z: number, color = "#F4EEE3", h = 0.55) {
    cyl(0.28, 0.28, 0.05, clay(color), x, y + h, z); cyl(0.04, 0.05, h, clay("#D9B582"), x, y + h / 2, z, scene, 12); cyl(0.18, 0.2, 0.03, clay("#D9B582"), x, y + 0.015, z);
    return y + h + 0.025;
  }
  function globe(x: number, y: number, z: number) {
    cyl(0.1, 0.12, 0.04, clay("#D9B582"), x, y + 0.02, z); cyl(0.012, 0.012, 0.12, clay("#D9B582"), x, y + 0.09, z, scene, 8);
    const s = new THREE.Mesh(new THREE.SphereGeometry(0.2, 40, 24), new THREE.MeshPhysicalMaterial({ map: TEX.globe, roughness: 0.4, clearcoat: 0.5 })); s.position.set(x, y + 0.36, z); s.rotation.z = 0.4; add(s);
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.235, 0.012, 10, 48, Math.PI * 1.3), clay("#D9B582")); ring.position.copy(s.position); ring.rotation.set(0, Math.PI / 2, -0.4 + 2.2); add(ring);
  }
  function scale(x: number, y: number, z: number) {
    const brass = new THREE.MeshPhysicalMaterial({ color: "#E2C58C", roughness: 0.35, metalness: 0.5, clearcoat: 0.3 });
    cyl(0.1, 0.12, 0.03, brass, x, y + 0.015, z); cyl(0.012, 0.012, 0.36, brass, x, y + 0.2, z, scene, 10);
    const beam = box(0.46, 0.02, 0.02, 0.008, brass, x, y + 0.38, z); beam.rotation.z = 0.06;
    for (const s of [-1, 1]) { const px = x + s * 0.22, py = y + 0.38 + s * 0.012 - 0.17; cyl(0.004, 0.004, 0.16, brass, px, py + 0.09, z, scene, 6); cyl(0.09, 0.06, 0.025, brass, px, py, z); }
  }
  function bin(x: number, y: number, z: number, color: string) {
    const b = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.12, 0.34, 32, 1, true), clay(color, { side: THREE.DoubleSide })); b.position.set(x, y + 0.17, z); add(b);
    cyl(0.12, 0.12, 0.01, clay(color), x, y + 0.005, z);
    for (const [dx, dz] of [[0.03, 0.02], [-0.05, -0.01], [0.0, -0.06]]) { const p = new THREE.Mesh(new THREE.IcosahedronGeometry(0.06, 1), clay("#FFFFFF")); p.position.set(x + dx, y + 0.3, z + dz); add(p); }
  }
  function rug(cx: number, y: number, cz: number, color: string, w = 2.6, d = 1.7) { box(w, 0.03, d, 0.012, clay(color, { roughness: 0.95, sheen: 0.8 }), cx, y + 0.015, cz); }
  function roundRug(cx: number, y: number, cz: number, color: string, r = 1.05) { const m = cyl(r, r, 0.03, clay(color, { roughness: 0.95, sheen: 0.8 }), cx, y + 0.015, cz, scene, 64); m.scale.z = 0.75; }
  function frontDoor(y: number, z: number) {   // closed door on the inside of the left exterior wall
    const g = new THREE.Group(); g.position.set(0.0, y, z); g.rotation.y = Math.PI / 2; scene.add(g);
    const trim = clay(C.white);
    box(0.08, 2.22, 0.06, 0.02, trim, -0.52, 1.11, 0.03, g); box(0.08, 2.22, 0.06, 0.02, trim, 0.52, 1.11, 0.03, g); box(1.12, 0.08, 0.06, 0.02, trim, 0, 2.2, 0.03, g);
    box(0.96, 2.14, 0.06, 0.03, clay("#BCD0C0"), 0, 1.08, 0.04, g);
    [[0, 1.55], [0, 0.65]].forEach(([px, py]) => box(0.7, 0.62, 0.02, 0.02, clay("#C9DACC"), px, py, 0.075, g));
    const k = new THREE.Mesh(new THREE.SphereGeometry(0.04, 16, 12), new THREE.MeshPhysicalMaterial({ color: "#E2C58C", metalness: 0.6, roughness: 0.3 })); k.position.set(0.36, 1.05, 0.11); add(k, g);
    box(0.9, 0.02, 0.5, 0.01, clay("#E8D9B8", { roughness: 0.95 }), 0, 0.01, 0.3, g);   // door mat
  }

  // ---------- agents ----------
  const agents: Agent[] = [];
  const gltf = new GLTFLoader();
  let disposed = false;
  const clock = new THREE.Clock();
  let dirty = true, raf = 0, last = 0;
  let pending = ROOMS.length;
  const overlay = document.createElement("div"); overlay.className = "agent-house-overlay";
  container.appendChild(overlay);

  function agentAt(key: AgentKey, cx: number, y: number, cz: number, size = 1.12) {
    const r = ROOMS.find((x) => x.key === key)!;
    // the 3D model built in Blender (front faces +Z), scaled so its larger side is `size`
    const m = new THREE.Group(); m.position.set(cx, y + 0.66 + size / 2, cz); scene.add(m);
    const pl = new THREE.PointLight(r.glow, 1.6, 2.4, 2); pl.position.set(cx, y + 1.3, cz - 0.6); scene.add(pl);   // behind the agent, so it lights the wall, not the face
    const label = document.createElement("div"); label.className = "agent-house-label"; label.dataset.state = "idle"; label.style.setProperty("--tint", r.glow);
    label.innerHTML = `<div class="agent-house-bubble"><b></b><span></span></div><div class="agent-house-pill"><i></i><b>${r.name}</b><em>· ${r.role}</em></div>`;
    overlay.appendChild(label);
    const a: Agent = {
      key, name: r.name, glow: r.glow, m, pl, baseY: m.position.y, baseYaw: 0, state: "idle", since: 0, hop: 0, glowNow: 1.2,
      label, title: label.querySelector(".agent-house-bubble b")!, text: label.querySelector(".agent-house-bubble span")!,
      mixer: null, clips: new Map(), current: null, root: null, rootRestY: 0, scale: 1,
    };
    agents.push(a);
    gltf.load(`${modelBase}/${key}.glb`, (g) => {
      if (disposed) { disposeTree(g.scene); return; }
      const model = g.scene;
      model.updateMatrixWorld(true);
      // Bounds from the bind pose: a skinned mesh's own box needs bone matrices that exist only after a first render.
      const bb = new THREE.Box3();
      model.traverse((o) => {
        const mesh = o as THREE.Mesh;
        if (mesh.isMesh) { mesh.geometry.computeBoundingBox(); bb.union(mesh.geometry.boundingBox!.clone().applyMatrix4(mesh.matrixWorld)); }
      });
      const sz = bb.getSize(new THREE.Vector3()), c = bb.getCenter(new THREE.Vector3());
      const k = size / Math.max(sz.x, sz.y); model.scale.setScalar(k); model.position.copy(c).multiplyScalar(-k);
      model.traverse((o) => {
        const mesh = o as THREE.Mesh;
        if (mesh.isMesh) {
          mesh.castShadow = mesh.receiveShadow = true; mesh.frustumCulled = false;
          const mat = mesh.material as THREE.MeshPhysicalMaterial; mat.roughness = 0.5; mat.envMapIntensity = 0.8;
        }
      });
      m.add(model);
      a.scale = k;
      a.root = model.getObjectByName("root") ?? null;
      if (a.root) { model.updateMatrixWorld(true); a.rootRestY = a.root.getWorldPosition(new THREE.Vector3()).y; }
      for (const clip of g.animations) a.clips.set(clip.name, clip);
      if (!reducedMotion && g.animations.length) {
        a.mixer = new THREE.AnimationMixer(model);
        a.mixer.addEventListener("finished", (e) => {
          // `done` plays once; then the agent rests in its idle loop with the done bubble still up.
          if ((e as unknown as { action: THREE.AnimationAction }).action === a.current && a.state === "done") playClip(a, "idle", 0.6);
        });
        playClip(a, a.state, 0);
      }
      if (--pending === 0) requestAnimationFrame(() => options.onReady?.());
      invalidate();
    }, undefined, () => { if (--pending === 0) options.onReady?.(); });
  }

  function playClip(a: Agent, state: string, fade = 0.35) {
    if (!a.mixer) return;
    const clip = a.clips.get(state) ?? a.clips.get("idle");
    if (!clip) return;
    const next = a.mixer.clipAction(clip);
    if (a.current === next && next.isRunning()) return;
    next.reset();
    if (clip.name === "done") { next.setLoop(THREE.LoopOnce, 1); next.clampWhenFinished = true; }
    else { next.setLoop(THREE.LoopRepeat, Infinity); next.time = clip.name === "idle" ? (agents.indexOf(a) * 1.7) % clip.duration : 0; }
    next.enabled = true; next.setEffectiveTimeScale(1); next.setEffectiveWeight(1);
    next.play();
    if (a.current && a.current !== next && fade > 0) next.crossFadeFrom(a.current, fade, false);
    else if (a.current && a.current !== next) a.current.stop();
    a.current = next;
  }

  // ---------- rooms ----------
  const R: Record<string, { x0: number; y: number; RH: number }> = {};
  for (const r of ROOMS) {
    const x0 = colX(r.col), y = LV[r.level], RH = RHS[r.level], wall = matte(r.wall), trim = clay(C.trim);
    floorPlane(x0, y, RW, RD);
    const bw = RW + (r.col === 0 ? T : 0), bx = x0 + RW / 2 - (r.col === 0 ? T / 2 : 0);
    box(bw, RH, T, 0.03, wall, bx, y + RH / 2, -T / 2);
    box(bw + 0.02, 0.06, T + 0.04, 0.02, trim, bx, y + RH + 0.03, -T / 2);
    box(RW, 0.1, 0.03, 0.012, trim, x0 + RW / 2, y + 0.05, 0.015);
    if (r.col === 0) {
      box(T, RH, RD, 0.03, wall, -T / 2, y + RH / 2, RD / 2);
      box(T + 0.04, 0.06, RD + 0.02, 0.02, trim, -T / 2, y + RH + 0.03, RD / 2);
      box(0.03, 0.1, RD, 0.012, trim, 0.015, y + 0.05, RD / 2);
    } else {
      // divider with a doorway through to the left room
      const dx = x0 - T / 2, zb = -T, zf = RD;
      box(T, RH, DOOR.z0 - zb, 0.03, wall, dx, y + RH / 2, (zb + DOOR.z0) / 2);
      box(T, RH, zf - DOOR.z1, 0.03, wall, dx, y + RH / 2, (DOOR.z1 + zf) / 2);
      box(T, RH - DOOR.h, DOOR.z1 - DOOR.z0 + 0.02, 0.02, wall, dx, y + DOOR.h + (RH - DOOR.h) / 2, (DOOR.z0 + DOOR.z1) / 2);
      for (const fx of [x0 + 0.012, x0 - T - 0.012]) {
        box(0.03, DOOR.h + 0.06, 0.07, 0.012, trim, fx, y + (DOOR.h + 0.06) / 2, DOOR.z0 - 0.035);
        box(0.03, DOOR.h + 0.06, 0.07, 0.012, trim, fx, y + (DOOR.h + 0.06) / 2, DOOR.z1 + 0.035);
        box(0.03, 0.07, DOOR.z1 - DOOR.z0 + 0.14, 0.012, trim, fx, y + DOOR.h + 0.035, (DOOR.z0 + DOOR.z1) / 2);
      }
      box(T + 0.04, 0.06, RD + T + 0.02, 0.02, trim, dx, y + RH + 0.03, (RD - T) / 2);
      box(0.03, 0.1, DOOR.z0, 0.012, trim, x0 + 0.015, y + 0.05, DOOR.z0 / 2);
      box(0.03, 0.1, RD - DOOR.z1, 0.012, trim, x0 + 0.015, y + 0.05, (DOOR.z1 + RD) / 2);
    }
    R[r.key] = { x0, y, RH };
  }

  // Brief Reader: a reading nook. Armchair, pinboard of clauses, binders, paper piles.
  { const { x0, y } = R["brief-reader"];
    rug(x0 + 2.25, y, 1.8, "#F1CFE0", 2.3, 1.5);
    windowOnWall(x0 + 2.75, y + 1.45, 0.0, 1.3, 0.9);
    wallPanel(x0 + 0.02, y + 1.45, 1.45, 1.2, 0.85, TEX.cork, "side", "#D9B582");
    bookshelf(x0 + 1.25, y, 0.22, 0, 1.75);
    cactus(x0 + 1.05, y + 1.75, 0.22); smallPlant(x0 + 1.45, y + 1.75, 0.22, "#F3D2E1");
    armchair(x0 + 0.75, y, 2.45, 0.75, "#F2D3E2");
    const st = sideTable(x0 + 0.5, y, 1.55, "#F7EEF2"); readingLamp(x0 + 0.42, st, 1.5); mug(x0 + 0.62, st, 1.68, "#F3D2E1");
    bookPile(x0 + 1.55, y, 2.75, ["#D9CFF3", "#F3D2E1", "#CDE6D6", "#F1E2C2"]);
    paperStack(x0 + 1.95, y, 2.85, 9, 0.3);
    agentAt("brief-reader", x0 + 2.25, y, 1.05);
    deskPod(x0 + 2.25, y, 1.8);
    paperStack(x0 + 1.65, y + TOP - 0.015, 1.75, 7, -0.15); binders(x0 + 2.65, y + TOP - 0.015, 1.72, ["#F3D2E1", "#E7A6C9", "#F7E3EC", "#D9CFF3"], 0.1);
  }
  // Mapper: a planning room. Route map on the wall, globe, sticky notes, snake plant.
  { const { x0, y } = R["mapper"];
    rug(x0 + 2.2, y, 1.85, "#C3E6EB", 3.0, 1.2);
    windowOnWall(x0 + 1.15, y + 1.45, 0.0, 1.2, 0.9);
    wallPanel(x0 + 2.85, y + 1.42, 0.0, 1.55, 1.0, TEX.map, "back", "#F4F1EA", 0.06);
    stickyNotes(x0 + 3.75, y + 1.2, 0.02, []);
    ([["#F7E3A1", 3.75, 1.75], ["#C3E6EB", 3.9, 1.55], ["#F3D2E1", 3.75, 1.35]] as const).forEach(([c, sx, sy]) => { const s = box(0.13, 0.13, 0.012, 0.004, clay(c), x0 + sx, y + sy, 0.01); s.rotation.z = (sx * 7 % 1) * 0.2 - 0.1; });
    tallGrass(x0 + 3.85, y, 0.5, "#D3ECEF");
    cabinet(x0 + 0.4, y, 0.4, "#CFE3E6");
    globe(x0 + 0.4, y + 0.78, 0.4);
    agentAt("mapper", x0 + 2.25, y, 1.05);
    deskPod(x0 + 2.2, y, 1.85); laptop(x0 + 1.7, y, 1.78); mug(x0 + 2.8, y + TOP, 1.72, "#CFE3E6");
    stickyNotes(x0 + 2.55, y + TOP, 1.95, ["#F7E3A1", "#F3D2E1", "#C3E6EB"]);
    bin(x0 + 3.6, y, 2.7, "#CFE3E6");
  }
  // Preparer: the books get drafted here. Monitor, calculator, ledgers, printer, chart.
  { const { x0, y, RH } = R["preparer"];
    rug(x0 + 2.3, y, 1.9, "#CBD7F7", 2.6, 1.7);
    frontDoor(y, 2.35);
    windowOnWall(x0 + 2.75, y + 1.7, 0.0, 1.4, 1.1);
    wallPanel(x0 + 0.95, y + 1.62, 0.0, 1.3, 0.9, TEX.chart, "back", "#F4F1EA", 0.05);
    hangingPlant(x0 + 0.42, y + RH, 1.35, 0.95);
    lowCabinet(x0 + 0.95, y, 0.3, 1.1, "#E3E9FA"); printer(x0 + 0.95, y + 0.62, 0.3);
    binders(x0 + 3.1, y, 2.85, ["#BCCBF4", "#93ABF0", "#E3E9FA", "#CDE6D6", "#BCCBF4"], -0.4);
    agentAt("preparer", x0 + 2.15, y, 1.1);
    deskPod(x0 + 2.3, y, 1.9); monitor(x0 + 1.65, y, 1.75, 0.25); laptop(x0 + 2.75, y, 1.82);
    calculator(x0 + 3.0, y + TOP, 2.05); bookPile(x0 + 1.6, y + TOP - 0.015, 2.05, ["#BCCBF4", "#F1E2C2"]);
    bin(x0 + 0.5, y, 2.95, "#D6DFF8");
  }
  // Reviewer: checks and limits. Gauge, clock, checklist, balance scale, stamp.
  { const { x0, y } = R["reviewer"];
    roundRug(x0 + 2.2, y, 1.9, "#D9CEF6", 1.25);
    floorLamp(x0 + 3.2, y, 0.45);
    windowOnWall(x0 + 2.25, y + 1.7, 0.0, 1.4, 1.1);
    roundPanel(x0 + 0.85, y + 1.75, 0.0, 0.45, TEX.gauge, "back", "#F4F1EA");
    roundPanel(x0 + 0.02, y + 2.45, 1.0, 0.24, TEX.clock, "side", "#E4DCF8");
    wallPanel(x0 + 0.02, y + 1.45, 1.0, 0.42, 0.56, TEX.checklist, "side", "#C9BFEF", 0.03);
    bigPlant(x0 + 3.8, y, 1.45, 1.0, "#E4DCF8");
    const st = sideTable(x0 + 3.45, y, 2.75, "#EFEAFB", 0.6); scale(x0 + 3.45, st, 2.75);
    agentAt("reviewer", x0 + 2.25, y, 1.1);
    deskPod(x0 + 2.2, y, 1.9); laptop(x0 + 1.7, y, 1.83); stamp(x0 + 2.75, y + TOP, 1.9); paperStack(x0 + 2.95, y + TOP - 0.015, 1.75, 4, 0.2); mug(x0 + 2.55, y + TOP, 2.1, "#E4DCF8");
  }

  // ---------- stairs (outside, right) ----------
  { const sx = BW + T + 0.08, sw = 1.0, n = 15, rise = LV[1] / n, run = (RD + T - 0.1) / n, m = clay("#EAD7AE");
    for (let i = 0; i < n; i++) { const h = rise * (i + 1); box(sw, h, run + 0.01, 0.03, m, sx + sw / 2, h / 2, RD - (i + 0.5) * run, scene); }
    const rail = clay(C.white);
    const p0 = new THREE.Vector3(sx + sw - 0.05, rise + 0.85, RD - 0.5 * run), p1 = new THREE.Vector3(sx + sw - 0.05, LV[1] + 0.85, -T + 0.1);
    const len = p0.distanceTo(p1); const rail0 = cyl(0.03, 0.03, len, rail, 0, 0, 0, scene, 12);
    rail0.position.copy(p0.clone().add(p1).multiplyScalar(0.5)); rail0.lookAt(p1); rail0.rotateX(Math.PI / 2);
    for (let i = 0; i < n; i += 3) { const h = rise * (i + 1); cyl(0.022, 0.022, 0.85, rail, sx + sw - 0.05, h + 0.425, RD - (i + 0.5) * run, scene, 10); }
    cyl(0.022, 0.022, 0.85, rail, sx + sw - 0.05, LV[1] + 0.425, -T + 0.1, scene, 10);
  }

  // ---------- lights ----------
  scene.add(new THREE.HemisphereLight("#FFFFFF", "#E9DEC8", 0.75));
  const sun = new THREE.DirectionalLight("#FFF6EA", 1.55);
  sun.position.set(-7, 14, 11); sun.target.position.set(4.5, 1.2, 1.5); scene.add(sun, sun.target);
  sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -10, right: 10, top: 10, bottom: -10, near: 1, far: 45 });
  sun.shadow.bias = -0.0003; sun.shadow.normalBias = 0.02; sun.shadow.radius = 4;
  const fill = new THREE.DirectionalLight("#FFF4EC", 0.8); fill.position.set(12, 6, 10); scene.add(fill);

  // ---------- camera ----------
  const camera = new THREE.PerspectiveCamera(20, W / H, 0.5, 200);
  const target = new THREE.Vector3(4.85, 2.6, 1.4);
  const dir = new THREE.Vector3(0.42, 0.4, 1).normalize();
  camera.position.copy(target).addScaledVector(dir, 30.5);
  camera.lookAt(target);
  camera.updateMatrixWorld();
  for (const a of agents) { a.baseYaw = Math.atan2(dir.x, dir.z) * 0.85; a.m.rotation.y = a.baseYaw; }

  // ---------- live render ----------
  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  let aoPass: GTAOPass | null = null;
  if (useAO) {
    aoPass = new GTAOPass(scene, camera, W, H); aoPass.blendIntensity = 1.0;
    aoPass.updateGtaoMaterial({ radius: 0.45, distanceExponent: 1.4, thickness: 1.2, scale: 1, samples: 16 });
    aoPass.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 6, rings: 2, samples: 16 });
    composer.addPass(aoPass);
  }
  composer.addPass(new OutputPass());

  const BASE_DIST = 30.5, BASE_ASPECT = 1600 / 1100;
  function resize() {
    W = Math.max(1, container.clientWidth); H = Math.max(1, container.clientHeight);
    renderer.setSize(W, H); composer.setSize(W, H);
    camera.aspect = W / H;
    camera.position.copy(target).addScaledVector(dir, BASE_DIST * Math.max(1, BASE_ASPECT / camera.aspect));
    camera.updateProjectionMatrix();
    invalidate();
  }
  const ro = new ResizeObserver(resize); ro.observe(container); resize();

  const byKey = (k: string) => agents.find((a) => a.key === k);

  // ---------- notes travelling between rooms ----------
  const dot = track(radial("#FFFFFF"));
  const flights: Flight[] = [];
  // Notes live in their own scene, drawn over the finished frame: the AO pass would print sprites as dark squares.
  const notes = new THREE.Scene();
  const noteGeo = track(new THREE.SphereGeometry(0.1, 20, 14));
  const headOf = (a: Agent, out: THREE.Vector3) => out.copy(a.m.position).setY(a.m.position.y + 0.35);
  function endpoint(k: string, out: THREE.Vector3): THREE.Vector3 | null {
    const a = byKey(k);
    if (a) return headOf(a, out);
    if (k === "controller") return out.set(BW / 2, LV[1] * 0.55, RD + 3.2);   // out the front, toward the person at the screen
    return null;
  }
  function message(from: string, to: string, seconds = 0.95): Promise<void> {
    const p0 = endpoint(from, new THREE.Vector3()), p1 = endpoint(to, new THREE.Vector3());
    if (!p0 || !p1 || reducedMotion || disposed) return Promise.resolve();
    const tint = new THREE.Color(byKey(from)?.glow ?? byKey(to)?.glow ?? "#7FCAD5");
    const ink = tint.clone().offsetHSL(0, 0.12, -0.2);   // the pastel glow alone vanishes on the white card
    const mid = p0.clone().add(p1).multiplyScalar(0.5);
    mid.y += 0.9 + p0.distanceTo(p1) * 0.12; mid.z += 1.2;
    const curve = new THREE.QuadraticBezierCurve3(p0, mid, p1);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: dot, color: tint, transparent: true, depthTest: false, depthWrite: false }));
    sprite.scale.setScalar(0.85); sprite.renderOrder = 10; notes.add(sprite);
    const core = new THREE.Mesh(noteGeo, new THREE.MeshBasicMaterial({ color: ink, transparent: true, depthTest: false }));
    core.renderOrder = 11; sprite.add(core); core.scale.setScalar(1 / 0.85);
    const trail = Array.from({ length: 6 }, (_, i) => {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: dot, color: ink, transparent: true, depthTest: false, depthWrite: false, opacity: 0.55 - i * 0.08 }));
      s.scale.setScalar(0.3 - i * 0.035); s.renderOrder = 9; notes.add(s); return s;
    });
    const lineGeo = new THREE.BufferGeometry().setFromPoints(curve.getPoints(48));
    const line = new THREE.Line(lineGeo, new THREE.LineDashedMaterial({ color: ink, dashSize: 0.18, gapSize: 0.14, transparent: true, opacity: 0, depthTest: false }));
    line.computeLineDistances(); line.renderOrder = 8; notes.add(line);
    return new Promise((resolve) => { flights.push({ sprite, trail, line, curve, start: clock.getElapsedTime(), seconds, resolve }); });
  }
  function endFlight(f: Flight) {
    for (const s of [f.sprite, ...f.trail]) { notes.remove(s); s.material.dispose(); }
    for (const c of f.sprite.children) ((c as THREE.Mesh).material as THREE.Material).dispose();
    notes.remove(f.line); f.line.geometry.dispose(); (f.line.material as THREE.Material).dispose();
    f.resolve();
  }
  function stepFlights(t: number) {
    for (let i = flights.length - 1; i >= 0; i--) {
      const f = flights[i], u = (t - f.start) / f.seconds;
      if (u >= 1.35) { endFlight(f); flights.splice(i, 1); continue; }
      const e = u < 1 ? 1 - Math.pow(1 - u, 2.2) : 1;
      f.sprite.position.copy(f.curve.getPoint(Math.min(1, e)));
      const fade = u < 1 ? 1 : Math.max(0, 1 - (u - 1) / 0.35);
      f.sprite.material.opacity = fade;
      ((f.sprite.children[0] as THREE.Mesh).material as THREE.MeshBasicMaterial).opacity = fade;
      f.trail.forEach((s, k) => { s.position.copy(f.curve.getPoint(Math.max(0, Math.min(1, e - (k + 1) * 0.035)))); s.visible = u < 1; });
      (f.line.material as THREE.LineDashedMaterial).opacity = 0.7 * Math.min(1, u * 3) * (u < 1 ? 1 : Math.max(0, 1 - (u - 1) / 0.35));
    }
  }

  // ---------- state ----------
  function setState(key: AgentKey, state: AgentState, text = "", opts: { to?: string } = {}) {
    const a = byKey(key); if (!a) return;
    const changed = a.state !== state;
    a.state = state; if (changed) a.since = clock.getElapsedTime();
    a.label.dataset.state = state;
    a.title.textContent = state === "talking" && opts.to ? `${a.name.toUpperCase()} · TO ${(NAMES[opts.to] ?? opts.to).toUpperCase()}` : `${a.name.toUpperCase()} · ${state.toUpperCase()}`;
    a.text.textContent = text;
    a.text.title = text;
    if (changed) playClip(a, state);
    invalidate();
  }

  let demoOn = Boolean(options.demo), step = -1, nextStepAt = 0.8;
  function runDemo(t: number) {
    if (!demoOn || t < nextStepAt) return;
    step = (step + 1) % STEPS.length;
    if (step === 0) agents.forEach((a) => setState(a.key, "idle"));
    const [key, state, text] = STEPS[step];
    agents.forEach((a) => { if (a.key !== key && a.state !== "done") setState(a.key, "idle"); });
    setState(key, state, text);
    nextStepAt = t + (state === "asking" ? 3.6 : 2.6);
  }

  // pointer: agents glance toward the cursor and hop when you hover them
  const pointer = new THREE.Vector2(), ray = new THREE.Raycaster(); let hovered: Agent | null = null;
  const canvas = renderer.domElement;
  function onMove(e: PointerEvent) {
    const r = canvas.getBoundingClientRect();
    pointer.set((e.clientX - r.left) / r.width * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(pointer, camera);
    const hit = ray.intersectObjects(agents.map((a) => a.m), true)[0];
    const a = hit ? agents.find((x) => { let o: THREE.Object3D | null = hit.object; while (o) { if (o === x.m) return true; o = o.parent; } return false; }) : undefined;
    if (a && a !== hovered && !reducedMotion) a.hop = 1;
    hovered = a ?? null; canvas.style.cursor = a ? "pointer" : "";
    invalidate();
  }
  function onLeave() { pointer.set(0, 0); hovered = null; canvas.style.cursor = ""; invalidate(); }
  function onClick() {
    if (!hovered) return;
    if (demoOn || options.demo) {
      const order: AgentState[] = ["idle", "working", "asking", "done"];
      api.demo(false);
      setState(hovered.key, order[(order.indexOf(hovered.state) + 1) % order.length], "Clicked in the preview");
    }
    options.onAgentClick?.(hovered.key);
  }
  canvas.addEventListener("pointermove", onMove);
  canvas.addEventListener("pointerleave", onLeave);
  canvas.addEventListener("click", onClick);

  // ---------- animation loop ----------
  const head = new THREE.Vector3(), tmp = new THREE.Vector3();
  function tick() {
    raf = 0;
    if (disposed) return;
    const t = clock.getElapsedTime(), dt = Math.min(0.05, t - last); last = t;
    runDemo(t);
    agents.forEach((a) => {
      let glow = 1.1;
      if (a.state === "working") glow = 1.6 + 1.6 * (0.5 + 0.5 * Math.sin(6 * t));
      if (a.state === "talking") glow = 1.8 + 0.8 * (0.5 + 0.5 * Math.sin(9 * t));
      if (a.state === "asking") glow = 2.6;
      if (a.state === "done") glow = 2.0;
      if (!reducedMotion) {
        a.mixer?.update(dt);
        a.hop = Math.max(0, a.hop - dt * 2.2);
        a.m.position.y = a.baseY + 0.22 * Math.sin(Math.PI * (1 - a.hop)) * (a.hop > 0 ? 1 : 0);
        a.m.rotation.set(-pointer.y * 0.08, a.baseYaw + pointer.x * 0.28, 0);
        a.glowNow += (glow - a.glowNow) * Math.min(1, dt * 6);
      } else {
        a.glowNow = glow;
      }
      a.pl.intensity = a.glowNow;
      // the label rides on the body: the model's root bone carries the clip's bounce
      head.copy(a.m.position); head.y += 0.82;
      if (a.root) { a.root.getWorldPosition(tmp); head.y += (tmp.y - a.rootRestY) - (a.m.position.y - a.baseY); }
      head.project(camera);
      a.label.style.transform = `translate(${(head.x + 1) / 2 * W}px, ${(1 - head.y) / 2 * H}px) translate(-50%, -100%)`;
    });
    stepFlights(t);
    composer.render();
    if (flights.length) { renderer.autoClear = false; renderer.render(notes, camera); renderer.autoClear = true; }
    dirty = false;
    schedule();
  }
  function invalidate() { dirty = true; schedule(); }
  function schedule() {
    if (raf || disposed || document.hidden) return;
    if (reducedMotion && !dirty) return;   // a still scene draws only when something changed
    raf = requestAnimationFrame(tick);
  }
  function onVisibility() { if (!document.hidden) { clock.getDelta(); last = clock.getElapsedTime(); dirty = true; schedule(); } }
  document.addEventListener("visibilitychange", onVisibility);
  schedule();

  function disposeTree(root: THREE.Object3D) {
    root.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (mesh.geometry) mesh.geometry.dispose();
      const mats = mesh.material ? (Array.isArray(mesh.material) ? mesh.material : [mesh.material]) : [];
      for (const m of mats) {
        for (const v of Object.values(m)) if (v instanceof THREE.Texture) v.dispose();
        m.dispose();
      }
    });
  }

  const api: House = {
    setState,
    message: (from, to, seconds) => message(from, to, seconds),
    hop(key) { const a = byKey(key); if (a && !reducedMotion) { a.hop = 1; } invalidate(); },
    demo(on = true) { demoOn = on; options.onDemoChange?.(on); },
    dispose() {
      if (disposed) return;
      disposed = true;
      if (raf) cancelAnimationFrame(raf);
      ro.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
      canvas.removeEventListener("pointermove", onMove);
      canvas.removeEventListener("pointerleave", onLeave);
      canvas.removeEventListener("click", onClick);
      for (const f of flights.splice(0)) endFlight(f);
      for (const a of agents) { a.mixer?.stopAllAction(); if (a.mixer) a.mixer.uncacheRoot(a.mixer.getRoot()); }
      disposeTree(scene);
      for (const t of Object.values(TEX)) t.dispose();
      WOOD.dispose(); leafGeo.dispose();
      aoPass?.dispose();
      composer.dispose();
      for (const d of disposables) d.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      canvas.remove(); overlay.remove();
    },
  };
  return api;
}
