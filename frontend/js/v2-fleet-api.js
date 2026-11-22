import { apiRequest } from './api-client.js';

export function createV2FleetApi(baseUrl) {
  const request = (path, options) => apiRequest(baseUrl.replace(/\/+$/, ''), `/api/v2${path}`, options);
  const actions = '/diagnostics/actions';
  return {
    getFleet: () => request('/fleet'),
    getState: id => request(`/vehicles/${encodeURIComponent(id)}/state`),
    submitAction: body => request(actions, { method: 'POST', body, timeoutMs: 6000 }),
    getAction: id => request(`${actions}/${encodeURIComponent(id)}`, { allowOneRetry: false }),
    getHistory: id => request(`/diagnostics/vehicles/${encodeURIComponent(id)}/actions`, { allowOneRetry: false }),
  };
}
