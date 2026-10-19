"use client";

import { CircleCheck, Upload, CircleX } from "lucide-react";
import { useRef, useState, type DragEvent } from "react";
import { toast } from "sonner";

import { Progress } from "@/components/ui/progress";
import { uploadDocument } from "@/lib/api";
import { formatBytes } from "@/lib/format";
import { cn } from "@/lib/utils";

interface UploadItem {
  id: string;
  name: string;
  progress: number;
  state: "uploading" | "done" | "error";
  error?: string;
}

interface Props {
  maxMb: number;
  onUploaded: () => void;
}

export function UploadDropzone({ maxMb, onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [items, setItems] = useState<UploadItem[]>([]);

  const patch = (id: string, changes: Partial<UploadItem>) =>
    setItems((prev) => prev.map((item) => (item.id === id ? { ...item, ...changes } : item)));

  /** Client-side checks give instant feedback; the backend validates again. */
  function validate(file: File): string | null {
    if (!file.name.toLowerCase().endsWith(".pdf")) return "Only PDF files are allowed.";
    if (file.size === 0) return "The file is empty.";
    if (file.size > maxMb * 1024 * 1024) return `File is larger than ${maxMb} MB (${formatBytes(file.size)}).`;
    return null;
  }

  async function handleFiles(files: FileList | File[]) {
    for (const file of Array.from(files)) {
      const problem = validate(file);
      if (problem) {
        toast.error(`${file.name}: ${problem}`);
        continue;
      }
      const id = `${file.name}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      setItems((prev) => [{ id, name: file.name, progress: 0, state: "uploading" }, ...prev]);
      try {
        await uploadDocument(file, (progress) => patch(id, { progress }));
        patch(id, { progress: 100, state: "done" });
        toast.success(`${file.name} uploaded. Processing started.`);
        onUploaded();
      } catch (e) {
        const message = e instanceof Error ? e.message : "Upload failed";
        patch(id, { state: "error", error: message });
        toast.error(`${file.name}: ${message}`);
      }
    }
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    void handleFiles(e.dataTransfer.files);
  }

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload PDF files"
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors",
          dragging ? "border-primary bg-primary/10" : "border-border hover:border-primary/60 hover:bg-muted/40",
        )}
      >
        <Upload className="mb-3 size-8 text-muted-foreground" />
        <p className="text-sm font-medium">Drag and drop PDFs here, or click to browse</p>
        <p className="mt-1 text-xs text-muted-foreground">PDF only, up to {maxMb} MB each</p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          hidden
          onChange={(e) => {
            if (e.target.files) void handleFiles(e.target.files);
            e.target.value = ""; // allow re-selecting the same file
          }}
        />
      </div>

      {items.length > 0 && (
        <ul className="mt-4 space-y-3">
          {items.slice(0, 5).map((item) => (
            <li key={item.id} className="rounded-lg border border-border p-3">
              <div className="flex items-center justify-between gap-2 text-sm">
                <span className="truncate font-medium">{item.name}</span>
                {item.state === "done" && <CircleCheck className="size-4 shrink-0 text-emerald-400" />}
                {item.state === "error" && <CircleX className="size-4 shrink-0 text-red-400" />}
                {item.state === "uploading" && (
                  <span className="shrink-0 text-xs text-muted-foreground">{item.progress}%</span>
                )}
              </div>
              {item.state === "uploading" && <Progress value={item.progress} className="mt-2" />}
              {item.state === "error" && <p className="mt-1 text-xs text-red-400">{item.error}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
