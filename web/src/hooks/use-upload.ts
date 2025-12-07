"use client";

import { useCallback, useState } from "react";
import type { UploadResponse } from "@/lib/types";
import { uploadFiles } from "@/lib/api";

interface UseUploadOptions {
  onSuccess?: (response: UploadResponse) => void;
  onError?: (error: Error) => void;
}

interface UseUploadResult {
  upload: (files: File[]) => Promise<UploadResponse | null>;
  isUploading: boolean;
  error: Error | null;
  reset: () => void;
}

const ALLOWED_EXTENSIONS = [
  // Documents
  ".pdf",
  ".docx",
  ".doc",
  ".txt",
  ".html",
  ".htm",
  ".rtf",
  ".pptx",
  ".ppt",
  ".xlsx",
  ".xls",
  ".csv",
  // Videos
  ".mp4",
  ".avi",
  ".mov",
];

export function useUpload({
  onSuccess,
  onError,
}: UseUploadOptions = {}): UseUploadResult {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const validateFiles = useCallback((files: File[]): string | null => {
    if (files.length === 0) {
      return "Please select at least one file";
    }

    for (const file of files) {
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        return `File type not supported: ${file.name}. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`;
      }
    }

    return null;
  }, []);

  const upload = useCallback(
    async (files: File[]): Promise<UploadResponse | null> => {
      // Validate files
      const validationError = validateFiles(files);
      if (validationError) {
        const err = new Error(validationError);
        setError(err);
        onError?.(err);
        return null;
      }

      setIsUploading(true);
      setError(null);

      try {
        const response = await uploadFiles(files);
        onSuccess?.(response);
        return response;
      } catch (err) {
        const error = err instanceof Error ? err : new Error("Upload failed");
        setError(error);
        onError?.(error);
        return null;
      } finally {
        setIsUploading(false);
      }
    },
    [validateFiles, onSuccess, onError]
  );

  const reset = useCallback(() => {
    setError(null);
    setIsUploading(false);
  }, []);

  return {
    upload,
    isUploading,
    error,
    reset,
  };
}

export { ALLOWED_EXTENSIONS };
