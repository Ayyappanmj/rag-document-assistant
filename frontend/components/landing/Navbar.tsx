import Link from "next/link";

import { Brand } from "@/components/layout/Brand";
import { GithubIcon } from "@/components/common/GithubIcon";
import { buttonVariants } from "@/components/ui/button";
import { GITHUB_URL } from "@/lib/constants";

export function Navbar() {
  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Brand />
        <nav className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
          <a href="#features" className="hover:text-foreground">Features</a>
          <a href="#architecture" className="hover:text-foreground">Architecture</a>
          <a href="#evaluation" className="hover:text-foreground">Evaluation</a>
        </nav>
        <div className="flex items-center gap-2">
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
            className={buttonVariants({ variant: "ghost", size: "sm" })}
          >
            <GithubIcon /> GitHub
          </a>
          <Link href="/dashboard" className={buttonVariants({ size: "sm" })}>
            Open app
          </Link>
        </div>
      </div>
    </header>
  );
}
