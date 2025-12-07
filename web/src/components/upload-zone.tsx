"use client";

import { useCallback, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { ALLOWED_EXTENSIONS } from "@/hooks/use-upload";

interface UploadZoneProps {
  onFilesSelected: (files: File[]) => void;
  isUploading?: boolean;
  disabled?: boolean;
}

export function UploadZone({
  onFilesSelected,
  isUploading = false,
  disabled = false,
}: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      if (disabled || isUploading) return;

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        onFilesSelected(files);
      }
    },
    [disabled, isUploading, onFilesSelected]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      if (files.length > 0) {
        onFilesSelected(files);
      }
      // Reset input
      e.target.value = "";
    },
    [onFilesSelected]
  );

  const acceptString = ALLOWED_EXTENSIONS.join(",");

  return (
    <Card
      className={`
        relative cursor-pointer transition-all duration-200
        ${isDragging ? "border-primary border-2 bg-primary/5" : "border-dashed border-2"}
        ${disabled || isUploading ? "opacity-50 cursor-not-allowed" : "hover:border-primary/50"}
      `}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <CardContent className="flex flex-col items-center justify-center py-12 px-6 text-center">
        <input
          type="file"
          multiple
          accept={acceptString}
          onChange={handleFileInput}
          disabled={disabled || isUploading}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
        />

        {isUploading ? (
          <>
            <div className="w-12 h-12 mb-4 rounded-full border-4 border-primary/30 border-t-primary animate-spin" />
            <p className="text-lg font-medium">Uploading...</p>
            <p className="text-sm text-muted-foreground mt-1">
              Please wait while your files are being uploaded
            </p>
          </>
        ) : (
          <>
            <svg
              className={`w-12 h-12 mb-4 ${isDragging ? "text-primary" : "text-muted-foreground"}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>

            <p className="text-lg font-medium">
              {isDragging ? "Drop files here" : "Drag & drop your documents"}
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              or click to browse
            </p>
            <p className="text-xs text-muted-foreground mt-4">
              Supported: PDF, Word, PowerPoint, Excel, Text, HTML, Videos (MP4, AVI, MOV)
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
