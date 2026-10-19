import { Sparkles } from "lucide-react";
import Link from "next/link";

import { APP_NAME } from "@/lib/constants";

export function Brand() {
  return (
    <Link href="/" className="flex items-center gap-2 font-semibold">
      <span className="flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-cyan-400 text-white">
        <Sparkles className="size-4" />
      </span>
      <span>{APP_NAME}</span>
    </Link>
  );
}
