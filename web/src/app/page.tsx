"use client";

import { useState, useCallback, useEffect } from "react";
import Link from "next/link";
import { UploadZone } from "@/components/upload-zone";
import { JobProgress } from "@/components/job-progress";
import { GuideCard } from "@/components/guide-card";
import { useUpload } from "@/hooks/use-upload";
import { usePolling } from "@/hooks/use-polling";
import { listGuides, retryFailedFiles, listBatches } from "@/lib/api";
import type { Guide, BatchSummary } from "@/lib/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function Home() {
  const [currentBatchId, setCurrentBatchId] = useState<string | null>(null);
  const [guides, setGuides] = useState<Guide[]>([]);
  const [recentBatches, setRecentBatches] = useState<BatchSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Upload hook
  const { upload, isUploading, error: uploadError } = useUpload({
    onSuccess: (response) => {
      setCurrentBatchId(response.batch_id);
      setError(null);
    },
    onError: (err) => {
      setError(err.message);
    },
  });

  // Polling hook
  const { progress, isPolling } = usePolling({
    batchId: currentBatchId,
    interval: 2000,
    onComplete: async (finalProgress) => {
      // Refresh guides when complete
      if (
        finalProgress.status === "completed" ||
        finalProgress.status === "partial_failed"
      ) {
        await loadGuides();
      }
    },
  });

  // Load guides
  const loadGuides = useCallback(async () => {
    try {
      const response = await listGuides();
      setGuides(response.guides);
    } catch (err) {
      console.error("Failed to load guides:", err);
    }
  }, []);

  // Load recent batches
  const loadBatches = useCallback(async () => {
    try {
      const response = await listBatches(5);
      setRecentBatches(response.batches);
    } catch (err) {
      console.error("Failed to load batches:", err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadGuides();
    loadBatches();
  }, [loadGuides, loadBatches]);

  // Handle file selection
  const handleFilesSelected = useCallback(
    async (files: File[]) => {
      setError(null);
      await upload(files);
    },
    [upload]
  );

  // Handle retry
  const handleRetry = useCallback(async () => {
    if (!currentBatchId) return;
    try {
      await retryFailedFiles(currentBatchId);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Retry failed");
    }
  }, [currentBatchId]);

  const displayError = error || uploadError?.message;

  return (
    <main className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">Guide Generator</h1>
            <p className="text-sm text-muted-foreground">
              Convert your documents into clean HTML guides
            </p>
          </div>
          <nav className="flex gap-4">
            <Link
              href="/guides"
              className="text-sm font-medium hover:text-primary transition-colors"
            >
              View All Guides
            </Link>
          </nav>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left column: Upload and Progress */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Upload Documents</CardTitle>
                <CardDescription>
                  Upload your documents and we'll convert them into organized HTML guides
                </CardDescription>
              </CardHeader>
              <CardContent>
                <UploadZone
                  onFilesSelected={handleFilesSelected}
                  isUploading={isUploading}
                  disabled={isPolling}
                />
              </CardContent>
            </Card>

            {/* Error display */}
            {displayError && (
              <div className="p-4 bg-red-50 text-red-700 rounded-lg">
                {displayError}
              </div>
            )}

            {/* Progress display */}
            {progress && (
              <JobProgress progress={progress} onRetry={handleRetry} />
            )}

            {/* Recent batches */}
            {recentBatches.length > 0 && !progress && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Recent Conversions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {recentBatches.map((batch) => (
                      <div
                        key={batch.id}
                        className="flex items-center justify-between p-2 rounded-md hover:bg-muted cursor-pointer"
                        onClick={() => setCurrentBatchId(batch.id)}
                      >
                        <div>
                          <p className="text-sm font-medium">
                            {batch.total_files} files
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {new Date(batch.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        <span
                          className={`px-2 py-1 text-xs rounded-full ${
                            batch.status === "completed"
                              ? "bg-green-100 text-green-700"
                              : batch.status === "failed"
                                ? "bg-red-100 text-red-700"
                                : "bg-blue-100 text-blue-700"
                          }`}
                        >
                          {batch.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right column: Guides */}
          <div>
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Generated Guides</CardTitle>
                  {guides.length > 0 && (
                    <Link
                      href="/guides"
                      className="text-sm text-primary hover:underline"
                    >
                      View all
                    </Link>
                  )}
                </div>
                <CardDescription>
                  Your converted documents appear here
                </CardDescription>
              </CardHeader>
              <CardContent>
                {guides.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <svg
                      className="w-12 h-12 mx-auto mb-4 opacity-50"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                    <p>No guides yet</p>
                    <p className="text-sm mt-1">
                      Upload documents to get started
                    </p>
                  </div>
                ) : (
                  <div className="grid gap-4">
                    {guides.slice(0, 4).map((guide) => (
                      <GuideCard key={guide.id} guide={guide} />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </main>
  );
}
