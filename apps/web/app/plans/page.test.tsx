import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import PlansPage from "./page";

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

vi.mock("@/components/plan-assistant-panel", () => ({
  PlanAssistantPanel: () => <div>AI 助手面板</div>,
}));

vi.mock("@/lib/hooks/use-plans", () => ({
  usePlans: () => ({
    isLoading: false,
    error: null,
    data: {
      plans: [
        {
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
        },
        {
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
        },
      ],
    },
  }),
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

describe("/plans page", () => {
  it("renders multiple plan cards, highlights the current plan, and no longer shows the legacy form labels", () => {
    render(<PlansPage />);

    expect(screen.getByText("Python Learning Plan")).toBeInTheDocument();
    expect(screen.getByText("CET-6 Learning Plan")).toBeInTheDocument();
    expect(screen.getByText("进行中")).toBeInTheDocument();
    expect(screen.getByText("AI 助手面板")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "设为当前" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "删除计划" })).toHaveLength(2);
    expect(screen.queryByText("学习目标")).not.toBeInTheDocument();
    expect(screen.queryByText("题型偏好")).not.toBeInTheDocument();
  });
});
