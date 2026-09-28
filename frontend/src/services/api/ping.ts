import api from "./axios";

export async function pingApi(): Promise<boolean> {
  await api.get("/ping");
  return true;
}
