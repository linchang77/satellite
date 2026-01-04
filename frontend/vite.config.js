import { defineConfig } from 'vite'
import cesium from 'vite-plugin-cesium'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(),cesium()],
})
