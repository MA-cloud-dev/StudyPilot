"use client";

import Link from "next/link";
import React from "react";
import { useRouter } from "next/navigation";

import { getErrorMessage } from "@/lib/api/errors";
import { useActivatePlan, useDeletePlan } from "@/lib/hooks/use-plans";
import type { components } from "@/lib/api/schema";

type PlanCardSummary = components["schemas"]["PlanCardSummary"];

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function PlanCard({ plan }: { plan: PlanCardSummary }) {
  const router = useRouter();
  const activatePlan = useActivatePlan();
  const deletePlan = useDeletePlan();

  const handleActivatePlan = async () => {
    await activatePlan.mutateAsync({ planId: plan.id });
  };

  const handleDeletePlan = async () => {
    if (!window.confirm(`确认删除计划“${plan.title}”吗？删除后将不会在计划中心继续展示。`)) {
      return;
    }

    await deletePlan.mutateAsync({ planId: plan.id });
    router.refresh();
  };

  const actionError = activatePlan.error || deletePlan.error;

  return (
    <article className="relative flex h-full flex-col border border-slate-200 bg-white p-6 transition hover:border-ink">
      <div className="flex-1 flex flex-col gap-6">
        <div>
          {plan.is_current ? (
             <span className="inline-block bg-accent px-2 py-0.5 text-xs font-semibold text-white mb-3">
               进行中
             </span>
          ) : null}
          <h3 className="text-lg font-semibold text-ink line-clamp-2 leading-snug">
            {plan.title}
          </h3>
          <p className="mt-2 text-sm text-slate-500 line-clamp-2">
            {plan.goal}
          </p>
        </div>

        <div className="space-y-2 mt-auto">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-500">进度：{plan.progress_percent}%</span>
          </div>
          <div className="h-1.5 w-full bg-slate-100">
            <div className="h-full bg-accent" style={{ width: `${plan.progress_percent}%` }} />
          </div>
        </div>

        <div className="flex gap-3">
          <Link
            className="flex-1 border border-slate-200 py-2.5 text-sm font-medium text-center text-ink hover:bg-slate-50 transition"
            href={`/plans/${plan.id}`}
          >
            查看计划
          </Link>
          {plan.is_current ? (
            <Link
              className="flex-1 bg-accent py-2.5 text-sm font-medium text-center text-white hover:bg-red-700 transition"
              href="/workbench"
            >
              进入工作台
            </Link>
          ) : (
            <button
              className="flex-1 border border-accent py-2.5 text-sm font-medium text-center text-accent transition hover:bg-accent hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
              disabled={activatePlan.isPending}
              onClick={handleActivatePlan}
              type="button"
            >
              {activatePlan.isPending ? "切换中..." : "设为当前"}
            </button>
          )}
        </div>

        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-slate-400">最近更新 {formatDate(plan.updated_at)}</p>
          <button
            className="text-sm font-medium text-rose-600 transition hover:text-rose-700 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={deletePlan.isPending}
            onClick={handleDeletePlan}
            type="button"
          >
            {deletePlan.isPending ? "删除中..." : "删除计划"}
          </button>
        </div>

        {actionError ? <p className="text-sm text-rose-600">{getErrorMessage(actionError)}</p> : null}
      </div>
    </article>
  );
}
