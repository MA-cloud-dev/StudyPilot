"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { QueryStateCard } from "@/components/query-state-card";
import { getErrorMessage } from "@/lib/api/errors";
import { useCurrentPlan } from "@/lib/hooks/use-current-plan";
import {
  useCompleteLearningSession,
  useSendLearningMessage,
  useStartLearningSession,
} from "@/lib/hooks/use-learning-session";
import { useCurrentWorkflow } from "@/lib/hooks/use-current-workflow";
import type { components } from "@/lib/api/schema";

type ConversationTurn = components["schemas"]["ConversationTurn"];
type LearningSession = components["schemas"]["LearningSession"];

export default function WorkbenchPage() {
  const workflow = useCurrentWorkflow();
  const plan = useCurrentPlan();
  const startSession = useStartLearningSession();
  const sendMessage = useSendLearningMessage();
  const completeSession = useCompleteLearningSession();
  const [session, setSession] = useState<LearningSession | null>(null);
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [message, setMessage] = useState("");
  const [sessionSummary, setSessionSummary] = useState("");
  const [masterySignals, setMasterySignals] = useState<string[]>([]);
  const [sessionCompleted, setSessionCompleted] = useState(false);

  const microPlan = plan.data?.current_micro_plan;

  const handleStartSession = async () => {
    if (!microPlan) {
      return;
    }

    const nextSession = await startSession.mutateAsync({
      micro_plan_id: microPlan.id,
    });
    setSession(nextSession);
    setTurns(nextSession.conversation_turns ?? []);
    setSessionSummary(nextSession.session_summary);
    setMasterySignals(nextSession.mastery_signals ?? []);
    setSessionCompleted(false);
  };

  const handleSendMessage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!session || !message.trim()) {
      return;
    }

    const nextMessage = message.trim();
    const now = new Date().toISOString();
    const optimisticTurn: ConversationTurn = {
      role: "user",
      message: nextMessage,
      created_at: now,
    };

    setTurns((current) => [...current, optimisticTurn]);
    setMessage("");

    try {
      const reply = await sendMessage.mutateAsync({
        session_id: session.id,
        message: nextMessage,
      });
      setTurns((current) => [
        ...current,
        {
          role: "assistant",
          message: reply.reply,
          created_at: new Date().toISOString(),
        },
      ]);
      setSessionSummary(reply.session_summary);
      setMasterySignals(reply.mastery_signals ?? []);
    } catch (error) {
      setTurns((current) => current.filter((turn) => turn !== optimisticTurn));
      setMessage(nextMessage);
    }
  };

  const handleCompleteSession = async () => {
    if (!session) {
      return;
    }

    await completeSession.mutateAsync({
      session_id: session.id,
      completion_signals: ["learner_confirmed", "phase3_workbench_complete"],
    });
    setSessionCompleted(true);
  };

  const topics = microPlan?.topics ?? [];
  const tasks = microPlan?.tasks ?? [];
  const completionCriteria = microPlan?.completion_criteria ?? [];

  return (
    <div className="flex h-full min-h-0 flex-col gap-8 lg:min-h-[calc(100vh-3rem)]">
      <header className="border-b border-slate-200 pb-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-4">
            <p className="text-sm font-semibold uppercase tracking-[0.25em] text-accent">Workbench</p>
            <h2 className="text-[2.8rem] font-bold leading-none tracking-tight text-ink">学习工作台</h2>
            <p className="max-w-4xl text-sm leading-relaxed text-slate-600">
              当前阶段由后端 `workflow` 决定。完成本次微观学习后，必须通过阶段测试，才能开启下一次微观学习。
            </p>
          </div>
          {microPlan ? (
            <div className="border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600">
              预计 {microPlan.estimated_duration} 分钟
            </div>
          ) : null}
        </div>

        <div className="mt-8 border border-slate-200 bg-slate-50 px-6 py-5 text-sm text-slate-700">
          {workflow.data ? (
            <div className="space-y-2">
              <p className="font-bold text-ink">阶段: {workflow.data.current_stage}</p>
              <p className="leading-6 text-slate-600">{workflow.data.next_action}</p>
            </div>
          ) : (
            <p>加载工作流状态中...</p>
          )}
        </div>
      </header>

      {!microPlan && !plan.isLoading ? (
        <QueryStateCard
          title="当前没有可学习的微观计划"
          empty={false}
          emptyMessage="unused"
        >
          <div className="space-y-4 text-sm text-slate-600">
            <p>请先在计划中心生成当前周期计划，工作台才会拿到真实的学习任务。</p>
            <Link className="inline-flex bg-accent px-6 py-3 font-bold text-white transition hover:bg-red-700" href="/plans">
              去生成计划
            </Link>
          </div>
        </QueryStateCard>
      ) : null}

      <div className="grid min-h-0 flex-1 gap-8 xl:grid-cols-[minmax(0,1.38fr)_420px]">
        <QueryStateCard
          title="当前学习内容"
          loading={plan.isLoading}
          error={plan.error ? getErrorMessage(plan.error) : null}
          empty={!microPlan}
          emptyMessage="当前没有微观计划，无法启动学习会话。"
          className="min-h-0"
          bodyClassName="flex h-full min-h-0 flex-col"
        >
          {microPlan ? (
            <div className="flex h-full min-h-0 flex-col gap-6 text-sm text-slate-700">
              <div className="border border-slate-200 bg-white px-6 py-6 transition hover:border-ink">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="max-w-3xl">
                    <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-400">当前学习内容</p>
                    <p className="mt-3 text-[2rem] font-bold leading-tight text-ink">{microPlan.title}</p>
                    <p className="mt-4 leading-relaxed text-slate-600">
                      当前工作流会围绕这份微观计划生成学习内容和 checkpoint 测试。
                    </p>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 px-4 py-3 text-sm text-slate-600">
                    <p>预计 {microPlan.estimated_duration} 分钟</p>
                    <p className="mt-1 font-bold">{microPlan.status}</p>
                  </div>
                </div>

                <div className="mt-8 space-y-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ink">Topics</p>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {topics.map((topic) => (
                      <span className="border border-slate-200 bg-slate-50 px-4 py-2 font-medium" key={topic}>
                        {topic}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="mt-8 flex flex-wrap gap-3 pt-6 border-t border-slate-100">
                  <button
                    className="bg-accent px-6 py-3 text-sm font-bold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={startSession.isPending || !microPlan}
                    onClick={handleStartSession}
                    type="button"
                  >
                    {startSession.isPending ? "启动中..." : session ? "重新开始本次学习" : "启动学习会话"}
                  </button>
                  <button
                    className="border border-slate-200 bg-white px-6 py-3 text-sm font-bold text-ink transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={!session || completeSession.isPending || sessionCompleted}
                    onClick={handleCompleteSession}
                    type="button"
                  >
                    {completeSession.isPending ? "提交完成中..." : sessionCompleted ? "已完成本次学习" : "完成学习并进入阶段测试"}
                  </button>
                  <Link className="border border-slate-200 bg-white px-6 py-3 text-sm font-bold text-ink transition hover:bg-slate-50" href="/assessments">
                    前往测试页
                  </Link>
                </div>
                {startSession.error ? <p className="mt-4 text-sm text-red-600">{getErrorMessage(startSession.error)}</p> : null}
                {completeSession.error ? <p className="mt-4 text-sm text-red-600">{getErrorMessage(completeSession.error)}</p> : null}
                {sessionCompleted ? (
                  <p className="mt-4 text-sm font-bold text-emerald-700" data-testid="workbench-session-complete">
                    学习完成信号已提交，测试页现在可以生成阶段测试，测试通过后才能开启下一次微观学习。
                  </p>
                ) : null}
              </div>

              <div className="grid min-h-0 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                <section className="border border-slate-200 bg-white px-6 py-6 transition hover:border-ink">
                  <div className="flex items-center justify-between gap-4 border-b border-slate-100 pb-4 mb-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink">Tasks</p>
                    <span className="text-sm font-bold text-slate-500">{tasks.length} 项</span>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1 2xl:grid-cols-2">
                    {tasks.map((task, index) => (
                      <article className="border border-slate-100 bg-slate-50 px-4 py-4" key={`${microPlan.id}-task-${index}`}>
                        <p className="font-bold text-ink">{String(task.title ?? `Task ${index + 1}`)}</p>
                        <p className="mt-2 text-slate-500">{String(task.status ?? "pending")}</p>
                      </article>
                    ))}
                  </div>
                </section>

                <section className="border border-slate-200 bg-white px-6 py-6 transition hover:border-ink">
                  <div className="flex items-center justify-between gap-4 border-b border-slate-100 pb-4 mb-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ink">Completion Criteria</p>
                    <span className="text-sm font-bold text-slate-500">{completionCriteria.length} 条</span>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1 2xl:grid-cols-2">
                    {completionCriteria.map((criterion) => (
                      <article className="border border-slate-100 bg-slate-50 px-4 py-4 leading-relaxed" key={criterion}>
                        {criterion}
                      </article>
                    ))}
                  </div>
                </section>
              </div>
            </div>
          ) : null}
        </QueryStateCard>

        <QueryStateCard
          title="学习助手对话"
          action={session ? <span className="text-sm font-bold text-slate-500">session ready</span> : null}
          empty={!session}
          emptyMessage="先启动学习会话，再向学习助手发送一轮问题。"
          className="flex min-h-0 flex-col"
          bodyClassName="flex min-h-0 flex-1 flex-col"
        >
          {session ? (
            <div className="flex min-h-0 flex-1 flex-col gap-6">
              <div className="border border-slate-200 bg-white px-5 py-5 text-sm text-slate-600 transition hover:border-ink">
                <p className="font-bold text-ink">当前摘要</p>
                <p className="mt-3 leading-relaxed">{sessionSummary}</p>
                {masterySignals.length > 0 ? (
                  <div className="mt-4 flex flex-wrap gap-2 pt-4 border-t border-slate-100">
                    {masterySignals.map((signal) => (
                      <span className="bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600" key={signal}>
                        {signal}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>

              <div className="min-h-[320px] flex-1 space-y-4 overflow-y-auto border border-slate-200 bg-white p-5 transition hover:border-ink">
                {turns.map((turn, index) => (
                  <div
                    className={[
                      "max-w-[85%] px-5 py-4 text-sm leading-relaxed",
                      turn.role === "assistant" ? "border border-slate-200 bg-slate-50 text-slate-700" : "ml-auto border border-ink bg-ink text-white",
                    ].join(" ")}
                    key={`${turn.created_at}-${index}`}
                  >
                    {turn.message}
                  </div>
                ))}
              </div>

              <form className="space-y-4" onSubmit={handleSendMessage}>
                <textarea
                  className="min-h-28 w-full border border-slate-200 bg-white px-5 py-4 text-sm outline-none transition focus:border-ink"
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder="例如：请用更通俗的方式解释这个主题。"
                  value={message}
                />
                {sendMessage.error ? <p className="text-sm text-red-600">{getErrorMessage(sendMessage.error)}</p> : null}
                <button
                  className="w-full bg-ink px-5 py-4 text-sm font-bold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={sendMessage.isPending || !message.trim()}
                  type="submit"
                >
                  {sendMessage.isPending ? "发送中..." : "发送问题"}
                </button>
              </form>
            </div>
          ) : null}
        </QueryStateCard>
      </div>
    </div>
  );
}
