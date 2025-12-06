"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { BatchProgress } from "@/lib/types";
import { getBatchProgress } from "@/lib/api";

interface UsePollingOptions {
  batchId: string | null;
  interval?: number;
  enabled?: boolean;
  onComplete?: (progress: BatchProgress) => void;
  onError?: (error: Error) => void;
}

interface UsePollingResult {
  progress: BatchProgress | null;
  isPolling: boolean;
  error: Error | null;
  startPolling: () => void;
  stopPolling: () => void;
}

export function usePolling({
  batchId,
  interval = 2000,
  enabled = true,
  onComplete,
  onError,
}: UsePollingOptions): UsePollingResult {
  const [progress, setProgress] = useState<BatchProgress | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const fetchProgress = useCallback(async () => {
    if (!batchId) return;

    try {
      const data = await getBatchProgress(batchId);
      setProgress(data);
      setError(null);

      // Check if complete or failed - stop polling
      if (
        data.status === "completed" ||
        data.status === "failed" ||
        data.status === "partial_failed"
      ) {
        stopPolling();
        onComplete?.(data);
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Unknown error");
      setError(error);
      onError?.(error);
      // Stop polling on error to prevent infinite requests
      stopPolling();
    }
  }, [batchId, stopPolling, onComplete, onError]);

  const startPolling = useCallback(() => {
    if (!batchId || !enabled) return;

    setIsPolling(true);
    setError(null);

    // Fetch immediately
    fetchProgress();

    // Start interval
    intervalRef.current = setInterval(fetchProgress, interval);
  }, [batchId, enabled, interval, fetchProgress]);

  // Auto-start polling when batchId changes
  useEffect(() => {
    if (batchId && enabled) {
      startPolling();
    }

    return () => {
      stopPolling();
    };
  }, [batchId, enabled, startPolling, stopPolling]);

  return {
    progress,
    isPolling,
    error,
    startPolling,
    stopPolling,
  };
}
