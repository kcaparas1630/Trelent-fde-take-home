/**
 * API client for communicating with the Python backend.
 */

import type {
  BatchProgress,
  BatchSummary,
  FileInfo,
  Guide,
  UploadResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(response.status, error.detail || "Request failed");
  }

  return response.json();
}

// ==================== Upload ====================

export async function uploadFiles(files: File[]): Promise<UploadResponse> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });

  return fetchApi<UploadResponse>("/upload", {
    method: "POST",
    body: formData,
  });
}

// ==================== Batches ====================

export async function listBatches(
  limit = 50
): Promise<{ batches: BatchSummary[]; total: number }> {
  return fetchApi(`/batches?limit=${limit}`);
}

export async function getBatchProgress(batchId: string): Promise<BatchProgress> {
  return fetchApi(`/batches/${batchId}`);
}

export async function getBatchFiles(
  batchId: string
): Promise<{ files: FileInfo[]; total: number }> {
  return fetchApi(`/batches/${batchId}/files`);
}

export async function getFailedFiles(
  batchId: string
): Promise<{ files: FileInfo[]; total: number }> {
  return fetchApi(`/batches/${batchId}/failed`);
}

export async function retryFailedFiles(
  batchId: string
): Promise<UploadResponse> {
  return fetchApi(`/batches/${batchId}/retry`, {
    method: "POST",
  });
}

// ==================== Guides ====================

export async function listGuides(
  batchId?: string
): Promise<{ guides: Guide[]; total: number }> {
  const params = batchId ? `?batch_id=${batchId}` : "";
  return fetchApi(`/guides${params}`);
}

export async function getGuide(guideId: string): Promise<Guide> {
  return fetchApi(`/guides/${guideId}`);
}

export async function getGuideHtml(guideId: string): Promise<string> {
  const url = `${API_BASE}/guides/${guideId}/html`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new ApiError(response.status, "Failed to fetch guide HTML");
  }

  return response.text();
}

// ==================== Utility ====================

export async function getAllowedExtensions(): Promise<{ extensions: string[] }> {
  return fetchApi("/allowed-extensions");
}

export async function healthCheck(): Promise<{ status: string }> {
  return fetchApi("/health");
}
