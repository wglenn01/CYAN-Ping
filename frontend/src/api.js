import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";
export const API = `${BACKEND_URL}/api`;

const client = axios.create({ baseURL: API });

client.interceptors.request.use((config) => {
  const stored = localStorage.getItem("sp_user");
  if (stored) {
    try {
      const { token } = JSON.parse(stored);
      if (token) config.headers.Authorization = `Bearer ${token}`;
    } catch (e) {}
  }
  return config;
});

client.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem("sp_user");
      if (window.location.pathname !== "/login") window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const api = {
  login: (username, password) =>
    client.post("/auth/login", { username, password }).then((r) => r.data),
  me: () => client.get("/auth/me").then((r) => r.data),
  overview: () => client.get("/overview").then((r) => r.data),
  tree: () => client.get("/tree").then((r) => r.data),
  groups: () => client.get("/groups").then((r) => r.data),
  targets: () => client.get("/targets").then((r) => r.data),
  target: (id) => client.get(`/targets/${id}`).then((r) => r.data),
  createTarget: (body) => client.post("/targets", body).then((r) => r.data),
  updateTarget: (id, body) => client.put(`/targets/${id}`, body).then((r) => r.data),
  deleteTarget: (id) => client.delete(`/targets/${id}`).then((r) => r.data),
  series: (id, range) =>
    client.get(`/targets/${id}/series`, { params: { range } }).then((r) => r.data),
  getMtr: (id) => client.get(`/targets/${id}/mtr`).then((r) => r.data),
  runMtr: (id) => client.post(`/targets/${id}/mtr/run`).then((r) => r.data),
  startLiveMtr: (id) => client.post(`/targets/${id}/mtr/start`).then((r) => r.data),
  stopLiveMtr: (id) => client.post(`/targets/${id}/mtr/stop`).then((r) => r.data),
  liveMtr: (id) => client.get(`/targets/${id}/mtr/live`).then((r) => r.data),
  alerts: () => client.get("/alerts").then((r) => r.data),
  alertRules: () => client.get("/alert-rules").then((r) => r.data),
  updateRule: (id, enabled) =>
    client.put(`/alert-rules/${id}`, { enabled }).then((r) => r.data),
};

export default client;
