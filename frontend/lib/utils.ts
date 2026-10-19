import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Joins class names and resolves conflicting Tailwind classes (same file `shadcn init` creates). */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
