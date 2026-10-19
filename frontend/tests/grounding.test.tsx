import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GroundingBadge } from "@/components/chat/GroundingBadge";

describe("GroundingBadge", () => {
  it("renders verified status when grounded is true", () => {
    render(
      <GroundingBadge
        grounded={true}
        confidence={0.95}
        unsupportedClaims={[]}
        citationCoverage={1.0}
        invalidCitations={[]}
      />
    );
    expect(screen.getByText(/Grounded/i)).toBeInTheDocument();
    expect(screen.getByText(/95%/i)).toBeInTheDocument();
  });

  it("renders warning status when grounded is false", () => {
    render(
      <GroundingBadge
        grounded={false}
        confidence={0.4}
        unsupportedClaims={["Company revenue doubled in 2026."]}
        citationCoverage={0.3}
        invalidCitations={[]}
      />
    );
    expect(screen.getByText(/Possibly unsupported/i)).toBeInTheDocument();
    expect(screen.getByText(/Company revenue doubled in 2026/i)).toBeInTheDocument();
  });

  it("renders nothing when grounded is null", () => {
    const { container } = render(
      <GroundingBadge
        grounded={null}
        confidence={null}
        unsupportedClaims={[]}
        citationCoverage={null}
        invalidCitations={[]}
      />
    );
    expect(container.firstChild).toBeNull();
  });
});
