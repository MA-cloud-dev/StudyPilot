"use client";

import Link from "next/link";

import { QueryStateCard } from "@/components/query-state-card";
import { getErrorMessage } from "@/lib/api/errors";
import { useCurrentPlan } from "@/lib/hooks/use-current-plan";
import { useProfile } from "@/lib/hooks/use-profile";
import { useCurrentWorkflow } from "@/lib/hooks/use-current-workflow";

export default function HomePage() {
  const workflow = useCurrentWorkflow();
  const profile = useProfile();
  const currentPlan = useCurrentPlan();

  const hasProfile = Boolean(profile.data);
  const hasPlan = Boolean(currentPlan.data?.current_micro_plan || currentPlan.data?.macro_plan);

  const primaryCta = !hasProfile
    ? { href: "/profile", label: "先完成建档" }
    : hasPlan
      ? { href: "/workbench", label: "继续当前学习" }
      : { href: "/plans", label: "生成第一份计划" };

  return (
    <div className="space-y-12">
      <header className="border-b border-slate-200 pb-8">
        <p className="text-sm font-semibold uppercase tracking-[0.25em] text-accent">StudyPilot</p>
        <h2 className="mt-4 text-3xl font-bold text-ink">阶段三纵向联调入口</h2>
        <p className="mt-4 max-w-3xl text-sm leading-relaxed text-slate-600">
          首页持续读取真实 workflow、profile 和 current plan，用于串联阶段三的整条学习闭环。
        </p>
        <div className="mt-8 flex gap-4">
          <Link className="border border-transparent bg-accent px-6 py-3 text-sm font-medium text-white hover:bg-red-700 transition" data-testid="home-primary-cta" href={primaryCta.href}>
            {primaryCta.label}
          </Link>
          <Link className="border border-slate-200 bg-white px-6 py-3 text-sm font-medium text-ink hover:bg-slate-50 transition" href="/knowledge">
            管理知识仓库
          </Link>
        </div>
      </header>

      <div className="grid gap-8 lg:grid-cols-3">
        <QueryStateCard
          title="当前工作流"
          loading={workflow.isLoading}
          error={workflow.error ? getErrorMessage(workflow.error) : null}
          empty={!workflow.data}
          emptyMessage="当前没有可用 workflow。"
        >
          {workflow.data ? (
            <div className="space-y-2 text-sm text-slate-700">
              <p className="font-semibold text-ink">{workflow.data.current_stage}</p>
              <p>{workflow.data.next_action}</p>
            </div>
          ) : null}
        </QueryStateCard>

        <QueryStateCard
          title="建档状态"
          loading={profile.isLoading}
          error={profile.error ? getErrorMessage(profile.error) : null}
          empty={!profile.data}
          emptyMessage="当前还没有学习者档案。"
        >
          {profile.data ? (
            <div className="space-y-2 text-sm text-slate-700">
              <p className="font-semibold text-ink">{profile.data.subject_scope}</p>
              <p>{profile.data.learning_goals}</p>
            </div>
          ) : null}
        </QueryStateCard>

        <QueryStateCard
          title="计划状态"
          loading={currentPlan.isLoading}
          error={currentPlan.error ? getErrorMessage(currentPlan.error) : null}
          empty={!currentPlan.data?.macro_plan}
          emptyMessage="当前还没有已生成计划。"
        >
          {currentPlan.data?.macro_plan ? (
            <div className="space-y-2 text-sm text-slate-700">
              <p className="font-semibold text-ink">{currentPlan.data.macro_plan.title}</p>
              <p>{currentPlan.data.current_micro_plan?.title ?? "暂无当前微观计划"}</p>
            </div>
          ) : null}
        </QueryStateCard>
      </div>
    </div>
  );
}
