import { ArrowRight, Play, Upload } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { GithubIcon } from "@/components/common/GithubIcon";
import { buttonVariants } from "@/components/ui/button";
import { GITHUB_URL, TECH_BADGES } from "@/lib/constants";

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-0 -z-10 h-[420px] w-[820px] -translate-x-1/2 rounded-full bg-gradient-to-r from-violet-600/30 to-cyan-500/20 blur-3xl"
      />
      <div className="mx-auto max-w-4xl px-4 pb-20 pt-20 text-center md:pt-28">
        <Badge variant="outline" className="mb-6 gap-1.5 px-3 py-1">
          Free and open source <ArrowRight className="size-3" /> runs locally with Ollama
        </Badge>
        <h1 className="text-4xl font-bold tracking-tight md:text-6xl">
          <span className="bg-gradient-to-r from-violet-400 to-cyan-300 bg-clip-text text-transparent">
            RAG Document Assistant
          </span>
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-muted-foreground md:text-xl">
          Production-Grade Retrieval-Augmented Generation for Complex Documents
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link href="/documents" className={buttonVariants({ size: "lg" })}>
            <Upload className="size-4" /> Upload Documents
          </Link>
          <Link href="/chat" className={buttonVariants({ size: "lg", variant: "secondary" })}>
            <Play className="size-4" /> Try Demo
          </Link>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
            className={buttonVariants({ size: "lg", variant: "outline" })}
          >
            <GithubIcon /> GitHub
          </a>
        </div>
        <ul className="mt-10 flex flex-wrap items-center justify-center gap-2" aria-label="Technologies">
          {TECH_BADGES.map((tech) => (
            <li key={tech}>
              <Badge variant="secondary">{tech}</Badge>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
