<template>
  <div class="wrap">
    <div class="left">
      <div class="card">
        <div class="h">T0 Topology</div>

        <div class="small" v-if="loading">Loading CSVs… {{ loadProgress }}</div>
        <div class="small" v-else-if="ready">
          Loaded: {{ sats.length }} sats<br />
          T0: <span class="mono">{{ t0Label }}</span>
        </div>
        <div class="small" v-else>Not loaded.</div>

        <div class="divider"></div>

        <div class="h2">Links</div>
        <label class="check">
          <input type="checkbox" v-model="showLinks" :disabled="!ready" />
          <span>Enable links</span>
        </label>

        <div class="row2">
          <div class="label">Mode</div>
          <select class="select" v-model="linkMode" :disabled="!ready || !showLinks">
            <option value="orbit">Same-orbit ring</option>
            <option value="nearest">Nearest neighbors (K)</option>
            <option value="threshold">Distance threshold (km)</option>
          </select>
        </div>

        <div class="row2" v-if="linkMode === 'nearest'">
          <div class="label">K</div>
          <input class="input" type="number" min="1" max="8" v-model.number="nearestK" />
        </div>

        <div class="row2" v-if="linkMode === 'threshold'">
          <div class="label">Threshold (km)</div>
          <input class="input" type="number" min="100" step="50" v-model.number="distKm" />
        </div>

        <button class="btn wide" @click="resetView" :disabled="!ready">Reset view</button>

        <div class="small">
          Orbit grouping inferred from filename: <span class="mono">Sat_&lt;orbit&gt;_&lt;slot&gt;_...</span>
        </div>
      </div>
    </div>

    <div class="center">
      <div ref="host" class="viewport"></div>
    </div>

    <div class="right">
      <div class="card">
        <div class="h">Selection</div>
        <div v-if="selected">
          <div class="kv"><b>ID</b><span class="mono">{{ selected.id }}</span></div>
          <div class="kv"><b>Orbit</b><span>{{ selected.orbit }}</span></div>
          <div class="kv"><b>Slot</b><span>{{ selected.slot }}</span></div>

          <div class="divider"></div>

          <div class="h2">LLA</div>
          <div class="kv"><b>Lat</b><span>{{ fmt(selected.lla_Lat, 6) }}°</span></div>
          <div class="kv"><b>Lon</b><span>{{ fmt(selected.lla_Lon, 6) }}°</span></div>
          <div class="kv"><b>Alt</b><span>{{ fmt(selected.lla_Alt, 3) }} km</span></div>

          <div class="divider"></div>

          <div class="h2">COE</div>
          <div class="kv"><b>a</b><span>{{ fmt(selected.coe_SemiMajorAxis, 6) }} km</span></div>
          <div class="kv"><b>e</b><span>{{ fmt(selected.coe_Eccentricity, 10) }}</span></div>
          <div class="kv"><b>i</b><span>{{ fmt(selected.coe_Inclination, 6) }}°</span></div>
          <div class="kv"><b>RAAN</b><span>{{ fmt(selected.coe_RAAN, 6) }}°</span></div>
          <div class="kv"><b>ω</b><span>{{ fmt(selected.coe_ArgPerigee, 6) }}°</span></div>
          <div class="kv"><b>ν</b><span>{{ fmt(selected.coe_TrueAnomaly, 6) }}°</span></div>
        </div>
        <div v-else class="small">Click a satellite node to inspect.</div>
      </div>

      <div class="card">
        <div class="h">Controls</div>
        <div class="small">
          Left drag: rotate<br />
          Wheel: zoom<br />
          Right drag: pan
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch, markRaw } from "vue";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

type SatT0 = {
  id: string;
  orbit: number;
  slot: number;

  // T0 fields
  utc: string;

  r: [number, number, number]; // km (J2000)
  lla_Lat: number;
  lla_Lon: number;
  lla_Alt: number;

  coe_SemiMajorAxis: number;
  coe_Eccentricity: number;
  coe_Inclination: number;
  coe_RAAN: number;
  coe_ArgPerigee: number;
  coe_TrueAnomaly: number;

  mesh: THREE.Mesh;
};

type Selected = Omit<SatT0, "mesh" | "r"> & { r: [number, number, number] };

const host = ref<HTMLDivElement | null>(null);

const loading = ref(true);
const ready = ref(false);
const loadProgress = ref("");
const t0Label = ref("");

// ✅ 改为 ref，避免 Vue 深代理 THREE.Mesh 导致 renderer 报错
const sats = ref<SatT0[]>([]);
const selected = ref<Selected | null>(null);

// link controls
const showLinks = ref(true);
const linkMode = ref<"orbit" | "nearest" | "threshold">("orbit");
const nearestK = ref(2);
const distKm = ref(2000);

// three
let renderer: THREE.WebGLRenderer | null = null;
let scene: THREE.Scene | null = null;
let camera: THREE.PerspectiveCamera | null = null;
let controls: OrbitControls | null = null;
let raf = 0;
let resizeObs: ResizeObserver | null = null;

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();

let orbitLinkLines = new Map<number, THREE.LineSegments>();


// scale: km -> world units (1000 km = 1 unit)
const KM_TO_UNITS = 1 / 1000;

// 自定义的轨道颜色表
const ORBIT_COLORS = [
  0x4cc9f0, // orbit 6
  0x4ade80, // orbit 7
  0xa78bfa, // orbit 8
  0xfbbf24, // orbit 9（备用）
  0xfb7185, // orbit 10（备用）
];

function colorForOrbit(orbit: number) {
  return ORBIT_COLORS[orbit % ORBIT_COLORS.length];
}


// 你贴出来的 15 个文件名（按需改这里）
const CSV_FILES = [
  "Sat_6_6_ephem_ext.csv",
  "Sat_6_7_ephem_ext.csv",
  "Sat_6_8_ephem_ext.csv",
  "Sat_6_9_ephem_ext.csv",
  "Sat_6_10_ephem_ext.csv",
  "Sat_7_6_ephem_ext.csv",
  "Sat_7_7_ephem_ext.csv",
  "Sat_7_8_ephem_ext.csv",
  "Sat_7_9_ephem_ext.csv",
  "Sat_7_10_ephem_ext.csv",
  "Sat_8_6_ephem_ext.csv",
  "Sat_8_7_ephem_ext.csv",
  "Sat_8_8_ephem_ext.csv",
  "Sat_8_9_ephem_ext.csv",
  "Sat_8_10_ephem_ext.csv",
] as const;

const BASE_URL = "/data/Xingli_xls_15/";

// ---------- utils ----------
function fmt(x: number, digits: number) {
  return Number.isFinite(x) ? x.toFixed(digits) : "-";
}

function parseCsv(text: string): string[][] {
  const clean = (text ?? "").replace(/^\uFEFF/, "");
  const lines = clean.split(/\r?\n/).filter((l) => l.trim().length > 0);
  return lines.map((l) => l.split(",").map((x) => x.trim()));
}

function getColIndexMap(headerRow: string[]) {
  const map = new Map<string, number>();
  headerRow.forEach((name, idx) => map.set(name.replace(/^\uFEFF/, "").trim(), idx));
  return map;
}

function numAt(row: string[], idx: number) {
  if (idx < 0 || idx >= row.length) return NaN;
  const v = Number(row[idx]);
  return Number.isFinite(v) ? v : NaN;
}

function parseOrbitSlotFromFilename(name: string) {
  const m = name.match(/^Sat_(\d+)_(\d+)_/i);
  return {
    orbit: m ? Number(m[1]) : 0,
    slot: m ? Number(m[2]) : 0,
  };
}

// ---------- three ----------
function makeNodeMesh() {
  const geo = new THREE.SphereGeometry(0.09, 20, 20);
  const mat = new THREE.MeshStandardMaterial({
    color: 0xb9d4ff,
    roughness: 0.55,
    metalness: 0.15,
  });
  return new THREE.Mesh(geo, mat);
}

function addLights(s: THREE.Scene) {
  s.add(new THREE.AmbientLight(0xffffff, 0.85));
  const d = new THREE.DirectionalLight(0xffffff, 1.0);
  d.position.set(3, 2, 4);
  s.add(d);
}

function setHighlight(mesh: THREE.Mesh | null) {
  for (const sat of sats.value) {
    const mat = sat.mesh.material as THREE.MeshStandardMaterial;
    mat.emissive.setHex(0x000000);
    mat.color.setHex(0xb9d4ff);
    sat.mesh.scale.setScalar(1);
  }
  if (mesh) {
    const mat = mesh.material as THREE.MeshStandardMaterial;
    mat.emissive.setHex(0x2b5cff);
    mat.color.setHex(0xffffff);
    mesh.scale.setScalar(1.25);
  }
}

function resetView() {
  if (!camera || !controls) return;
  camera.position.set(0, 0, 12);
  controls.target.set(0, 0, 0);
  controls.update();
}

function rebuildLinks() {
  if (!scene) return;

  // 清理旧的轨道连线
  for (const line of orbitLinkLines.values()) {
    scene.remove(line);
    line.geometry.dispose();
    (line.material as THREE.Material).dispose();
  }
  orbitLinkLines.clear();

  if (!showLinks.value) return;
  if (linkMode.value !== "orbit") return;

  // orbit -> sats
  const map = new Map<number, SatT0[]>();
  for (const sat of sats.value) {
    const arr = map.get(sat.orbit) ?? [];
    arr.push(sat);
    map.set(sat.orbit, arr);
  }

  // 每个 orbit 单独一条 LineSegments（非闭环：不连首尾）
for (const [orbit, arr] of map.entries()) {
  if (arr.length < 2) continue;

  arr.sort((a, b) => a.slot - b.slot);

  const positions: number[] = [];
  for (let i = 0; i < arr.length - 1; i++) {
    const a = arr[i].mesh.position;
    const b = arr[i + 1].mesh.position;
    positions.push(a.x, a.y, a.z, b.x, b.y, b.z);
  }

  const geom = new THREE.BufferGeometry();
  geom.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));

  const mat = new THREE.LineBasicMaterial({
    color: colorForOrbit(orbit),
    transparent: true,
    opacity: 0.35,
  });

  const line = new THREE.LineSegments(geom, mat);
  line.frustumCulled = false;

  scene.add(line);
  orbitLinkLines.set(orbit, line);
  }
}

function onPointerDown(ev: PointerEvent) {
  if (!renderer || !camera) return;
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -(((ev.clientY - rect.top) / rect.height) * 2 - 1);

  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(sats.value.map((s) => s.mesh), false);

  if (!hits.length) {
    setHighlight(null);
    selected.value = null;
    return;
  }

  const m = hits[0].object as THREE.Mesh;
  setHighlight(m);

  const ud = m.userData as { id: string };
  const sat = sats.value.find((x) => x.id === ud.id);
  if (!sat) return;

  selected.value = {
    id: sat.id,
    orbit: sat.orbit,
    slot: sat.slot,
    utc: sat.utc,
    r: sat.r,
    lla_Lat: sat.lla_Lat,
    lla_Lon: sat.lla_Lon,
    lla_Alt: sat.lla_Alt,
    coe_SemiMajorAxis: sat.coe_SemiMajorAxis,
    coe_Eccentricity: sat.coe_Eccentricity,
    coe_Inclination: sat.coe_Inclination,
    coe_RAAN: sat.coe_RAAN,
    coe_ArgPerigee: sat.coe_ArgPerigee,
    coe_TrueAnomaly: sat.coe_TrueAnomaly,
  };
}

function animate() {
  if (!renderer || !scene || !camera) return;
  controls?.update();
  renderer.render(scene, camera);
  raf = requestAnimationFrame(animate);
}

// ---------- data: read only first data row (T0) ----------
async function loadT0() {
  loading.value = true;
  ready.value = false;
  loadProgress.value = "";

  // 清空旧数据
  sats.value = [];
  selected.value = null;
  t0Label.value = "";

  // 逐文件加载：失败不中断（保证能看到已成功的节点）
  for (let i = 0; i < CSV_FILES.length; i++) {
    const file = CSV_FILES[i];
    loadProgress.value = `${i + 1}/${CSV_FILES.length} ${file}`;

    try {
      const res = await fetch(BASE_URL + file);
      if (!res.ok) throw new Error(`Fetch failed: ${file} (${res.status})`);

      const text = await res.text();
      const rows = parseCsv(text);
      if (rows.length < 2) throw new Error(`CSV too few rows: ${file}`);

      const header = rows[0];
      const col = getColIndexMap(header);

      const idxUTCG = col.get("UTCG") ?? -1;
      const idxRx = col.get("r_x") ?? -1;
      const idxRy = col.get("r_y") ?? -1;
      const idxRz = col.get("r_z") ?? -1;

      if ([idxUTCG, idxRx, idxRy, idxRz].some((x) => x < 0)) {
        throw new Error(`Missing required cols in ${file}: need UTCG,r_x,r_y,r_z`);
      }

      // first data row (T0)
      const r0 = rows[1];
      const utc = r0[idxUTCG];

      const rx = numAt(r0, idxRx);
      const ry = numAt(r0, idxRy);
      const rz = numAt(r0, idxRz);

      const idxLat = col.get("lla_Lat") ?? -1;
      const idxLon = col.get("lla_Lon") ?? -1;
      const idxAlt = col.get("lla_Alt") ?? -1;

      const idxA = col.get("coe_Semi-major_Axis") ?? -1;
      const idxE = col.get("coe_Eccentricity") ?? -1;
      const idxI = col.get("coe_Inclination") ?? -1;
      const idxRAAN = col.get("coe_RAAN") ?? -1;
      const idxW = col.get("coe_Arg_of_Perigee") ?? -1;
      const idxNu = col.get("coe_True_Anomaly") ?? -1;

      const { orbit, slot } = parseOrbitSlotFromFilename(file);
      const id = file.replace("_ephem_ext.csv", "");

      // ✅ 关键：mesh 不要被 Vue 代理（否则 three render 会报 modelViewMatrix proxy 错误）
      const mesh = markRaw(makeNodeMesh());
      const mat = mesh.material as THREE.MeshStandardMaterial;
      mat.color.setHex(colorForOrbit(orbit));

      mesh.name = "Sat";
      mesh.userData = { id };

      // position in scene
      mesh.position.set(rx * KM_TO_UNITS, ry * KM_TO_UNITS, rz * KM_TO_UNITS);

      // ===== DEBUG: print parsed T0 row =====
      console.groupCollapsed(`[T0] ${file}`);
      console.log("UTCG:", utc);
      console.log("r (km):", { rx, ry, rz });
      console.log("LLA:", {
        lat: numAt(r0, idxLat),
        lon: numAt(r0, idxLon),
        alt: numAt(r0, idxAlt),
      });
      console.log("COE:", {
        a: numAt(r0, idxA),
        e: numAt(r0, idxE),
        i: numAt(r0, idxI),
        raan: numAt(r0, idxRAAN),
        w: numAt(r0, idxW),
        nu: numAt(r0, idxNu),
      });
      console.log("orbit/slot:", { orbit, slot });
      console.groupEnd();

      const sat: SatT0 = {
        id,
        orbit,
        slot,
        utc,
        r: [rx, ry, rz],
        lla_Lat: numAt(r0, idxLat),
        lla_Lon: numAt(r0, idxLon),
        lla_Alt: numAt(r0, idxAlt),
        coe_SemiMajorAxis: numAt(r0, idxA),
        coe_Eccentricity: numAt(r0, idxE),
        coe_Inclination: numAt(r0, idxI),
        coe_RAAN: numAt(r0, idxRAAN),
        coe_ArgPerigee: numAt(r0, idxW),
        coe_TrueAnomaly: numAt(r0, idxNu),
        mesh,
      };

      sats.value.push(sat);
      scene?.add(mesh); // ✅ 成功一个就立刻 add，避免“中途失败导致 0 节点”

      if (!t0Label.value) t0Label.value = utc;
    } catch (err) {
      console.error("[load one file failed]", file, err);
      // 继续下一个文件
    }
  }

  loading.value = false;
  ready.value = sats.value.length > 0;
  loadProgress.value = ready.value ? "done" : "no sats loaded";
}

// reactive rebuild links
watch([showLinks, linkMode, nearestK, distKm], () => {
  if (!ready.value) return;
  rebuildLinks();
});

onMounted(async () => {
  if (!host.value) return;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x070b1a);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(host.value.clientWidth, host.value.clientHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  host.value.appendChild(renderer.domElement);

  camera = new THREE.PerspectiveCamera(45, host.value.clientWidth / host.value.clientHeight, 0.01, 2000);
  camera.position.set(0, 0, 12);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.target.set(0, 0, 0);
  controls.update();

  addLights(scene);

  // stars
  {
    const starCount = 900;
    const positions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {
      positions[i * 3 + 0] = (Math.random() - 0.5) * 80;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 80;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 80;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const m = new THREE.PointsMaterial({ size: 0.05, sizeAttenuation: true, color: 0xffffff });
    scene.add(new THREE.Points(g, m));
  }

  try {
    await loadT0();

    rebuildLinks();

    renderer.domElement.addEventListener("pointerdown", onPointerDown);

    resizeObs = new ResizeObserver(() => {
      if (!host.value || !renderer || !camera) return;
      const w = host.value.clientWidth;
      const h = host.value.clientHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    });
    resizeObs.observe(host.value);

    raf = requestAnimationFrame(animate);
  } catch (e: any) {
    console.error(e);
    loadProgress.value = String(e?.message ?? e);
    loading.value = false;
    ready.value = false;
  }
});

onBeforeUnmount(() => {
  if (raf) cancelAnimationFrame(raf);
  if (renderer) renderer.domElement.removeEventListener("pointerdown", onPointerDown);
  if (resizeObs && host.value) resizeObs.unobserve(host.value);
  resizeObs = null;

  controls?.dispose();
  controls = null;

  for (const line of orbitLinkLines.values()) {
      scene?.remove(line);
      line.geometry.dispose();
      (line.material as THREE.Material).dispose();
  }
  orbitLinkLines.clear();

  if (scene) {
    for (const sat of sats.value) {
      scene.remove(sat.mesh);
      (sat.mesh.geometry as THREE.BufferGeometry).dispose();
      (sat.mesh.material as THREE.Material).dispose();
    }
    scene = null;
  }

  if (renderer) {
    const canvas = renderer.domElement;
    renderer.dispose();
    canvas.parentElement?.removeChild(canvas);
    renderer = null;
  }
  camera = null;
});
</script>

<style scoped>
.wrap {
  display: grid;
  grid-template-columns: 320px 1fr 320px;
  height: 100vh;
  background: #050817;
  color: #e8eeff;
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
}

.left,
.right {
  padding: 12px;
  overflow: auto;
}
.center {
  position: relative;
  padding: 12px 0;
}

.viewport {
  position: absolute;
  inset: 12px;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.card {
  background: rgba(10, 14, 30, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  padding: 12px;
  margin-bottom: 12px;
  backdrop-filter: blur(8px);
}

.h {
  font-weight: 800;
  margin-bottom: 10px;
}
.h2 {
  font-weight: 700;
  margin: 10px 0 6px;
  font-size: 13px;
}

.row2 {
  display: grid;
  grid-template-columns: 110px 1fr;
  align-items: center;
  gap: 10px;
  margin: 8px 0;
}

.label {
  font-size: 12px;
  opacity: 0.9;
}
.small {
  font-size: 12px;
  opacity: 0.82;
  line-height: 1.5;
  margin-top: 8px;
}

.btn {
  padding: 8px 10px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.08);
  color: #e8eeff;
  cursor: pointer;
  font-size: 12px;
}
.btn:hover {
  background: rgba(255, 255, 255, 0.12);
}
.wide {
  width: 100%;
}

.select,
.input {
  width: 100%;
  padding: 7px 9px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.06);
  color: #e8eeff;
  outline: none;
}

.check {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 13px;
  margin: 6px 0 10px;
}

.kv {
  display: grid;
  grid-template-columns: 90px 1fr;
  gap: 10px;
  font-size: 12px;
  line-height: 1.8;
}

.divider {
  height: 1px;
  margin: 10px 0;
  background: rgba(255, 255, 255, 0.12);
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono",
    "Courier New", monospace;
}
</style>
