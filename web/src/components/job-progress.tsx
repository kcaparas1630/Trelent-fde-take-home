"use client";

import type { BatchProgress } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface JobProgressProps {
  progress: BatchProgress;
  onRetry?: () => void;
}

const STAGE_LABELS: Record<string, string> = {
  pending: "Waiting to start",
  uploading: "Uploading files",
  ingesting: "Converting documents to text",
  grouping: "Organizing by topic",
  rewriting: "Generating guide content",
  generating: "Creating HTML guides",
  completed: "Complete",
  partial_failed: "Completed with errors",
  failed: "Failed",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-400",
  processing: "bg-blue-500",
  completed: "bg-green-500",
  partial_failed: "bg-yellow-500",
  failed: "bg-red-500",
};

export function JobProgress({ progress, onRetry }: JobProgressProps) {
  const stageLabel = STAGE_LABELS[progress.stage] || progress.stage;
  const statusColor = STATUS_COLORS[progress.status] || "bg-gray-400";
  const isComplete = progress.status === "completed";
  const hasFailed =
    progress.status === "failed" || progress.status === "partial_failed";

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Processing Documents</CardTitle>
          <span
            className={`px-2 py-1 text-xs font-medium rounded-full text-white ${statusColor}`}
          >
            {progress.status}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress bar */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-muted-foreground">{stageLabel}</span>
            <span className="font-medium">{Math.round(progress.progress)}%</span>
          </div>
          <div className="h-3 bg-secondary rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                hasFailed ? "bg-red-500" : isComplete ? "bg-green-500" : "bg-primary"
              }`}
              style={{ width: `${progress.progress}%` }}
            />
          </div>
        </div>

        {/* File stats */}
        <div className="flex gap-4 text-sm">
          <div className="flex items-center gap-1">
            <span className="text-muted-foreground">Files:</span>
            <span className="font-medium">
              {progress.processed_files} / {progress.total_files}
            </span>
          </div>
          {progress.failed_files > 0 && (
            <div className="flex items-center gap-1 text-red-600">
              <span>Failed:</span>
              <span className="font-medium">{progress.failed_files}</span>
            </div>
          )}
        </div>

        {/* Message */}
        {progress.message && (
          <p className="text-sm text-muted-foreground">{progress.message}</p>
        )}

        {/* Error message */}
        {progress.error_message && (
          <div className="p-3 bg-red-50 text-red-700 rounded-md text-sm">
            {progress.error_message}
          </div>
        )}

        {/* Retry button for partial failures */}
        {progress.status === "partial_failed" && onRetry && (
          <button
            onClick={onRetry}
            className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
          >
            Retry Failed Files
          </button>
        )}
      </CardContent>
    </Card>
  );
}
