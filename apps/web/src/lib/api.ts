import type { AnalyzeRecoveryRequest, AnalyzeRecoveryResponse } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function analyzeRecovery(
  payload: AnalyzeRecoveryRequest,
): Promise<AnalyzeRecoveryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/recovery/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Analyze request failed with ${response.status}`);
  }

  return response.json();
}
