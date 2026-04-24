import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PlanCard } from "./plan-card";

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: React.ComponentProps<"a">) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: vi.fn(),
  }),
}));

vi.mock("@/lib/hooks/use-plans", () => ({
  useActivatePlan: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    error: null,
  }),
  useDeletePlan: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
    error: null,
  }),
}));

describe("PlanCard", () => {
  afterEach(() => {
    cleanup();
  });

  it("shows the current badge and workbench link for the active plan", () => {
    render(
      <PlanCard
        plan={{
          id: "plan-1",
          title: "Python Learning Plan",
          goal: "Finish Python foundations in 8 weeks",
          status: "active",
          version: 2,
          created_at: "2026-04-08T10:00:00Z",
          updated_at: "2026-04-08T10:00:00Z",
          unit_count: 4,
          completed_unit_count: 1,
          progress_percent: 25,
          current_micro_plan_id: "micro-1",
          current_micro_plan_title: "Functions and loops",
          is_current: true,
        }}
      />,
    );

    expect(screen.getByText("进行中")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "进入工作台" })).toHaveAttribute("href", "/workbench");
    expect(screen.getByRole("button", { name: "删除计划" })).toBeInTheDocument();
  });

  it("hides the workbench link for a historical plan", () => {
    render(
      <PlanCard
        plan={{
          id: "plan-2",
          title: "CET-6 Learning Plan",
          goal: "Review vocabulary and reading",
          status: "completed",
          version: 1,
          created_at: "2026-04-01T10:00:00Z",
          updated_at: "2026-04-02T10:00:00Z",
          unit_count: 3,
          completed_unit_count: 3,
          progress_percent: 100,
          current_micro_plan_id: "micro-2",
          current_micro_plan_title: "Reading drills",
          is_current: false,
        }}
      />,
    );

    expect(screen.queryByText("进行中")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "进入工作台" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "查看计划" })).toHaveAttribute("href", "/plans/plan-2");
    expect(screen.getByRole("button", { name: "设为当前" })).toBeInTheDocument();
  });
});
