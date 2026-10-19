import { APP_NAME } from "@/lib/constants";

export function Footer() {
  return (
    <footer className="border-t border-border py-8 text-center text-sm text-muted-foreground">
      {APP_NAME}. Built with FastAPI, Next.js, FAISS and BM25.
    </footer>
  );
}
