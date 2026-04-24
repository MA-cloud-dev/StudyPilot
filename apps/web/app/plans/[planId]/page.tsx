"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import React from "react";

import { QueryStateCard } from "@/components/query-state-card";
import { getErrorMessage } from "@/lib/api/errors";
import { useActivatePlan, useDeletePlan, usePlanDetail } from "@/lib/hooks/use-plans";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function PlanDetailPage() {
  const router = useRouter();
  const params = useParams<{ planId: string }>();
  const planId = params.planId;
  const planDetail = usePlanDetail(planId);
  const activatePlan = useActivatePlan();
  const deletePlan = useDeletePlan();
  const detail = planDetail.data;
  const milestones = detail?.macro_plan.milestones ?? [];
  const microPlans = detail?.micro_plans ?? [];
  const actionError = activatePlan.error || deletePlan.error;

  const handleActivatePlan = async () => {
    await activatePlan.mutateAsync({ planId });
  };

  const handleDeletePlan = async () => {
    if (!detail) {
      return;
    }
    if (!window.confirm(`确认删除计划“${detail.macro_plan.title}”吗？删除后将不会在计划中心继续展示。`)) {
      return;
    }

    await deletePlan.mutateAsync({ planId });
    router.push("/plans");
    router.refresh();
  };

  return (
    <div className="space-y-6">
      <header className="rounded-[2rem] border border-slate-200 bg-white/85 p-6 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-[0.25em] text-accent">Plan Detail</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-slate-900">
          {detail?.macro_plan.title ?? "学习计划详情"}
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
          查看这一份学习计划的目标、阶段里程碑和全部微观计划。当前正在执行的微观计划会高亮显示。
        </p>
      </header>

      <QueryStateCard
        title="宏观计划"
        loading={planDetail.isLoading}
        error={planDetail.error ? getErrorMessage(planDetail.error) : null}
        empty={!detail}
        emptyMessage="未找到对应的学习计划。"
      >
        {detail ? (
          <div className="space-y-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-3">
                  {detail.is_current ? (
                    <span className="inline-flex rounded-full bg-accent px-3 py-1 text-xs font-semibold text-white">
                      当前计划
                    </span>
                  ) : null}
                  {!detail.is_current ? (
                    <button
                      className="rounded-full border border-accent px-4 py-2 text-sm font-semibold text-accent transition hover:bg-accent hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={activatePlan.isPending}
                      onClick={handleActivatePlan}
                      type="button"
                    >
                      {activatePlan.isPending ? "切换中..." : "设为当前计划"}
                    </button>
                  ) : null}
                  <button
                    className="rounded-full border border-rose-200 px-4 py-2 text-sm font-semibold text-rose-600 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={deletePlan.isPending}
                    onClick={handleDeletePlan}
                    type="button"
                  >
                    {deletePlan.isPending ? "删除中..." : "删除计划"}
                  </button>
                </div>
                <div>
                  <p className="text-2xl font-semibold text-slate-900">{detail.macro_plan.title}</p>
                  <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">{detail.macro_plan.goal}</p>
                </div>
              </div>
              <div className="grid gap-3 text-sm text-slate-600 md:grid-cols-2">
                <div className="rounded-2xl bg-white px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-400">时长</p>
                  <p className="mt-2 font-medium text-slate-900">
                    {detail.macro_plan.duration.value} {String(detail.macro_plan.duration.unit)}
                  </p>
                </div>
                <div className="rounded-2xl bg-white px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-400">状态 / 版本</p>
                  <p className="mt-2 font-medium text-slate-900">
                    {detail.macro_plan.status} / v{detail.macro_plan.version}
                  </p>
                </div>
                <div className="rounded-2xl bg-white px-4 py-3 md:col-span-2">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-400">最近更新</p>
                  <p className="mt-2 font-medium text-slate-900">{formatDate(detail.macro_plan.updated_at)}</p>
                </div>
              </div>
            </div>

            {actionError ? <p className="text-sm text-rose-600">{getErrorMessage(actionError)}</p> : null}

            <section className="space-y-3">
              <h2 className="text-lg font-semibold text-slate-900">阶段里程碑</h2>
              <div className="grid gap-4 md:grid-cols-2">
                {milestones.map((milestone, index) => (
                  <article className="rounded-3xl border border-slate-200 bg-white p-5" key={`${detail.macro_plan.id}-milestone-${index}`}>
                    <p className="text-sm font-semibold uppercase tracking-[0.2em] text-accent">Milestone {index + 1}</p>
                    <p className="mt-3 text-lg font-semibold text-slate-900">{String(milestone.title ?? `阶段 ${index + 1}`)}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{String(milestone.target ?? "")}</p>
                  </article>
                ))}
              </div>
            </section>
          </div>
        ) : null}
      </QueryStateCard>

      <QueryStateCard
        title="微观计划"
        loading={planDetail.isLoading}
        error={planDetail.error ? getErrorMessage(planDetail.error) : null}
        empty={!detail || microPlans.length === 0}
        emptyMessage="当前计划下还没有微观计划。"
      >
        {detail ? (
          <div className="space-y-4">
            {microPlans.map((microPlan) => {
              const isCurrentMicroPlan = detail.current_micro_plan_id === microPlan.id;
              const topics = microPlan.topics ?? [];
              const tasks = microPlan.tasks ?? [];
              const completionCriteria = microPlan.completion_criteria ?? [];

              return (
                <article
                  className={[
                    "rounded-[2rem] border p-5 transition",
                    isCurrentMicroPlan
                      ? "border-accent bg-accent/5 shadow-sm"
                      : "border-slate-200 bg-white",
                  ].join(" ")}
                  key={microPlan.id}
                >
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <div className="flex flex-wrap items-center gap-3">
                        <h3 className="text-xl font-semibold text-slate-900">{microPlan.title}</h3>
                        {isCurrentMicroPlan ? (
                          <span className="rounded-full bg-accent px-3 py-1 text-xs font-semibold text-white">
                            当前微观计划
                          </span>
                        ) : null}
                      </div>
                      <p className="mt-2 text-sm text-slate-500">
                        单元 {microPlan.unit_id} · 预计 {microPlan.estimated_duration} 分钟 · {microPlan.status}
                      </p>
                    </div>
                    <p className="text-sm text-slate-500">{formatDate(microPlan.updated_at)}</p>
                  </div>

                  <div className="mt-5 grid gap-4 xl:grid-cols-3">
                    <section className="space-y-2 rounded-2xl bg-slate-50 px-4 py-4">
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Topics</p>
                      <div className="flex flex-wrap gap-2">
                        {topics.map((topic) => (
                          <span className="rounded-full bg-white px-3 py-1 text-sm font-medium text-slate-700" key={topic}>
                            {topic}
                          </span>
                        ))}
                      </div>
                    </section>
                    <section className="space-y-2 rounded-2xl bg-slate-50 px-4 py-4">
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Tasks</p>
                      <ul className="space-y-2 text-sm text-slate-700">
                        {tasks.map((task, index) => (
                          <li className="rounded-2xl bg-white px-3 py-3" key={`${microPlan.id}-task-${index}`}>
                            <p className="font-medium text-slate-900">{String(task.title ?? `Task ${index + 1}`)}</p>
                            <p className="mt-1 text-slate-500">{String(task.status ?? "pending")}</p>
                          </li>
                        ))}
                      </ul>
                    </section>
                    <section className="space-y-2 rounded-2xl bg-slate-50 px-4 py-4">
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Completion</p>
                      <ul className="space-y-2 text-sm text-slate-700">
                        {completionCriteria.map((criterion) => (
                          <li className="rounded-2xl bg-white px-3 py-3" key={criterion}>
                            {criterion}
                          </li>
                        ))}
                      </ul>
                    </section>
                  </div>
                </article>
              );
            })}
          </div>
        ) : null}
      </QueryStateCard>

      {detail?.is_current ? (
        <div className="flex justify-end">
          <Link className="rounded-full bg-accent px-5 py-3 text-sm font-semibold text-white" href="/workbench">
            进入学习工作台
          </Link>
        </div>
      ) : null}
    </div>
  );
}
