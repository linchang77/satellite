/**
 * 卫星数据 API 服务
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

/**
 * 获取场景列表
 */
export async function getScenarios() {
  const response = await fetch(`${API_BASE_URL}/scenarios/`)
  if (!response.ok) {
    throw new Error(`获取场景列表失败: ${response.statusText}`)
  }
  return response.json()
}

/**
 * 根据ID获取场景详情
 */
export async function getScenario(scenarioId) {
  const response = await fetch(`${API_BASE_URL}/scenarios/${scenarioId}/`)
  if (!response.ok) {
    throw new Error(`获取场景详情失败: ${response.statusText}`)
  }
  return response.json()
}

/**
 * 获取场景下的所有卫星
 */
export async function getSatellitesByScenario(scenarioId) {
  const response = await fetch(`${API_BASE_URL}/scenarios/${scenarioId}/satellites/`)
  if (!response.ok) {
    throw new Error(`获取卫星数据失败: ${response.statusText}`)
  }
  return response.json()
}

/**
 * 获取场景及其所有卫星数据
 */
export async function getScenarioWithSatellites(scenarioId) {
  const [scenario, satellites] = await Promise.all([
    getScenario(scenarioId),
    getSatellitesByScenario(scenarioId)
  ])
  return { scenario, satellites }
}

