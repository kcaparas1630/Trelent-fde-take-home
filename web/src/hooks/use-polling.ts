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
  const consecutiveErrorsRef = useRef(0);
  const completedBatchesRef = useRef<Set<string>>(new Set());
  const maxConsecutiveErrors = 5;

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPolling(false);
    consecutiveErrorsRef.current = 0;
  }, []);

  const fetchProgress = useCallback(async (isInitialFetch = false) => {
    if (!batchId) return;

    // Don't fetch if there's no active interval (polling has stopped)
    // BUT allow initial fetches even without interval
    if (!intervalRef.current && !isInitialFetch) {
      return;
    }

    try {
      const data = await getBatchProgress(batchId);
      setProgress(data);
      setError(null);
      consecutiveErrorsRef.current = 0; // Reset error count on success

      // Check if complete or failed - stop polling
      if (
        data.status === "completed" ||
        data.status === "failed" ||
        data.status === "partial_failed"
      ) {
        completedBatchesRef.current.add(batchId); // Mark as completed
        stopPolling();
        onComplete?.(data);
      }
    } catch (err) {
      consecutiveErrorsRef.current += 1;
      const error = err instanceof Error ? err : new Error("Unknown error");

      // Only stop polling after multiple consecutive errors
      if (consecutiveErrorsRef.current >= maxConsecutiveErrors) {
        setError(error);
        onError?.(error);
        stopPolling();
      }
      // Otherwise, continue polling - the next fetch might succeed
    }
  }, [batchId, stopPolling, onComplete, onError]);

  const startPolling = useCallback(async () => {
    if (!batchId || !enabled) return;

    // Don't start if already polling
    if (intervalRef.current) {
      return;
    }

    // Don't start if this batch already completed
    if (completedBatchesRef.current.has(batchId)) {
      return;
    }

    setIsPolling(true);
    setError(null);

    // Fetch immediately and check status
    await fetchProgress(true);

    // Only start interval if the batch is still processing
    // (fetchProgress will have stopped polling if it's already complete)
    if (!completedBatchesRef.current.has(batchId)) {
      intervalRef.current = setInterval(() => fetchProgress(false), interval);
    } else {
      setIsPolling(false);
    }
  }, [batchId, enabled, interval, fetchProgress]);

  // Auto-start polling when batchId changes
  useEffect(() => {
    if (batchId && enabled) {
      // Remove from completed set when user manually selects a batch
      // This allows viewing completed batches again
      if (completedBatchesRef.current.has(batchId)) {
        completedBatchesRef.current.delete(batchId);
      }
      startPolling();
    } else if (!batchId) {
      // Clear progress when batchId is null
      setProgress(null);
      setError(null);
      stopPolling();
    }

    return () => {
      stopPolling();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchId, enabled]); // Only re-run when batchId or enabled changes

  return {
    progress,
    isPolling,
    error,
    startPolling,
    stopPolling,
  };
}
