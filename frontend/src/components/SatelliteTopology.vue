<template>
  <div class="topology-wrap">
    <div class="topology-section">
      <h3>卫星物理拓扑</h3>
      <div class="topology earth-bg">
        <v-network-graph :nodes="nodes" :edges="edges" :layouts="layouts">
          <template #override-node="{ scale }">
            <image :href="satIcon" :x="-12 * scale" :y="-12 * scale" :width="24 * scale" :height="24 * scale" />
          </template>
          <template #edge-label="{ edge, ...slotProps }">
            <v-edge-label :text="edge.label" align="center" vertical-align="above" v-bind="slotProps" />
          </template>
        </v-network-graph>

        <div v-if="status !== 'ready'" class="overlay">
          <div class="overlay-text">
            <template v-if="status === 'loading'">数据加载中…</template>
            <template v-else-if="status === 'not_found'">未找到该时间的星历数据</template>
            <template v-else>数据加载失败：{{ errorMsg }}</template>
          </div>
        </div>
      </div>

      <!-- 时间轴已移除
      <div class="control-item timeline" v-if="false">
        <div class="timeline-top">
          <span class="label">时间</span>
          <span class="value">{{ selectedTimeLabel }}</span>
        </div>
        <input class="slider" type="range" min="0" :max="Math.max(0, timeList.length - 1)" step="1" v-model.number="timeIndex" />
      </div-->
    </div>>

    <!-- 保留原路由拓扑部分不变 -->
    <div class="topology-section">
      <h3>路由拓扑</h3>
      <div class="controls">
        <label class="control-item">
          <span class="label" style="text-align:left; display:block;">卫星编号</span>
          <input class="input" v-model.trim="selectedRouter" placeholder="例如：r001001" />
        </label>
      </div>
      <div class="topology">
        <v-network-graph :nodes="routerNodes" :edges="routerEdges" :layouts="routerLayouts">
          <template #override-node="{ scale }">
            <image :href="satIcon" :x="-12 * scale" :y="-12 * scale" :width="24 * scale" :height="24 * scale" />
          </template>
          <template #edge-label="{ edge, ...slotProps }">
            <v-edge-label :text="edge.label" align="center" vertical-align="above" v-bind="slotProps" />
          </template>
        </v-network-graph>

        <div v-if="routerStatus !== 'ready'" class="overlay">
          <div class="overlay-text">
            <template v-if="routerStatus === 'loading'">数据加载中…</template>
            <template v-else>数据加载失败：{{ routerErrorMsg }}</template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'

// 卫星节点图标（位于 public 目录）
const satIcon = '/satellite.svg'
import { VNetworkGraph, VEdgeLabel } from 'v-network-graph'
import 'v-network-graph/lib/style.css'

/* 物理拓扑数据：frontend/public/data/Xingli_xls_15/*.csv
   文件名格式：Sat_X_Y_ephem_ext.csv
   X 表示轨道编号（共 3 个：6、7、8）
   Y 表示该轨道内卫星序号（6~10，每轨 5 颗）
*/

const status = ref('loading') // loading | ready | not_found | error
const errorMsg = ref('')

// ===================== 物理拓扑数据索引 =====================
const ephemerisFiles = [
  'Sat_6_6_ephem_ext.csv',
  'Sat_6_7_ephem_ext.csv',
  'Sat_6_8_ephem_ext.csv',
  'Sat_6_9_ephem_ext.csv',
  'Sat_6_10_ephem_ext.csv',
  'Sat_7_6_ephem_ext.csv',
  'Sat_7_7_ephem_ext.csv',
  'Sat_7_8_ephem_ext.csv',
  'Sat_7_9_ephem_ext.csv',
  'Sat_7_10_ephem_ext.csv',
  'Sat_8_6_ephem_ext.csv',
  'Sat_8_7_ephem_ext.csv',
  'Sat_8_8_ephem_ext.csv',
  'Sat_8_9_ephem_ext.csv',
  'Sat_8_10_ephem_ext.csv'
]

// Map<satId, Map<time, {lat,lon,alt}>>
const ephemIndex = ref(new Map())
const timeList = ref([]) // 1440 个时间点
const timeIndex = ref(0)

function parseEphemLine (line) {
  return line.split(',').map(s => s.trim())
}

async function loadEphemeris () {
  status.value = 'loading'
  errorMsg.value = ''
  try {
    const idx = new Map()
    const timesSet = new Set()

    for (const file of ephemerisFiles) {
      const resp = await fetch(`/data/Xingli_xls_15/${file}`)
      if (!resp.ok) throw new Error(`${file} HTTP ${resp.status}`)
      const text = await resp.text()
      const lines = text.split(/\r?\n/).filter(l => l.trim())
      if (lines.length < 2) continue

      const header = parseEphemLine(lines[0])
      const col = Object.fromEntries(header.map((h, i) => [h, i]))

      // 从文件名提取卫星 ID：Sat_X_Y
      const satId = file.replace('_ephem_ext.csv', '')

      if (!idx.has(satId)) idx.set(satId, new Map())

      for (let i = 1; i < lines.length; i++) {
        const parts = parseEphemLine(lines[i])
        const t = parts[col.UTCG]
        if (!t) continue
        idx.get(satId).set(t, {
          lat: Number(parts[col.lla_Lat]),
          lon: Number(parts[col.lla_Lon]),
          alt: Number(parts[col.lla_Alt])
        })
        timesSet.add(t)
      }
    }

    // 统一时间轴
    const times = Array.from(timesSet)
    times.sort((a, b) => new Date(a) - new Date(b))

    if (times.length === 0) throw new Error('星历数据为空')

    ephemIndex.value = idx
    timeList.value = times
    timeIndex.value = 0
    status.value = 'ready'
    // 加载完成后直接渲染一次静态拓扑
    updatePhysicalGraph()
  } catch (e) {
    status.value = 'error'
    errorMsg.value = e?.message ?? String(e)
  }
}

const selectedTime = computed(() => timeList.value[timeIndex.value] ?? '')
const selectedTimeLabel = computed(() => selectedTime.value)

// ===================== v-network-graph 数据 =====================
const nodes = reactive({})
const edges = reactive({})
const layouts = reactive({ nodes: {} })

function updatePhysicalGraph () {
  // 清空旧数据
  for (const k of Object.keys(nodes)) delete nodes[k]
  for (const k of Object.keys(edges)) delete edges[k]
  layouts.nodes = {}

  const t = selectedTime.value
  if (!t) {
    status.value = 'not_found'
    return
  }

  // 统计当前时刻所有卫星坐标
  const positions = [] // {satId,x,y}
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity

  for (const [satId, satMap] of ephemIndex.value.entries()) {
    const row = satMap.get(t)
    if (!row) continue
    // 使用经纬度：经度 -> x，纬度 -> y
    let x = row.lon
    let y = row.lat
    // 处理经度跨 ±180° 的情况，统一映射到 -180~180 区间
    if (x > 180) x -= 360
    positions.push({ satId, x, y })
    minX = Math.min(minX, x)
    maxX = Math.max(maxX, x)
    minY = Math.min(minY, y)
    maxY = Math.max(maxY, y)
  }

  if (positions.length === 0) {
    status.value = 'not_found'
    return
  }

  // 归一化到画布：中心 (0,0)，最大半径 300
  const spanX = maxX - minX
  const spanY = maxY - minY
  const scale = spanX > spanY ? 300 / spanX : 300 / spanY

  for (const { satId, x, y } of positions) {
    const nx = (x - (minX + spanX / 2)) * scale
    const ny = (y - (minY + spanY / 2)) * scale
    nodes[satId] = { name: satId }
    layouts.nodes[satId] = { x: nx, y: ny }
  }

  // 构造轨道内的连线（环）
  const orbitGroups = {
    '6': [],
    '7': [],
    '8': []
  }
  positions.forEach(p => {
    const [_, orbit] = p.satId.match(/^Sat_(\d+)_/) || []
    if (orbitGroups[orbit]) orbitGroups[orbit].push(p.satId)
  })

  let edgeId = 1
  for (const sats of Object.values(orbitGroups)) {
    sats.sort() // 简单排序，保证顺序一致
    const n = sats.length
    for (let i = 0; i < n; i++) {
      const s = sats[i]
      const t2 = sats[(i + 1) % n]
      // 取消 6 <-> 10 的闭合连线
      if ((s.endsWith('_6') && t2.endsWith('_10')) || (s.endsWith('_10') && t2.endsWith('_6'))) {
        continue
      }
      if (s && t2) {
        edges[`e${edgeId++}`] = { source: s, target: t2, label: '' }
      }
    }
  }

  status.value = 'ready'
}

watch([selectedTime, status], () => {
  if (status.value === 'ready') updatePhysicalGraph()
})

onMounted(() => {
  loadEphemeris()
  loadRouterData()
})

// ===================== 原路由拓扑代码保持不变 =====================
const routerStatus = ref('loading')
const routerErrorMsg = ref('')
const routers = [
  'r001001',
  'r001002',
  'r001003',
  'r001004',
  'r001005',
  'r002001',
  'r002002',
  'r002003',
  'r002004',
  'r002005',
  'r003001',
  'r003002',
  'r003003',
  'r003004',
  'r003005'
]
const selectedRouter = ref('r001001')
const routerConnections = ref(new Map())

// Router graph data
const routerNodes = reactive({})
const routerEdges = reactive({})
const routerLayouts = reactive({ nodes: {} })

async function loadRouterData () {
  routerStatus.value = 'loading'
  routerErrorMsg.value = ''
  try {
    const connections = new Map()
    for (const router of routers) {
      const resp = await fetch(`/data/router/${router}_net_qos.csv`)
      if (!resp.ok) continue
      const text = await resp.text()
      const lines = text.split(/\r?\n/).filter(l => l.trim())
      if (lines.length < 2) continue
      const header = lines[0].split(',').map(s => s.trim())
      const col = Object.fromEntries(header.map((h, i) => [h, i]))
      if (!connections.has(router)) connections.set(router, new Set())
      for (let i = 1; i < lines.length; i++) {
        const parts = lines[i].split(',').map(s => s.trim())
        const directNode = parts[col['直连节点']]
        if (directNode && directNode !== router) connections.get(router).add(directNode)
      }
    }
    routerConnections.value = connections
    updateRouterGraph()
    routerStatus.value = 'ready'
  } catch (e) {
    routerStatus.value = 'error'
    routerErrorMsg.value = e?.message ?? String(e)
  }
}

function updateRouterGraph () {
  const connections = routerConnections.value
  const startRouter = selectedRouter.value
  if (!connections.has(startRouter)) {
    for (const k of Object.keys(routerNodes)) delete routerNodes[k]
    for (const k of Object.keys(routerEdges)) delete routerEdges[k]
    routerLayouts.nodes = {}
    return
  }
  const reachable = new Set()
  const queue = [{ router: startRouter, hops: 0 }]
  const visited = new Set([startRouter])
  while (queue.length) {
    const { router, hops } = queue.shift()
    reachable.add(router)
    if (hops >= 16) continue
    const neighbors = connections.get(router) || new Set()
    for (const n of neighbors) {
      if (!visited.has(n)) {
        visited.add(n)
        queue.push({ router: n, hops: hops + 1 })
      }
    }
  }
  for (const k of Object.keys(routerNodes)) delete routerNodes[k]
  for (const router of reachable) routerNodes[router] = { name: router }
  for (const k of Object.keys(routerEdges)) delete routerEdges[k]
  const added = new Set()
  let eid = 1
  for (const s of reachable) {
    const ts = connections.get(s) || new Set()
    for (const t of ts) {
      if (!reachable.has(t)) continue
      const key = s < t ? `${s}-${t}` : `${t}-${s}`
      if (!added.has(key)) {
        added.add(key)
        routerEdges[`edge${eid++}`] = { source: s, target: t, label: '连接' }
      }
    }
  }
  routerLayouts.nodes = {}
  routerLayouts.type = 'manual'
  const orbitGroups = { '001': [], '002': [], '003': [] }
  for (const r of reachable) {
    const o = r.substring(1, 4)
    if (orbitGroups[o]) orbitGroups[o].push(r)
  }
  const cx = 0, cy = 0
  const cfg = { '001': { r: 250, off: 0 }, '002': { r: 180, off: Math.PI / 6 }, '003': { r: 110, off: Math.PI / 3 } }
  for (const [o, arr] of Object.entries(orbitGroups)) {
    if (!arr.length) continue
    const step = (2 * Math.PI) / arr.length
    arr.forEach((r, i) => {
      const a = i * step + cfg[o].off
      routerLayouts.nodes[r] = { x: cx + cfg[o].r * Math.cos(a), y: cy + cfg[o].r * Math.sin(a) }
    })
  }
}

watch(selectedRouter, () => { if (routerStatus.value === 'ready') updateRouterGraph() })
</script>

<style scoped>
.topology-wrap {
  display: flex;
  flex-direction: row;
  gap: 20px;
  width: 100%;
  height: 100vh;
  padding: 20px;
  box-sizing: border-box;
}
.topology-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
.topology-section h3 { margin: 0; color: #ffffff; }
.controls { width: 100%; max-width: 520px; display: flex; flex-direction: column; gap: 10px; }
.timeline { width: 100%; max-width: 520px; }
.control-item { display: flex; flex-direction: column; gap: 6px; }
.label { font-size: 12px; color: #ffffff; }
.input { height: 32px; padding: 0 10px; border: 1px solid #e2e8f0; border-radius: 8px; outline: none; }
.input:focus { border-color: #ffffff; }
.timeline-top { display: flex; align-items: baseline; justify-content: space-between; }
.value { font-size: 12px; color: #ffffff; }
.slider { width: 100%; }
.topology {
  position: relative;
  background: #fff;
  width: 100%;
  min-width: 700px;
  max-width: 900px;
  height: min(700px, calc(100vh - 150px));
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.08);
  overflow: hidden;
}
.overlay { position: absolute; inset: 0; display: flex; justify-content: center; align-items: center; background: rgba(255,255,255,0.8); pointer-events: none; }
.overlay-text { font-size: 13px; color: #475569; }
</style>
