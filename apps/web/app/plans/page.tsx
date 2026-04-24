"use client";

import React from "react";

import { PlanAssistantPanel } from "@/components/plan-assistant-panel";
import { PlanCard } from "@/components/plan-card";
import { QueryStateCard } from "@/components/query-state-card";
import { getErrorMessage } from "@/lib/api/errors";
import { usePlans } from "@/lib/hooks/use-plans";

export default function PlansPage() {
  const plansQuery = usePlans();
  const plans = plansQuery.data?.plans ?? [];

  return (
    <div className="flex h-full min-h-[calc(100vh-96px)]">
      {/* 左侧：计划卡片区 */}
      <section className="flex-1 pr-12">
        <header className="mb-8">
          <h1 className="text-[1.8rem] mb-2 font-bold text-ink">我的学习计划</h1>
          <p className="text-[0.95rem] text-slate-500">
            选择一个宏观计划进入对应的工作台，或通过右侧助手生成新计划。
          </p>
        </header>

        <div>
          {plansQuery.isLoading ? (
            <p className="text-sm text-slate-500">正在加载学习计划...</p>
          ) : plansQuery.error ? (
            <p className="text-sm text-red-600">{getErrorMessage(plansQuery.error)}</p>
          ) : plans.length === 0 ? (
            <p className="text-sm text-slate-500">当前还没有学习计划。可使用右侧 AI 助手创建。</p>
          ) : (
            <div className="grid gap-6 grid-cols-1 md:grid-cols-2 2xl:grid-cols-3">
              {plans.map((plan) => (
                <PlanCard key={plan.id} plan={plan} />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* 右侧：创建新计划助手 */}
      <aside className="w-[360px] border-l border-slate-200 pl-8 pb-12 flex flex-col shrink-0">
        <PlanAssistantPanel />
      </aside>
    </div>
  );
}
