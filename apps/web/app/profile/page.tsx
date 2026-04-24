"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import { QueryStateCard } from "@/components/query-state-card";
import { getErrorMessage } from "@/lib/api/errors";
import { useProfile, useUpsertProfile } from "@/lib/hooks/use-profile";

const questionTypeOptions = [
  { value: "single_choice", label: "单选题" },
  { value: "multiple_choice", label: "多选题" },
  { value: "short_answer", label: "简答题" },
];

const defaultForm = {
  learning_goals: "",
  subject_scope: "",
  current_level: "beginner",
  time_budget_value: "45",
  time_budget_unit: "day",
  preferred_style: "practical",
  preferred_difficulty: "medium",
  preferred_question_types: ["single_choice"],
  behavior_summary: "",
};

export default function ProfilePage() {
  const profile = useProfile();
  const upsertProfile = useUpsertProfile();
  const [formState, setFormState] = useState(defaultForm);

  useEffect(() => {
    if (!profile.data) {
      return;
    }

    setFormState({
      learning_goals: profile.data.learning_goals,
      subject_scope: profile.data.subject_scope,
      current_level: profile.data.current_level,
      time_budget_value: String(profile.data.time_budget.value ?? ""),
      time_budget_unit: String(profile.data.time_budget.unit ?? "day"),
      preferred_style: profile.data.preferred_style,
      preferred_difficulty: profile.data.preferred_difficulty,
      preferred_question_types:
        (profile.data.preferred_question_types ?? []).length > 0
          ? (profile.data.preferred_question_types ?? [])
          : defaultForm.preferred_question_types,
      behavior_summary: profile.data.behavior_summary,
    });
  }, [profile.data]);

  const handleQuestionTypeToggle = (value: string) => {
    setFormState((current) => ({
      ...current,
      preferred_question_types: current.preferred_question_types.includes(value)
        ? current.preferred_question_types.filter((item) => item !== value)
        : [...current.preferred_question_types, value],
    }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await upsertProfile.mutateAsync({
      learning_goals: formState.learning_goals,
      subject_scope: formState.subject_scope,
      current_level: formState.current_level,
      time_budget: {
        unit: formState.time_budget_unit,
        value: Number(formState.time_budget_value),
      },
      preferred_style: formState.preferred_style,
      preferred_difficulty: formState.preferred_difficulty,
      preferred_question_types: formState.preferred_question_types,
      behavior_summary: formState.behavior_summary,
    });
  };

  if (profile.isLoading) {
    return (
      <QueryStateCard
        title="学习者档案"
        loading
        emptyMessage="unused"
      />
    );
  }

  if (profile.error) {
    return (
      <QueryStateCard
        title="学习者档案"
        error={getErrorMessage(profile.error)}
        emptyMessage="unused"
      />
    );
  }

  return (
    <div className="space-y-12">
      <header className="border-b border-slate-200 pb-8">
        <p className="text-sm font-semibold uppercase tracking-[0.25em] text-accent">Profile</p>
        <h2 className="mt-4 text-3xl font-bold text-ink">最小建档入口</h2>
        <p className="mt-4 max-w-3xl text-sm leading-relaxed text-slate-600">
          先完成学习目标、基础与偏好设置，后续计划生成会直接读取这份真实档案。
        </p>
      </header>

      <div className="grid gap-8 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="border border-slate-200 bg-white p-8">
          <div className="flex items-start justify-between gap-4 border-b border-slate-100 pb-4 mb-6">
            <div>
              <h3 className="text-xl font-bold text-ink">
                {profile.data ? "更新学习者档案" : "创建学习者档案"}
              </h3>
              <p className="mt-2 text-sm text-slate-500">
                {profile.data ? "你可以随时调整偏好，计划中心会读取最新档案。" : "当前处于 onboarding，先建档才能生成计划。"}
              </p>
            </div>
            <span className="bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
              {profile.data ? "ready" : "onboarding"}
            </span>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-ink">学习目标</span>
              <textarea
                className="min-h-28 w-full border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-ink"
                onChange={(event) => setFormState((current) => ({ ...current, learning_goals: event.target.value }))}
                placeholder="例如：8 周内打好概率论基础，并完成一次 checkpoint 测试。"
                required
                value={formState.learning_goals}
              />
            </label>

            <div className="grid gap-6 md:grid-cols-2">
              <label className="block space-y-2">
                <span className="text-sm font-medium text-ink">学科范围</span>
                <input
                  className="w-full border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-ink"
                  onChange={(event) => setFormState((current) => ({ ...current, subject_scope: event.target.value }))}
                  placeholder="例如：math / databases / english"
                  required
                  value={formState.subject_scope}
                />
              </label>

              <label className="block space-y-2">
                <span className="text-sm font-medium text-ink">当前基础</span>
                <select
                  className="w-full border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-ink bg-white"
                  onChange={(event) => setFormState((current) => ({ ...current, current_level: event.target.value }))}
                  value={formState.current_level}
                >
                  <option value="beginner">beginner</option>
                  <option value="intermediate">intermediate</option>
                  <option value="advanced">advanced</option>
                </select>
              </label>
            </div>

            <div className="grid gap-6 md:grid-cols-[1fr_180px]">
              <label className="block space-y-2">
                <span className="text-sm font-medium text-ink">时间预算</span>
                <input
                  className="w-full border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-ink"
                  min="1"
                  onChange={(event) => setFormState((current) => ({ ...current, time_budget_value: event.target.value }))}
                  required
                  type="number"
                  value={formState.time_budget_value}
                />
              </label>
              <label className="block space-y-2">
                <span className="text-sm font-medium text-ink">单位</span>
                <select
                  className="w-full border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-ink bg-white"
                  onChange={(event) => setFormState((current) => ({ ...current, time_budget_unit: event.target.value }))}
                  value={formState.time_budget_unit}
                >
                  <option value="day">day</option>
                  <option value="week">week</option>
                  <option value="session">session</option>
                </select>
              </label>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <label className="block space-y-2">
                <span className="text-sm font-medium text-ink">讲解风格</span>
                <select
                  className="w-full border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-ink bg-white"
                  onChange={(event) => setFormState((current) => ({ ...current, preferred_style: event.target.value }))}
                  value={formState.preferred_style}
                >
                  <option value="practical">practical</option>
                  <option value="rigorous">rigorous</option>
                  <option value="visual">visual</option>
                </select>
              </label>

              <label className="block space-y-2">
                <span className="text-sm font-medium text-ink">难度偏好</span>
                <select
                  className="w-full border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-ink bg-white"
                  onChange={(event) => setFormState((current) => ({ ...current, preferred_difficulty: event.target.value }))}
                  value={formState.preferred_difficulty}
                >
                  <option value="easy">easy</option>
                  <option value="medium">medium</option>
                  <option value="hard">hard</option>
                </select>
              </label>
            </div>

            <fieldset className="space-y-3 pt-2">
              <legend className="text-sm font-medium text-ink">题型偏好</legend>
              <div className="flex flex-wrap gap-3 mt-2">
                {questionTypeOptions.map((option) => {
                  const selected = formState.preferred_question_types.includes(option.value);

                  return (
                    <label
                      className={[
                        "inline-flex cursor-pointer items-center gap-2 border px-4 py-2 text-sm transition",
                        selected ? "border-accent bg-accent text-white" : "border-slate-200 bg-white text-ink hover:border-ink",
                      ].join(" ")}
                      key={option.value}
                    >
                      <input
                        checked={selected}
                        className="sr-only"
                        onChange={() => handleQuestionTypeToggle(option.value)}
                        type="checkbox"
                      />
                      {option.label}
                    </label>
                  );
                })}
              </div>
            </fieldset>

            <label className="block space-y-2 pt-2">
              <span className="text-sm font-medium text-ink">行为摘要</span>
              <textarea
                className="min-h-24 w-full border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-ink"
                onChange={(event) => setFormState((current) => ({ ...current, behavior_summary: event.target.value }))}
                placeholder="可选。记录你当前的学习节奏、常见问题或偏好。"
                value={formState.behavior_summary}
              />
            </label>

            {upsertProfile.error ? <p className="text-sm text-red-600">{getErrorMessage(upsertProfile.error)}</p> : null}
            {upsertProfile.isSuccess ? <p className="text-sm text-emerald-700">学习者档案已保存，下一步可以生成学习计划。</p> : null}

            <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-slate-100">
              <button
                className="bg-accent px-6 py-3 text-sm font-bold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={upsertProfile.isPending || formState.preferred_question_types.length === 0}
                type="submit"
              >
                {upsertProfile.isPending ? "保存中..." : "保存档案"}
              </button>
              <Link className="border border-slate-200 bg-white px-6 py-3 text-sm font-bold text-ink hover:bg-slate-50 transition" href="/plans">
                前往计划中心
              </Link>
            </div>
          </form>
        </section>

        <QueryStateCard
          title="当前建档说明"
          empty={false}
          emptyMessage="unused"
        >
          <div className="space-y-4 text-sm text-slate-600">
            <p>第二阶段把 `/profile` 作为真实的 onboarding 入口，计划生成会直接读取这里的目标、时间预算和偏好。</p>
            <p>如果你还没有上传资料，也可以先建档，后续在知识仓库页补资料后再生成计划。</p>
            <div className="border border-slate-200 bg-slate-50 p-5 mt-4">
              <p className="font-bold text-ink">下一步建议</p>
              <p className="mt-2 text-slate-600">
                {profile.data ? "档案已存在，建议先去知识仓库上传资料，再到计划中心生成当前周期计划。" : "先完成建档，再进入知识仓库或计划中心。"}
              </p>
            </div>
          </div>
        </QueryStateCard>
      </div>
    </div>
  );
}
