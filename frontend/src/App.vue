<!-- <script setup>
import SatelliteTopology3D from './components/SatelliteTopology3D.vue'
import TestThree from './components/TestThree.vue'
// import SatelliteViewerTest from './components/SatelliteViewerTest.vue'
</script> -->

<!-- <template>
  <div class="app-container"> -->
      <!-- <SatelliteTopology /> -->
      <!-- <SatelliteTopology3D /> -->
      <!-- <TestThree />
  </div>
</template> -->

<!-- <style scoped>
.app-container {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
}
</style> -->
<script setup lang="ts">
  import SatTopology3D from "./components/SatTopology3D.vue";
  </script>
<template>
  <div style="width: 100vw; height: 100vh; padding: 14px; box-sizing: border-box;">
    <SatTopology3D />
  </div>
</template>

