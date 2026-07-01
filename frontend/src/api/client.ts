import axios from "axios";
import { toast } from "sonner";

const client = axios.create({
  baseURL: "/api/v1",
});

// Request interceptor: inject Authorization header
client.interceptors.request.use((config) => {
  const token = localStorage.getItem("token") || sessionStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Refresh lock to prevent concurrent refreshes
let isRefreshing = false;
let refreshPromise: Promise<string> | null = null;

async function refreshToken(): Promise<string> {
  const token = localStorage.getItem("token") || sessionStorage.getItem("token");
  if (!token) throw new Error("No token");
  const resp = await axios.post("/api/v1/auth/refresh", null, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const newToken = resp.data.token;
  // Store to whichever storage had the old token
  if (localStorage.getItem("token")) localStorage.setItem("token", newToken);
  else sessionStorage.setItem("token", newToken);
  return newToken;
}

// Response interceptor: handle 401
client.interceptors.response.use(
  (resp) => resp,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      // 排除登录/注册请求 — 401 代表凭据错误，不是 token 过期
      const url = originalRequest.url || "";
      if (url.includes("/auth/login") || url.includes("/auth/register")) {
        return Promise.reject(error);
      }

      originalRequest._retry = true;

      // Use refresh lock - only one refresh at a time
      if (!isRefreshing) {
        isRefreshing = true;
        refreshPromise = refreshToken().finally(() => {
          isRefreshing = false;
          refreshPromise = null;
        });
      }

      if (refreshPromise) {
        try {
          const newToken = await refreshPromise;
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return client(originalRequest);
        } catch {
          // Refresh failed - clear auth and redirect
          toast.error("登录已过期，请重新登录");
          localStorage.clear();
          sessionStorage.clear();
          window.location.href = "/login";
          return Promise.reject(error);
        }
      }
    }

    return Promise.reject(error);
  }
);

export default client;
