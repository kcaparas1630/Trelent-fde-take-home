"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { getGuide, getGuideHtml } from "@/lib/api";
import type { Guide } from "@/lib/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface Props {
  params: Promise<{ id: string }>;
}

export default function GuideViewPage({ params }: Props) {
  const resolvedParams = use(params);
  const [guide, setGuide] = useState<Guide | null>(null);
  const [html, setHtml] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadGuide() {
      try {
        const [guideData, htmlContent] = await Promise.all([
          getGuide(resolvedParams.id),
          getGuideHtml(resolvedParams.id),
        ]);
        setGuide(guideData);
        setHtml(htmlContent);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load guide");
      } finally {
        setLoading(false);
      }
    }

    loadGuide();
  }, [resolvedParams.id]);

  if (loading) {
    return (
      <main className="min-h-screen bg-background">
        <div className="max-w-4xl mx-auto px-4 py-12 text-center">
          <div className="w-8 h-8 mx-auto mb-4 rounded-full border-4 border-primary/30 border-t-primary animate-spin" />
          <p className="text-muted-foreground">Loading guide...</p>
        </div>
      </main>
    );
  }

  if (error || !guide) {
    return (
      <main className="min-h-screen bg-background">
        <div className="max-w-4xl mx-auto px-4 py-12">
          <Card>
            <CardContent className="py-8 text-center">
              <p className="text-red-600">{error || "Guide not found"}</p>
              <Link
                href="/guides"
                className="inline-block mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
              >
                Back to Guides
              </Link>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b sticky top-0 bg-background/95 backdrop-blur z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <Link
              href="/guides"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              ← Back to Guides
            </Link>
            <h1 className="text-xl font-bold mt-1">{guide.title}</h1>
            {guide.description && (
              <p className="text-sm text-muted-foreground">{guide.description}</p>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => {
                const blob = new Blob([html || ""], { type: "text/html" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `${guide.slug}.html`;
                a.click();
                URL.revokeObjectURL(url);
              }}
              className="px-3 py-1.5 text-sm bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80 transition-colors"
            >
              Download HTML
            </button>
            <button
              onClick={() => {
                if (html) {
                  const win = window.open("", "_blank");
                  if (win) {
                    win.document.write(html);
                    win.document.close();
                  }
                }
              }}
              className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
            >
              Open in New Tab
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        {html ? (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Preview</CardTitle>
              <CardDescription>
                This is how your guide will look when exported
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="border rounded-lg overflow-hidden">
                <iframe
                  srcDoc={html}
                  className="w-full min-h-[600px] bg-white"
                  title={guide.title}
                />
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              No HTML content available
            </CardContent>
          </Card>
        )}
      </div>
    </main>
  );
}
