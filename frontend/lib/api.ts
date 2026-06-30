import type { AppConfig, PatientProfile } from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://localhost:8000";

export async function startMatch(profile: PatientProfile): Promise<string> {
  const res = await fetch(`${API_BASE}/api/match/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Failed to start matching (${res.status}). ${detail}`);
  }
  const data = await res.json();
  return data.job_id as string;
}

export function streamUrl(jobId: string): string {
  return `${API_BASE}/api/match/stream/${jobId}`;
}

export async function fetchConfig(): Promise<AppConfig | null> {
  try {
    const res = await fetch(`${API_BASE}/api/config`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as AppConfig;
  } catch {
    return null;
  }
}
