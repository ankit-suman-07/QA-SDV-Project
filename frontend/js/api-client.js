const DEFAULT_TIMEOUT_MS = 5000; // Section 10: recommended client timeout
const RETRYABLE_STATUSES = new Set([408, 500, 502, 503, 504]);

export class ApiRequestError extends Error {
  constructor(apiError) {
    super(apiError.message);
    this.apiError = apiError;
  }
}

function normalizeApiError(httpStatus, body) {
  return {
    httpStatus,
    code: body?.code ?? "UNKNOWN_ERROR",
    message: body?.message ?? "Something went wrong. Please try again.",
    path: body?.path,
    retryable: RETRYABLE_STATUSES.has(httpStatus),
  };
}

function networkFailureError() {
  return {
    httpStatus: 0,
    code: "NETWORK_ERROR",
    message: "Could not reach the server.",
    retryable: true,
  };
}

function timeoutError() {
  return {
    httpStatus: 408,
    code: "TIMEOUT",
    message: "The request took too long to respond.",
    retryable: true,
  };
}

async function doFetch(baseUrl, path, options) {
  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${baseUrl}${path}`, {
      method: options.method ?? "GET",
      headers: { "Content-Type": "application/json" },
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    });

    if (!response.ok) {
      let parsedBody = null;
      try {
        parsedBody = await response.json();
      } catch {
        parsedBody = null;
      }
      throw new ApiRequestError(normalizeApiError(response.status, parsedBody));
    }
    if (response.status === 204) return null;
    try {
      return await response.json();
    } catch {
      return null;
    }
  } catch (err) {
    if (err instanceof ApiRequestError) throw err;
    if (err.name === "AbortError") throw new ApiRequestError(timeoutError());
    throw new ApiRequestError(networkFailureError());
  } finally {
    clearTimeout(timer);
  }
}

/** Section 10: GET may retry once automatically; POST must never
 * auto-retry, since a timeout doesn't prove the backend didn't accept it. */
export async function apiRequest(baseUrl, path, options = {}) {
  const method = options.method ?? "GET";
  try {
    return await doFetch(baseUrl, path, options);
  } catch (err) {
    const canRetry = method === "GET" && options.allowOneRetry !== false;
    if (canRetry && err instanceof ApiRequestError && err.apiError.retryable) {
      return await doFetch(baseUrl, path, options);
    }
    throw err;
  }
}
