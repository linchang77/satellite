<template>
  <div class="cesium-container">
    <div v-if="loading" class="loading-overlay">
      <div class="loading-message">{{ loadingMessage }}</div>
    </div>
    <div v-if="error" class="error-overlay">
      <div class="error-message">{{ error }}</div>
    </div>
    <div ref="viewerContainer" class="viewer"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';

// 设置 Cesium 静态资源基础路径
window.CESIUM_BASE_URL = '/cesium';
import * as Cesium from 'cesium';

const viewerContainer = ref(null);
const loading = ref(true);
const loadingMessage = ref('正在初始化场景...');
const error = ref(null);
let viewer = null;

// 轨道面颜色，用于区分不同轨道的卫星
const planeColors = [
  Cesium.Color.RED,
  Cesium.Color.GREEN,
  Cesium.Color.BLUE,
  Cesium.Color.YELLOW,
  Cesium.Color.MAGENTA,
  Cesium.Color.CYAN,
];

// 15颗卫星的文件名
const satelliteFiles = [
    'Sat_6_6_ephem_ext.csv', 'Sat_6_7_ephem_ext.csv', 'Sat_6_8_ephem_ext.csv', 'Sat_6_9_ephem_ext.csv', 'Sat_6_10_ephem_ext.csv',
    'Sat_7_6_ephem_ext.csv', 'Sat_7_7_ephem_ext.csv', 'Sat_7_8_ephem_ext.csv', 'Sat_7_9_ephem_ext.csv', 'Sat_7_10_ephem_ext.csv',
    'Sat_8_6_ephem_ext.csv', 'Sat_8_7_ephem_ext.csv', 'Sat_8_8_ephem_ext.csv', 'Sat_8_9_ephem_ext.csv', 'Sat_8_10_ephem_ext.csv'
];

/**
 * 解析CSV文本数据
 * @param {string} csvText CSV格式的文本
 * @returns {Array<Object>} 解析后的对象数组
 */
function parseCsv(csvText) {
  const lines = csvText.trim().split('\n');
  const headers = lines[0].split(',').map(h => h.trim());
  return lines.slice(1).map(line => {
    const values = line.split(',').map(v => v.trim());
    return headers.reduce((obj, header, index) => {
      obj[header] = values[index];
      return obj;
    }, {});
  });
}

function getSampleValue(sample, candidates) {
  for (const key of candidates) {
    if (Object.prototype.hasOwnProperty.call(sample, key) && sample[key] != null && String(sample[key]).trim() !== '') {
      return sample[key];
    }
  }
  return undefined;
}

function parseTimeFromSample(sample) {
  const raw = getSampleValue(sample, ['Time (UTCG)', 'UTCG', 'time', 'Time', 'timestamp', '日期', '时间']);
  if (raw == null) {
    throw new Error('未找到时间字段（例如 Time (UTCG)/UTCG）');
  }
  const s = String(raw).trim();

  // 1) 尝试 Cesium 原生 ISO8601
  try {
    return Cesium.JulianDate.fromIso8601(s);
  } catch (_) {
    // ignore
  }

  // 2) 常见格式兼容："YYYY-MM-DD HH:mm:ss" / "YYYY/MM/DD HH:mm:ss" => 转成 ISO
  const normalized = s.replace(' ', 'T').replace(/\//g, '-');
  try {
    return Cesium.JulianDate.fromIso8601(normalized.endsWith('Z') ? normalized : normalized + 'Z');
  } catch (_) {
    // ignore
  }

  // 3) 用 JS Date 兜底
  const d = new Date(s);
  if (!Number.isNaN(d.getTime())) {
    return Cesium.JulianDate.fromDate(d);
  }

  throw new Error(`无法解析时间字段: ${s}`);
}

function parseNumberFromSample(sample, candidates) {
  const raw = getSampleValue(sample, candidates);
  if (raw == null) {
    return NaN;
  }
  const n = Number(String(raw).trim());
  return Number.isFinite(n) ? n : NaN;
}

/**
 * 加载并处理所有卫星的星历数据
 */
async function loadSatelliteData() {
  const allSatData = [];
  for (let i = 0; i < satelliteFiles.length; i++) {
    const file = satelliteFiles[i];
    try {
      loadingMessage.value = `正在加载卫星数据 (${i + 1}/${satelliteFiles.length}): ${file}`;
      const response = await fetch(`/data/Xingli_xls_15/${file}`);
      if (!response.ok) throw new Error(`文件加载失败: ${response.statusText}`);
      const csvText = await response.text();
      const parsedData = parseCsv(csvText);
      allSatData.push({ name: file.replace('_ephem_ext.csv', ''), data: parsedData });
    } catch (err) {
      console.error(`加载或解析 ${file} 出错:`, err);
      throw err;
    }
  }
  return allSatData;
}

/**
 * 初始化 Cesium 查看器并加载卫星
 */
async function initializeViewer() {
  try {
    if (!viewerContainer.value) return;

    viewer = new Cesium.Viewer(viewerContainer.value, {
      timeline: true,
      animation: true,
      infoBox: true,
      // 使用J2000/ICRF作为内部参考系，以匹配星历数据
      scene3DOnly: true,
      shouldAnimate: true,
      imageryProvider: new Cesium.OpenStreetMapImageryProvider(),
      terrainProvider: new Cesium.EllipsoidTerrainProvider(),
    });


    //加载数据
    const allSatData = await loadSatelliteData();

    if (allSatData.length === 0 || allSatData[0].data.length === 0) {
      throw new Error('星历数据为空或加载失败');
    }

    loadingMessage.value = '正在创建卫星实体...';

    const firstSample = allSatData[0].data[0];
    const lastSample = allSatData[0].data[allSatData[0].data.length - 1];
    const startTime = parseTimeFromSample(firstSample);
    const stopTime = parseTimeFromSample(lastSample);

    // 设置时钟
    viewer.clock.startTime = startTime;
    viewer.clock.stopTime = stopTime;
    viewer.clock.currentTime = startTime;
    viewer.clock.multiplier = 100; // 时间倍率
    viewer.timeline.zoomTo(startTime, stopTime);

    let firstSatelliteEntity = null;

    allSatData.forEach((sat, index) => {
      const positionProperty = new Cesium.SampledPositionProperty(Cesium.ReferenceFrame.INERTIAL);

      sat.data.forEach(sample => {
        const time = parseTimeFromSample(sample);

        const rxKm = parseNumberFromSample(sample, ['r_x (km)', 'r_x', 'rx', 'x', 'J2000_X', 'X']);
        const ryKm = parseNumberFromSample(sample, ['r_y (km)', 'r_y', 'ry', 'y', 'J2000_Y', 'Y']);
        const rzKm = parseNumberFromSample(sample, ['r_z (km)', 'r_z', 'rz', 'z', 'J2000_Z', 'Z']);

        if (!Number.isFinite(rxKm) || !Number.isFinite(ryKm) || !Number.isFinite(rzKm)) {
          return;
        }

        // J2000坐标单位是km，需要转换为米
        const position = new Cesium.Cartesian3(rxKm * 1000, ryKm * 1000, rzKm * 1000);
        positionProperty.addSample(time, position);
      });

      const planeIndex = parseInt(sat.name.split('_')[1]) - 6; // 从Sat_6_x中提取轨道面索引
      const color = planeColors[planeIndex % planeColors.length];

      const entity = viewer.entities.add({
        id: sat.name,
        name: sat.name,
        position: positionProperty,
        point: {
          pixelSize: 8,
          color: color,
        },
        path: {
          // 用“短尾迹”代替整条轨道，性能会好很多
          show: true,
          resolution: 60,
          material: color.withAlpha(0.6),
          width: 2,
          leadTime: 0,
          trailTime: 60 * 80,
        },
        label: {
          text: sat.name,
          font: '12pt sans-serif',
          fillColor: Cesium.Color.WHITE,
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 2,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0, -12),
        }
      });
    });



    loading.value = false;

  } catch (err) {
    console.error('初始化Cesium场景失败:', err);
    error.value = err.message || '初始化场景失败，请检查数据文件或浏览器控制台。';
    loading.value = false;
  }
}

onMounted(() => {
  initializeViewer();
});

onBeforeUnmount(() => {
  if (viewer && !viewer.isDestroyed()) {
    viewer.destroy();
    viewer = null;
  }
});

</script>

<style scoped>
.cesium-container {
  height: 100vh;
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
  color: white;
  font-size: 18px;
}

.loading-message,
.error-message {
  padding: 20px;
  background-color: rgba(0, 0, 0, 0.8);
  border-radius: 8px;
  text-align: center;
}

.error-message {
  color: #ff6b6b;
}
</style>