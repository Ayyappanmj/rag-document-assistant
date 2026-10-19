import { Suspense } from "react";

import { ChatView } from "@/components/chat/ChatView";
import { Skeleton } from "@/components/ui/skeleton";

export default function ChatPage() {
  // useSearchParams (used by ChatView) must sit inside a Suspense boundary for production builds
  return (
    <Suspense fallback={<Skeleton className="h-[60vh] w-full rounded-xl" />}>
      <ChatView />
    </Suspense>
  );
}
