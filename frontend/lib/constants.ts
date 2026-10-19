import { BarChart3, FileText, LayoutDashboard, MessagesSquare, Settings } from "lucide-react";

export const APP_NAME = "RAG Document Assistant";
export const GITHUB_URL =
  process.env.NEXT_PUBLIC_GITHUB_URL ?? "https://github.com/your-username/rag-document-assistant";

export const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/chat", label: "Chat", icon: MessagesSquare },
  { href: "/evaluation", label: "Evaluation", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
] as const;

export const TECH_BADGES = [
  "Python", "FastAPI", "Next.js", "FAISS", "BM25", "Sentence Transformers", "RAG", "NLP",
];

export const SAMPLE_QUESTIONS = [
  "Summarize the main points of this document.",
  "What are the key numbers or figures mentioned?",
  "What were the major revenue sources?",
  "Compare the figures mentioned across the uploaded documents.",
  "What risks or limitations are discussed?",
];
