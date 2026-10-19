import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StatusBadge } from "@/components/documents/StatusBadge";
import { DocumentsTable } from "@/components/documents/DocumentsTable";
import type { DocumentRecord } from "@/types";

describe("StatusBadge", () => {
  it("renders Ready status with proper label", () => {
    render(<StatusBadge status="ready" />);
    expect(screen.getByText("Ready")).toBeInTheDocument();
  });

  it("renders Processing status with proper label", () => {
    render(<StatusBadge status="processing" />);
    expect(screen.getByText("Processing")).toBeInTheDocument();
  });

  it("renders Failed status with proper label", () => {
    render(<StatusBadge status="failed" title="Corrupt PDF" />);
    const badge = screen.getByText("Failed");
    expect(badge).toBeInTheDocument();
  });
});

describe("DocumentsTable", () => {
  const mockDocs: DocumentRecord[] = [
    {
      id: "doc-1",
      name: "handbook.pdf",
      size_bytes: 2048576,
      page_count: 24,
      chunk_count: 50,
      status: "ready",
      created_at: "2026-03-01T10:00:00Z",
    },
    {
      id: "doc-2",
      name: "financials.pdf",
      size_bytes: 1048576,
      page_count: 10,
      chunk_count: 20,
      status: "failed",
      error_message: "Scanned image unreadable",
      created_at: "2026-03-02T11:00:00Z",
    },
  ];

  it("renders document list items with metadata", () => {
    render(<DocumentsTable documents={mockDocs} onView={vi.fn()} onDelete={vi.fn()} />);

    expect(screen.getByText("handbook.pdf")).toBeInTheDocument();
    expect(screen.getByText("financials.pdf")).toBeInTheDocument();
    expect(screen.getByText("Scanned image unreadable")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toBeInTheDocument();
  });

  it("triggers onView and onDelete callbacks", () => {
    const onView = vi.fn();
    const onDelete = vi.fn();

    render(<DocumentsTable documents={mockDocs} onView={onView} onDelete={onDelete} />);

    const viewButton = screen.getByRole("button", { name: "View handbook.pdf" });
    fireEvent.click(viewButton);
    expect(onView).toHaveBeenCalledWith(mockDocs[0]);

    const deleteButton = screen.getByRole("button", { name: "Delete handbook.pdf" });
    fireEvent.click(deleteButton);
    expect(onDelete).toHaveBeenCalledWith(mockDocs[0]);
  });
});
