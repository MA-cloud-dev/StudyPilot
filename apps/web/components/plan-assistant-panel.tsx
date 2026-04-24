"use client";

import Link from "next/link";
import React, { useEffect, useRef, useState, type FormEvent } from "react";

import { getErrorMessage } from "@/lib/api/errors";
import {
  useGeneratePlanFromAssistant,
  usePlanAssistantMessage,
  usePlanAssistantSession,
} from "@/lib/hooks/use-plans";
import type { components } from "@/lib/api/schema";

type PlanAssistantSession = components["schemas"]["PlanAssistantSession"];
type PlanAssistantGenerateResponse = components["schemas"]["PlanAssistantGenerateResponse"];

export function PlanAssistantPanel() {
  const createSession = usePlanAssistantSession();
  const sendMessage = usePlanAssistantMessage();
  const generatePlan = useGeneratePlanFromAssistant();
  const initialized = useRef(false);
  const [session, setSession] = useState<PlanAssistantSession | null>(null);
  const [message, setMessage] = useState("");
  const [generatedPlan, setGeneratedPlan] = useState<PlanAssistantGenerateResponse | null>(null);

  useEffect(() => {
    if (initialized.current) {
      return;
    }

    initialized.current = true;
    void createSession.mutateAsync().then(setSession).catch(() => {
      initialized.current = false;
    });
  }, [createSession]);

  const userTurns =
    (session?.conversation_turns ?? []).filter((turn) => turn.role === "user" && turn.message.trim().length > 0);

  const handleSendMessage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!session || !message.trim()) {
      return;
    }

    const response = await sendMessage.mutateAsync({
      sessionId: session.id,
      message: message.trim(),
    });
    setSession(response.session);
    setMessage("");
  };

  const handleGeneratePlan = async () => {
    if (!session) {
      return;
    }

    const response = await generatePlan.mutateAsync({ sessionId: session.id });
    setSession(response.session);
    setGeneratedPlan(response);
  };

  const combinedError =
    createSession.error || sendMessage.error || generatePlan.error
      ? getErrorMessage(createSession.error || sendMessage.error || generatePlan.error)
      : null;

  return (
    <div className="flex h-full flex-col">
      <div className="py-5 border-b border-slate-200 flex items-center gap-2">
        <span className="text-accent text-lg">✦</span>
        <h3 className="font-semibold text-base">创建新计划 (AI)</h3>
      </div>
      
      <div className="flex-1 overflow-y-auto py-6 flex flex-col gap-5">
        {(session?.conversation_turns ?? []).length ? (
          (session?.conversation_turns ?? []).map((turn, index) => (
            <div
              className={`flex gap-3 max-w-[95%] ${turn.role === 'assistant' ? "self-start" : "self-end flex-row-reverse"}`}
              key={`${turn.created_at}-${index}`}
            >
              <div className={`w-7 h-7 flex items-center justify-center text-xs font-bold shrink-0 ${turn.role === 'assistant' ? "border border-red-300 text-accent bg-red-50" : "bg-slate-200 text-ink border border-slate-300"}`}>
                {turn.role === 'assistant' ? 'AI' : 'Me'}
              </div>
              <div className={`p-3 text-sm leading-relaxed ${turn.role === 'assistant' ? "border border-slate-200 bg-white" : "bg-ink text-white"}`}>
                {turn.message}
              </div>
            </div>
          ))
        ) : (
          <div aria-label="loading" className="space-y-3 p-2">
            <div className="h-4 w-1/2 animate-pulse bg-slate-200" />
            <div className="h-4 w-full animate-pulse bg-slate-200" />
          </div>
        )}

        {generatedPlan ? (
          <div className="border border-slate-200 bg-white p-4 text-sm mt-4">
            <p className="font-medium text-emerald-700 mb-3">计划已创建：{generatedPlan.macro_plan.title}</p>
            <div className="flex gap-2">
              <Link
                className="border border-slate-200 px-3 py-1.5 text-ink hover:bg-slate-50 transition"
                href={`/plans/${generatedPlan.macro_plan.id}`}
              >
                查看详情
              </Link>
              <Link className="bg-accent text-white px-3 py-1.5 hover:bg-red-700 transition" href="/workbench">
                进入工作台
              </Link>
            </div>
          </div>
        ) : null}
      </div>

      <div className="pt-6 border-t border-slate-200">
        <form onSubmit={handleSendMessage} className="space-y-3">
          <div className="flex border border-slate-200 bg-white">
            <input
              type="text"
              className="flex-1 border-none py-3 px-4 text-sm outline-none"
              placeholder="描述学习目标..."
              onChange={(event) => setMessage(event.target.value)}
              value={message}
            />
            <button
              className="w-11 flex items-center justify-center bg-ink text-white border-none cursor-pointer disabled:opacity-50"
              disabled={!session || sendMessage.isPending || !message.trim()}
              type="submit"
            >
               ➤
            </button>
          </div>
          {combinedError && <p className="text-sm text-red-600">{combinedError}</p>}
          <div className="text-right">
            <button
              className="px-4 py-2 text-sm bg-accent text-white hover:bg-red-700 transition disabled:opacity-50"
              disabled={!session || generatePlan.isPending || userTurns.length === 0}
              onClick={handleGeneratePlan}
              type="button"
            >
              {generatePlan.isPending ? "生成中..." : "生成计划"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
