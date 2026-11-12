import { apiRequest } from './api-client.js';
import { CONFIG } from './config.js';

export function createHttpFleetApi(baseUrl = CONFIG.API_BASE_URL) {
  return {
    getFleet: () => apiRequest(baseUrl, '/api/v1/fleet'),
    getState: id => apiRequest(baseUrl, `/api/v1/vehicles/${encodeURIComponent(id)}/state`),
  };
}
