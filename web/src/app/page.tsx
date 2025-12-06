import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center p-8">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Welcome</CardTitle>
          <CardDescription>Your app starts here.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Good luck!
          </p>
          <Link href="/example-guide">Sample Guide</Link>
        </CardContent>
      </Card>
    </main>
  );
}
