import axios from "axios";

// TODO [BUG] date handling is wrong in the browser, timezone is sent properly
// but the date is still UTC(?) based for the requested date (and all filters)
// therefore the response also is --> timezone seems to not be set properly
// in the whole browser session
// e.g: 23.09.2026 00:31 --> request Europe/Berlin, 22.09.2026
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

export default api;
