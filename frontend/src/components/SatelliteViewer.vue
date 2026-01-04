<template>
  <div class="cesium-container">
    <div v-if="loading" class="loading-overlay">
      <div class="loading-message">正在加载场景数据...</div>
    </div>
    <div v-if="error" class="error-overlay">
      <div class="error-message">{{ error }}</div>
    </div>
    <div ref="viewerContainer" class="viewer"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { getScenarioWithSatellites } from '../api/satellite.js'

// Tell Cesium where static assets are served from (vite-plugin-cesium serves them at /cesium)
// MUST set before importing Cesium so Cesium can resolve its static assets.
window.CESIUM_BASE_URL = '/cesium'
import * as Cesium from 'cesium'

const props = defineProps({
  scenarioId: {
    type: [Number, String],
    required: true,
    default: 1
  }
})

const viewerContainer = ref(null)
const loading = ref(false)
const error = ref(null)
let viewer = null

// Colors for different planes
const planeColors = [
  '#ff0000', // Red
  '#00ff00', // Green
  '#0000ff', // Blue
  '#ffff00', // Yellow
  '#ff00ff', // Magenta
  '#00ffff', // Cyan
  '#800000', // Maroon
  '#008000', // Dark Green
  '#000080', // Navy
  '#808000', // Olive
  '#800080', // Purple
  '#008080', // Teal
  '#ffa500', // Orange
  '#a52a2a', // Brown
  '#ffc0cb'  // Pink
]

/**
 * 创建圆形轨道位置（简化实现）
 * @param {Cesium.JulianDate} start - 起始时间
 * @param {Number} periodSeconds - 轨道周期（秒）
 * @param {Number} altitudeMeters - 高度（米）
 * @param {Number} inclinationDeg - 倾角（度）
 * @param {Number} raanDeg - 升交点赤经（度）
 * @param {Number} initialTrueAnomalyDeg - 初始真近点角（度）
 * @param {Number} samples - 采样点数
 */
function createCircularOrbitPositions(start, periodSeconds, altitudeMeters, inclinationDeg, raanDeg, initialTrueAnomalyDeg, samples = 360) {
  const property = new Cesium.SampledPositionProperty()
  const inclRad = Cesium.Math.toRadians(inclinationDeg)
  const raanRad = Cesium.Math.toRadians(raanDeg)
  const initialTrueAnomalyRad = Cesium.Math.toRadians(initialTrueAnomalyDeg)

  for (let i = 0; i <= samples; i++) {
    const t = (i / samples) * periodSeconds
    const time = Cesium.JulianDate.addSeconds(start, t, new Cesium.JulianDate())

    // Mean anomaly (for circular orbit, true anomaly = mean anomaly)
    const meanAnomaly = (t / periodSeconds) * Math.PI * 2 + initialTrueAnomalyRad

    // True anomaly
    const trueAnomaly = meanAnomaly

    // Latitude
    const latRad = Math.asin(Math.sin(inclRad) * Math.sin(trueAnomaly))
    const lat = Cesium.Math.toDegrees(latRad)

    // Longitude
    const argOfLat = Math.atan2(Math.cos(trueAnomaly), Math.sin(trueAnomaly) * Math.cos(inclRad))
    const lonRad = raanRad + argOfLat
    const lon = Cesium.Math.toDegrees(lonRad)

    const pos = Cesium.Cartesian3.fromDegrees(lon, lat, altitudeMeters)
    property.addSample(time, pos)
  }
  return property
}

/**
 * 解析时间字符串（支持多种格式）
 */
function parseTime(timeStr) {
  if (!timeStr) return Cesium.JulianDate.now()
  
  // 尝试解析 ISO 8601 格式
  const date = new Date(timeStr)
  if (!isNaN(date.getTime())) {
    return Cesium.JulianDate.fromDate(date)
  }
  
  return Cesium.JulianDate.now()
}


/**
 * 初始化 Cesium 查看器并加载卫星数据
 */
async function initializeViewer() {
  try {
    loading.value = true
    error.value = null
    
    // 从后端获取场景和卫星数据
    const { scenario, satellites } = await getScenarioWithSatellites(props.scenarioId)
    
    if (!viewer) {
      viewer = new Cesium.Viewer(viewerContainer.value, {
        timeline: true,
        animation: true,
        imageryProvider: new Cesium.OpenStreetMapImageryProvider(),
        terrainProvider: new Cesium.EllipsoidTerrainProvider(),
        sceneModePicker: true,
      })
      viewer.scene.globe.show = true
      
    }
    
    // 解析时间
    const startTime = parseTime(scenario.start_time || scenario.epoch)
    const endTime = parseTime(scenario.end_time)
    const duration = Cesium.JulianDate.secondsDifference(endTime, startTime)
    
    // 设置时钟
    viewer.clock.startTime = startTime
    viewer.clock.stopTime = endTime
    viewer.clock.currentTime = startTime
    viewer.clock.multiplier = 60 // 加速模拟
    viewer.clock.shouldAnimate = true
    
    // 获取传感器配置
    const sensorConfig = scenario.sensor_config || {
      type: "cone",
      halfAngleDeg: 30,
      pointing: "nadir"
    }
    
    // 按轨道面分组卫星
    const satellitesByPlane = {}
    satellites.forEach(sat => {
      const planeIdx = sat.plane_index
      if (!satellitesByPlane[planeIdx]) {
        satellitesByPlane[planeIdx] = []
      }
      satellitesByPlane[planeIdx].push(sat)
    })
    
    // 为每个卫星创建实体
    satellites.forEach((satellite, index) => {
      const planeIndex = satellite.plane_index
      const color = planeColors[(planeIndex - 1) % planeColors.length]
      
      // 使用固定的轨道周期（约90分钟）或从场景配置获取
      const periodSeconds = 5400 // ~90 minutes orbital period
      
      // 转换高度为米
      const altitudeMeters = satellite.alt_km * 1000
      
      // 创建圆形轨道位置
      const positionProp = createCircularOrbitPositions(
        startTime,
        periodSeconds,
        altitudeMeters,
        satellite.inc_deg,
        satellite.raan_deg,
        satellite.ta_deg,
        360
      )
      
      // 计算覆盖范围位置（使用高度的一半）
      const coverageAltMeters = altitudeMeters*1.5
      const coveragePosProp = createCircularOrbitPositions(
        startTime,
        periodSeconds,
        coverageAltMeters,
        satellite.inc_deg,
        satellite.raan_deg,
        satellite.ta_deg,
        360
      )
      
      // 卫星实体
      viewer.entities.add({
        id: satellite.sat_id || satellite.stk_name,
        name: satellite.stk_name || satellite.sat_id,
        position: positionProp,
        point: {
          pixelSize: 8,
          color: Cesium.Color.fromCssColorString(color),
        },
        path: {
          resolution: 120,
          material: Cesium.Color.fromCssColorString(color),
          width: 2,
          leadTime: 0,
          trailTime: periodSeconds * 2,
        },
        label: {
          text: satellite.stk_name || satellite.sat_id,
          font: '12pt sans-serif',
          fillColor: Cesium.Color.WHITE,
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 2,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0, -32),
          show: true
        }
      })
      
      // 覆盖范围实体
      if (sensorConfig.type === 'SimpleConic') {
        const halfAngleRad = Cesium.Math.toRadians(sensorConfig.halfAngleDeg || 30)
        const altitudeMeters = satellite.alt_km * 1000
        const bottomRadius = altitudeMeters * Math.tan(halfAngleRad)
        console.log(bottomRadius);
        
        viewer.entities.add({
          id: (satellite.sat_id || satellite.stk_name) + '_coverage',
          name: (satellite.stk_name || satellite.sat_id) + ' Coverage',
          position: coveragePosProp,
          cylinder: {
            length: altitudeMeters,
            topRadius: 0,
            bottomRadius: bottomRadius,
            material: Cesium.Color.fromCssColorString(color).withAlpha(0.2),
            outline: true,
            outlineColor: Cesium.Color.fromCssColorString(color),
            numberOfVerticalLines: 0,
            numberOfHorizontalLines: 0,
            show: true
          }
        })
      }
    })
    
    // 飞行到第一个卫星的初始位置
    if (satellites.length > 0) {
      const firstSat = satellites[0]
      const periodSeconds = 5400 // ~90 minutes orbital period
      const altitudeMeters = firstSat.alt_km * 1000
      const firstPositionProp = createCircularOrbitPositions(
        startTime,
        periodSeconds,
        altitudeMeters,
        firstSat.inc_deg,
        firstSat.raan_deg,
        firstSat.ta_deg,
        360
      )
      const initPos = firstPositionProp.getValue(startTime)
      viewer.camera.flyTo({ 
        destination: Cesium.Cartesian3.multiplyByScalar(initPos, 1.2, new Cesium.Cartesian3()) 
      })
    }
    
    loading.value = false
  } catch (err) {
    console.error('加载场景数据失败:', err)
    error.value = err.message || '加载场景数据失败，请检查网络连接或场景ID是否正确'
    loading.value = false
  }
}

onMounted(() => {
  initializeViewer()
})

onBeforeUnmount(() => {
  if (viewer && !viewer.isDestroyed()) {
    viewer.destroy()
    viewer = null
  }
})
</script>

<style scoped>
.cesium-container {
  height: 80vh;
  width: 100%;
  position: relative;
}

.viewer {
  height: 100%;
  width: 100%;
}

.loading-overlay,
.error-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(0, 0, 0, 0.7);
  z-index: 1000;
}

.loading-message,
.error-message {
  color: white;
  font-size: 18px;
  padding: 20px;
  background-color: rgba(0, 0, 0, 0.8);
  border-radius: 8px;
}

.error-message {
  color: #ff6b6b;
  max-width: 80%;
  text-align: center;
}
</style>
