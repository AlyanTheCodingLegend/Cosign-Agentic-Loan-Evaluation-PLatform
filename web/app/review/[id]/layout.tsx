import { Suspense } from "react";
import { Skeleton } from "@/components/ui";

// The page reads the id from the URL at runtime, so it streams in behind this fallback.
export default function CaseLayout({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<Skeleton className="mt-4 h-96" />}>{children}</Suspense>;
}
