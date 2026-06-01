import type {
  AnalyzeRecoveryRequest,
  AnalyzeRecoveryResponse,
  FeedbackRequest,
  RecoveryHistoryItem,
  RunScreenshotExtractResponse,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

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

export async function submitFeedback(
  recoveryId: number,
  payload: FeedbackRequest,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/recovery/${recoveryId}/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Feedback request failed with ${response.status}`);
  }
}

export async function fetchRecoveryHistory(limit = 7): Promise<RecoveryHistoryItem[]> {
  const response = await fetch(`${API_BASE_URL}/api/recovery/history?limit=${limit}`);

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `History request failed with ${response.status}`);
  }

  return response.json();
}

export async function extractRunScreenshot(file: File): Promise<RunScreenshotExtractResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/run-screenshot/extract`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Screenshot extraction failed with ${response.status}`);
  }

  return response.json();
}
