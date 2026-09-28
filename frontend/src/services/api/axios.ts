import axios from "axios";

// Base URL configuration:
// - Development: Vite proxy handles /api -> local nginx -> API
// - Production (Docker): nginx proxy handles /api -> http://api:8000/api
const api = axios.create({
  baseURL: "/api",
  timeout: 5000,
  headers: {
    "Content-Type": "application/json",
  },
});

// TODO: Handle player data route rate limits (HTTP 429): read Retry-After,
// show a clear cooldown message in the affected view, preserve existing data,
// and prevent automatic retries/refetches until the cooldown has passed.
export default api;
