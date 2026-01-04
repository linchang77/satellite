<template>
  <div class="sat-topology-wrap">
    <div class="controls">
      <label class="control-item">
        <span class="label" style="text-align:left; display:block;">卫星编号</span>
        <input
          class="input"
          v-model.trim="satId"
          placeholder="例如：Sat_1_1"
        />
      </label>
    </div>

    <div class="sat-topology">
      <v-network-graph :nodes="nodes" :edges="edges" :layouts="layouts">
        <template #edge-label="{ edge, ...slotProps }">
          <v-edge-label
            :text="edge.label"
            align="center"
            vertical-align="above"
            v-bind="slotProps"
          />
        </template>
      </v-network-graph>

      <div v-if="status !== 'ready'" class="overlay">
        <div class="overlay-text">
          <template v-if="status === 'loading'">数据加载中…</template>
          <template v-else-if="status === 'not_found'"
            >未找到该卫星在此时间的拓扑数据</template
          >
          <template v-else>数据加载失败：{{ errorMsg }}</template>
        </div>
      </div>
    </div>

    <div class="control-item timeline" v-if="timeList.length">
      <div class="timeline-top">
        <span class="label">时间</span>
        <span class="value">{{ selectedTimeLabel }}</span>
      </div>
      <input
        class="slider"
        type="range"
        min="0"
        :max="Math.max(0, timeList.length - 1)"
        step="1"
        v-model.number="timeIndex"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { VNetworkGraph, VEdgeLabel } from "v-network-graph";
import "v-network-graph/lib/style.css";

/**
 * CSV 字段：
 * Time_UTCG,SatId,FrontId,FrontRangeKm,BackId,BackRangeKm,LeftId,LeftRangeKm,LeftChanged,RightId,RightRangeKm,RightChanged
 */

const status = ref("loading"); // loading | ready | not_found | error
const errorMsg = ref("");

// 输入：卫星编号 + 时间轴
const satId = ref("Sat_1_1");
const timeList = ref([]); // string[]
const timeIndex = ref(0);

// 数据索引：Map<satId, Map<time, row>>
const dataIndex = ref(new Map());

function parseCsvLine(line) {
  // 该 CSV 数据本身不包含引号包裹字段，直接按逗号切分即可
  // 注意 Time_UTCG 本身带一个前导单引号，例如：'15 Dec 2025 00:00:00.000
  return line.split(",").map((s) => s.trim());
}

function buildIndex(csvText) {
  const lines = csvText.split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (lines.length < 2) return { index: new Map(), times: [] };

  const header = parseCsvLine(lines[0]);
  const col = Object.fromEntries(header.map((h, i) => [h, i]));

  const idx = new Map();
  const timesSet = new Set();

  for (let i = 1; i < lines.length; i++) {
    const parts = parseCsvLine(lines[i]);
    const Time_UTCG = parts[col.Time_UTCG];
    const SatId = parts[col.SatId];

    if (!Time_UTCG || !SatId) continue;

    const row = {
      Time_UTCG,
      SatId,
      FrontId: parts[col.FrontId],
      FrontRangeKm: Number(parts[col.FrontRangeKm]),
      BackId: parts[col.BackId],
      BackRangeKm: Number(parts[col.BackRangeKm]),
      LeftId: parts[col.LeftId],
      LeftRangeKm: Number(parts[col.LeftRangeKm]),
      RightId: parts[col.RightId],
      RightRangeKm: Number(parts[col.RightRangeKm]),
      // LeftChanged/RightChanged 目前不参与拓扑生成
    };

    if (!idx.has(SatId)) idx.set(SatId, new Map());
    idx.get(SatId).set(Time_UTCG, row);
    timesSet.add(Time_UTCG);
  }

  // 时间排序：由于格式类似 "'15 Dec 2025 01:00:00.000"，直接按字符串排序也基本可用
  // 这里做一个更稳的排序：转成 Date（去掉前导单引号）
  const times = Array.from(timesSet);
  times.sort((a, b) => {
    const da = new Date(a.replace(/^'/, ""));
    const db = new Date(b.replace(/^'/, ""));
    return da - db;
  });

  return { index: idx, times };
}

async function loadCsv() {
  status.value = "loading";
  errorMsg.value = "";
  try {
    // 注意：该路径需要确保在 Vite 的 public 目录下可直接访问。
    // 如果 data/ 不在 public 目录，请把该 csv 移到 public/data/ 下。
    const resp = await fetch("/data/XLneighbors_4_ranges_hourly.csv");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const text = await resp.text();
    const { index, times } = buildIndex(text);

    dataIndex.value = index;
    timeList.value = times;
    timeIndex.value = 0;

    // 先尝试渲染一次
    status.value = "ready";
  } catch (e) {
    status.value = "error";
    errorMsg.value = e?.message ?? String(e);
  }
}

onMounted(loadCsv);

const selectedTime = computed(() => timeList.value[timeIndex.value] ?? "");
const selectedTimeLabel = computed(() => selectedTime.value.replace(/^'/, ""));

const currentRow = computed(() => {
  if (!satId.value || !selectedTime.value) return null;
  const satMap = dataIndex.value.get(satId.value);
  if (!satMap) return null;
  return satMap.get(selectedTime.value) ?? null;
});

// graph 数据（保持生成逻辑不变：中心卫星 + 前后左右四条边）
const nodes = reactive({});
const edges = reactive({});
const layouts = reactive({ nodes: {} });

function applyRowToGraph(row) {
  // 清空旧数据（保持 reactive 对象引用不变）
  for (const k of Object.keys(nodes)) delete nodes[k];
  for (const k of Object.keys(edges)) delete edges[k];
  layouts.nodes = {};

  if (!row) return;

  const selectedSatId = row.SatId;

  nodes[selectedSatId] = { name: selectedSatId };
  nodes[row.FrontId] = { name: row.FrontId };
  nodes[row.BackId] = { name: row.BackId };
  nodes[row.LeftId] = { name: row.LeftId };
  nodes[row.RightId] = { name: row.RightId };

  edges.edge1 = {
    source: selectedSatId,
    target: row.FrontId,
    label: `前: ${row.FrontRangeKm.toFixed(2)} km`,
  };
  edges.edge2 = {
    source: selectedSatId,
    target: row.BackId,
    label: `后: ${row.BackRangeKm.toFixed(2)} km`,
  };
  edges.edge3 = {
    source: selectedSatId,
    target: row.LeftId,
    label: `左: ${row.LeftRangeKm.toFixed(2)} km`,
  };
  edges.edge4 = {
    source: selectedSatId,
    target: row.RightId,
    label: `右: ${row.RightRangeKm.toFixed(2)} km`,
  };

  // 十字型布局（与原来一致，只是坐标值集中管理）
  const d = 200;
  layouts.nodes = {
    [selectedSatId]: { x: 0, y: 0 },
    [row.FrontId]: { x: d, y: 0 },
    [row.BackId]: { x: -d, y: 0 },
    [row.LeftId]: { x: 0, y: -d },
    [row.RightId]: { x: 0, y: d },
  };
}

watch(
  currentRow,
  (row) => {
    if (status.value === "error") return;
    if (!row) {
      applyRowToGraph(null);
      status.value = "not_found";
      return;
    }
    applyRowToGraph(row);
    status.value = "ready";
  },
  { immediate: true }
);
</script>

<style scoped>
.sat-topology-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.controls {
  width: 520px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.timeline {
  width: 520px;
}

.control-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label {
  font-size: 12px;
  color: #ffffff;
}

.input {
  height: 32px;
  padding: 0 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  outline: none;
}

.input:focus {
  border-color: #ffffff;
}

.timeline-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.value {
  font-size: 12px;
  color: #ffffff;
}

.slider {
  width: 100%;
}

.sat-topology {
  position: relative;
  background: #fff;
  width: 520px;
  height: min(520px, calc(100vh - 48px));
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.overlay {
  position: absolute;
  inset: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  background: rgba(255, 255, 255, 0.8);
  pointer-events: none;
}

.overlay-text {
  font-size: 13px;
  color: #475569;
}
</style>
