import React from "react";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { QueryStateCard } from "./query-state-card";

describe("QueryStateCard", () => {
  it("renders a loading skeleton when loading", () => {
    render(<QueryStateCard title="Knowledge" loading emptyMessage="No assets yet." />);
    expect(screen.getByLabelText("loading")).toBeInTheDocument();
  });

  it("renders an error state when an error is provided", () => {
    render(<QueryStateCard title="Knowledge" error="Request failed" emptyMessage="No assets yet." />);
    expect(screen.getByText("Request failed")).toBeInTheDocument();
  });

  it("renders the empty message when the section is empty", () => {
    render(<QueryStateCard title="Knowledge" empty emptyMessage="No assets yet." />);
    expect(screen.getByText("No assets yet.")).toBeInTheDocument();
  });

  it("renders children when content exists", () => {
    render(
      <QueryStateCard title="Workflow" emptyMessage="unused">
        <p>learning</p>
      </QueryStateCard>,
    );
    expect(screen.getByText("learning")).toBeInTheDocument();
  });
});
