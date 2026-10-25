const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const getToken = () => localStorage.getItem('token');

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

export async function api(path, { method = 'GET', body, params } = {}) {
  const clean = params
    ? Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
    : [];
  const qs = clean.length ? '?' + new URLSearchParams(clean) : '';
  const token = getToken();
  let res;
  try {
    res = await fetch(BASE + path + qs, {
      method,
      headers: {
        ...(body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Can't reach the server. Check your connection and try again.", 0);
  }
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }

  if (!res.ok) {
    if (res.status === 401 && token) window.dispatchEvent(new Event('auth-expired'));
    let msg = data?.error;
    if (!msg && Array.isArray(data?.detail)) {
      msg = data.detail.map((d) => (d.msg || '').replace(/^Value error, /, '')).join('. ');
    }
    throw new ApiError(msg || 'Something went wrong. Please try again.', res.status, data);
  }
  return data;
}
