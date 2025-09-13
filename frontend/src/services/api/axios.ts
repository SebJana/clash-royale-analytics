import axios from "axios";

// Base URL configuration:
// - Development: Vite proxy handles /api -> http://localhost:8000/api
// - Production (Docker): nginx proxy handles /api -> http://api:8000/api
const api = axios.create({
  baseURL: "/api",
  timeout: 5000,
  headers: {
    "Content-Type": "application/json",
  },
});

export default api;
