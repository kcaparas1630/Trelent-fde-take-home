export type Guide = {
  id: string;
  title: string;
  description: string;
  slug: string;
  status: string;
  batch_id: string;
};

export type BatchProgress = {
  batch_id: string;
  status: "pending" | "processing" | "completed" | "partial_failed" | "failed";
  stage: string;
  progress: number;
  total_files: number;
  processed_files: number;
  failed_files: number;
  message?: string;
  error_message?: string;
};

export type BatchSummary = {
  id: string;
  status: string;
  progress: number;
  total_files: number;
  processed_files: number;
  failed_files: number;
  created_at: string;
};

export type FileInfo = {
  id: string;
  filename: string;
  status: string;
  error_message?: string;
};

export type UploadResponse = {
  batch_id: string;
  status: string;
  message: string;
};
