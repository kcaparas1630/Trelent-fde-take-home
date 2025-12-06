"use client";

import Link from "next/link";
import type { Guide } from "@/lib/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface GuideCardProps {
  guide: Guide;
}

export function GuideCard({ guide }: GuideCardProps) {
  return (
    <Link href={`/guides/${guide.id}`}>
      <Card className="h-full hover:shadow-md transition-shadow cursor-pointer">
        <CardHeader>
          <CardTitle className="text-lg">{guide.title}</CardTitle>
          {guide.description && (
            <CardDescription>{guide.description}</CardDescription>
          )}
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              {guide.status === "completed" ? "Ready to view" : guide.status}
            </span>
            <span className="text-primary font-medium">View →</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
