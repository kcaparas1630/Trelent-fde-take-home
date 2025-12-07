"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listGuides } from "@/lib/api";
import type { Guide } from "@/lib/types";
import { GuideCard } from "@/components/guide-card";
import {
  Card,
  CardContent,
} from "@/components/ui/card";

export default function GuidesPage() {
  const [guides, setGuides] = useState<Guide[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadGuides() {
      try {
        const response = await listGuides();
        setGuides(response.guides);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load guides");
      } finally {
        setLoading(false);
      }
    }

    loadGuides();
  }, []);

  // Group guides by topic
  const groupedGuides = guides.reduce(
    (acc, guide) => {
      const topic = guide.title.split(" - ")[0] || "General";
      if (!acc[topic]) {
        acc[topic] = [];
      }
      acc[topic].push(guide);
      return acc;
    },
    {} as Record<string, Guide[]>
  );

  return (
    <main className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">Guide Library</h1>
            <p className="text-sm text-muted-foreground">
              Browse all generated guides
            </p>
          </div>
          <nav className="flex gap-4">
            <Link
              href="/"
              className="text-sm font-medium hover:text-primary transition-colors"
            >
              ← Back to Home
            </Link>
          </nav>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {loading ? (
          <div className="text-center py-12">
            <div className="w-8 h-8 mx-auto mb-4 rounded-full border-4 border-primary/30 border-t-primary animate-spin" />
            <p className="text-muted-foreground">Loading guides...</p>
          </div>
        ) : error ? (
          <Card>
            <CardContent className="py-8 text-center">
              <p className="text-red-600">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
              >
                Retry
              </button>
            </CardContent>
          </Card>
        ) : guides.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <svg
                className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50"
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
              <p className="text-lg font-medium">No guides yet</p>
              <p className="text-muted-foreground mt-1">
                Upload documents to generate your first guide
              </p>
              <Link
                href="/"
                className="inline-block mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
              >
                Upload Documents
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-8">
            {Object.entries(groupedGuides).map(([topic, topicGuides]) => (
              <section key={topic}>
                <h2 className="text-lg font-semibold mb-4">{topic}</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {topicGuides.map((guide) => (
                    <GuideCard key={guide.id} guide={guide} />
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
