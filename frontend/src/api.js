import axios from "axios";

export const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const client = axios.create({
  baseURL: API,
  timeout: 90000,
});

export function serverError(err) {
  return (
    err?.response?.data?.detail ||
    err?.response?.data?.message ||
    null
  );
}

export default client;
