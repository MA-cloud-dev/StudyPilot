"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { QueryStateCard } from "@/components/query-state-card";
import { getErrorMessage } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";
import { useAssessment, useAssessmentResult, useGenerateAssessment, useSubmitAssessment } from "@/lib/hooks/use-assessments";
import { useCurrentPlan } from "@/lib/hooks/use-current-plan";
import { useCurrentWorkflow, useProceedWorkflow } from "@/lib/hooks/use-current-workflow";

type AssessmentType = components["schemas"]["AssessmentType"];
type Evaluation = components["schemas"]["Evaluation"];
type Question = components["schemas"]["Question"];
type QuestionResult = components["schemas"]["QuestionResult"];
type RubricResult = components["schemas"]["RubricResult"];
type WorkflowStage = components["schemas"]["WorkflowStage"];

const assessmentTypeByStage: Partial<Record<WorkflowStage, AssessmentType>> = {
  checkpoint_test: "checkpoint",
  unit_test: "unit",
  final_test: "final",
};

const stageTitleByStage: Partial<Record<WorkflowStage, string>> = {
  checkpoint_test: "阶段测试",
  unit_review: "阶段复盘",
  unit_test: "单元测试",
  final_review: "总复习",
  final_test: "总测试",
};

const proceedLabelByStage: Partial<Record<WorkflowStage, string>> = {
  unit_review: "进入单元测试",
  final_review: "进入总测试",
};

const PAPER_SUMMARY = "固定卷面：10 道单选题（2 分/题）+ 2 道问答题（5 分/题）";
const PASS_SUMMARY = "通过条件：score_ratio >= 0.8，当前模板等价为 24 / 30。";

function formatPoints(value: number | undefined) {
  return Number.isInteger(value) ? String(value) : (value ?? 0).toFixed(2);
}

function resultTone(result: QuestionResult | undefined, question: Question) {
  if (!result) {
    return "border-slate-200 bg-white";
  }
  if (question.question_type === "single_choice") {
    return result.is_correct ? "border-emerald-300 bg-emerald-50/70" : "border-rose-300 bg-rose-50/70";
  }
  return result.earned_points >= result.max_points ? "border-emerald-300 bg-emerald-50/70" : "border-amber-300 bg-amber-50/70";
}

function optionTone(option: string, answer: string, result: QuestionResult | undefined) {
  if (!result) {
    return answer === option ? "border-accent bg-accent/5 text-slate-900" : "border-slate-200 text-slate-600";
  }
  if (result.correct_answer === option) {
    return "border-emerald-400 bg-emerald-50 text-emerald-900";
  }
  if (result.submitted_answer === option && result.is_correct === false) {
    return "border-rose-400 bg-rose-50 text-rose-900";
  }
  if (result.submitted_answer === option && result.is_correct) {
    return "border-emerald-400 bg-emerald-50 text-emerald-900";
  }
  return "border-slate-200 text-slate-600";
}

function rubricResultByCriterion(rubricResults: RubricResult[] | undefined, criterion: string) {
  return (rubricResults ?? []).find((item) => item.criterion === criterion) ?? null;
}

export default function AssessmentsPage() {
  const router = useRouter();
  const workflow = useCurrentWorkflow();
  const plan = useCurrentPlan();
  const generateAssessment = useGenerateAssessment();
  const submitAssessment = useSubmitAssessment();
  const proceedWorkflow = useProceedWorkflow();
  const autoGenerateRef = useRef<string | null>(null);

  const [localAssessmentId, setLocalAssessmentId] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [uncertainties, setUncertainties] = useState<string[]>([]);
  const [localEvaluation, setLocalEvaluation] = useState<Evaluation | null>(null);

  const currentMicroPlan = plan.data?.current_micro_plan;
  const recentAssessmentId = workflow.data?.recent_assessment_id ?? null;
  const currentStage = workflow.data?.current_stage ?? null;
  const expectedAssessmentType = currentStage ? assessmentTypeByStage[currentStage] ?? null : null;
  const activeAssessmentId = localAssessmentId ?? recentAssessmentId;
  const assessmentQuery = useAssessment(activeAssessmentId);
  const shouldLoadResult = assessmentQuery.data?.status === "evaluated";
  const resultQuery = useAssessmentResult(activeAssessmentId, shouldLoadResult);
  const evaluation = localEvaluation ?? resultQuery.data ?? null;
  const questions = assessmentQuery.data?.questions ?? [];
  const isReviewStage = currentStage === "unit_review" || currentStage === "final_review";
  const reviewTitle = currentStage ? stageTitleByStage[currentStage] : null;

  const questionResultsById = useMemo<Record<string, QuestionResult>>(() => {
    if (!evaluation?.question_results) {
      return {};
    }
    return Object.fromEntries(evaluation.question_results.map((item) => [item.question_id, item]));
  }, [evaluation]);

  useEffect(() => {
    setLocalAssessmentId(null);
    setLocalEvaluation(null);
    setAnswers({});
    setUncertainties([]);
    autoGenerateRef.current = null;
  }, [currentStage]);

  useEffect(() => {
    if (!assessmentQuery.data?.id) {
      return;
    }
    setLocalAssessmentId(assessmentQuery.data.id);
  }, [assessmentQuery.data?.id]);

  useEffect(() => {
    if (questions.length === 0) {
      return;
    }

    setAnswers((current) => {
      const next = { ...current };
      for (const question of questions) {
        if (!(question.id in next)) {
          next[question.id] = "";
        }
      }
      return next;
    });
  }, [questions]);

  useEffect(() => {
    if (!expectedAssessmentType || !currentMicroPlan || workflow.isLoading || generateAssessment.isPending) {
      return;
    }
    if (activeAssessmentId) {
      return;
    }

    const generationKey = `${currentStage}:${expectedAssessmentType}:${currentMicroPlan.id}:${workflow.data?.updated_at ?? ""}`;
    if (autoGenerateRef.current === generationKey) {
      return;
    }

    autoGenerateRef.current = generationKey;
    void generateAssessment.mutateAsync({
      linked_plan_id: currentMicroPlan.id,
      type: expectedAssessmentType,
    });
  }, [
    activeAssessmentId,
    currentMicroPlan,
    currentStage,
    expectedAssessmentType,
    generateAssessment,
    workflow.data?.updated_at,
    workflow.isLoading,
  ]);

  const unresolvedQuestions = useMemo(() => {
    if (questions.length === 0) {
      return [];
    }
    return questions.filter((question) => !answers[question.id] && !uncertainties.includes(question.id));
  }, [answers, questions, uncertainties]);

  const handleGenerateAssessment = async () => {
    if (!currentMicroPlan || !expectedAssessmentType) {
      return;
    }

    const assessment = await generateAssessment.mutateAsync({
      linked_plan_id: currentMicroPlan.id,
      type: expectedAssessmentType,
    });

    setLocalAssessmentId(assessment.id);
    setLocalEvaluation(null);
    setAnswers({});
    setUncertainties([]);
  };

  const handleProceed = async () => {
    await proceedWorkflow.mutateAsync();
  };

  const handleUncertaintyToggle = (questionId: string) => {
    if (evaluation) {
      return;
    }
    setUncertainties((current) =>
      current.includes(questionId) ? current.filter((id) => id !== questionId) : [...current, questionId],
    );
  };

  const handleOptionSelect = (questionId: string, option: string) => {
    if (evaluation) {
      return;
    }
    setAnswers((current) => ({
      ...current,
      [questionId]: option,
    }));
    setUncertainties((current) => current.filter((id) => id !== questionId));
  };

  const handleTextAnswerChange = (questionId: string, value: string) => {
    if (evaluation) {
      return;
    }
    setAnswers((current) => ({
      ...current,
      [questionId]: value,
    }));
    if (value.trim()) {
      setUncertainties((current) => current.filter((id) => id !== questionId));
    }
  };

  const handleSubmitAssessment = async () => {
    if (!activeAssessmentId || questions.length === 0) {
      return;
    }

    const response = await submitAssessment.mutateAsync({
      assessmentId: activeAssessmentId,
      body: {
        answers: questions
          .filter((question) => answers[question.id]?.trim() && !uncertainties.includes(question.id))
          .map((question) => ({
            question_id: question.id,
            answer: answers[question.id].trim(),
          })),
        uncertainties,
      },
    });
    setLocalEvaluation(response.evaluation);
  };

  const handleNextAction = () => {
    if (!evaluation) {
      return;
    }
    if (evaluation.passed && workflow.data?.current_stage === "next_cycle") {
      router.push("/plans");
      return;
    }
    router.push("/workbench");
  };

  const renderQuestion = (question: Question, index: number) => {
    const answer = answers[question.id] ?? "";
    const uncertain = uncertainties.includes(question.id);
    const result = questionResultsById[question.id];
    const displayAnswer = evaluation ? (result?.submitted_answer ?? answer) : answer;
    const cardTone = resultTone(result, question);

    if (question.question_type === "single_choice") {
      return (
        <article className={`rounded-3xl border p-5 shadow-sm ${cardTone}`} key={question.id}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Question {index + 1}</p>
              <h3 className="mt-2 text-lg font-semibold text-slate-900">{question.stem}</h3>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
              {formatPoints(question.points)} 分
            </span>
          </div>
          <div className="mt-4 space-y-3">
            {(question.options ?? []).map((option) => {
              const checked = displayAnswer === option;

              return (
                <label
                  className={[
                    "flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm transition",
                    evaluation ? "cursor-default" : "cursor-pointer",
                    optionTone(option, displayAnswer, result),
                  ].join(" ")}
                  key={option}
                >
                  <input
                    checked={checked}
                    disabled={Boolean(evaluation)}
                    name={question.id}
                    onChange={() => handleOptionSelect(question.id, option)}
                    type="radio"
                  />
                  <span>{option}</span>
                </label>
              );
            })}
          </div>
          {!evaluation ? (
            <label className="mt-4 flex items-center gap-3 text-sm text-slate-600">
              <input checked={uncertain} onChange={() => handleUncertaintyToggle(question.id)} type="checkbox" />
              我不确定这题
            </label>
          ) : null}
          {result ? (
            <div className="mt-4 rounded-2xl border border-slate-200 bg-white/80 p-4 text-sm text-slate-700">
              <p className="font-semibold text-slate-900">
                得分 {formatPoints(result.earned_points)} / {formatPoints(result.max_points)}
              </p>
              {result.correct_answer ? <p className="mt-2">正确答案：{result.correct_answer}</p> : null}
              {result.error_reason ? <p className="mt-2 text-rose-700">错误原因：{result.error_reason}</p> : null}
              {result.explanation ? <p className="mt-2">解释：{result.explanation}</p> : null}
            </div>
          ) : null}
        </article>
      );
    }

    return (
      <article className={`rounded-3xl border p-5 shadow-sm ${cardTone}`} key={question.id}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Question {index + 1}</p>
            <h3 className="mt-2 text-lg font-semibold text-slate-900">{question.stem}</h3>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
            {formatPoints(question.points)} 分
          </span>
        </div>
        <textarea
          className="mt-4 min-h-28 w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-accent disabled:bg-slate-50"
          disabled={Boolean(evaluation)}
          onChange={(event) => handleTextAnswerChange(question.id, event.target.value)}
          placeholder="请输入你的简短回答"
          value={displayAnswer}
        />
        {!evaluation ? (
          <label className="mt-4 flex items-center gap-3 text-sm text-slate-600">
            <input checked={uncertain} onChange={() => handleUncertaintyToggle(question.id)} type="checkbox" />
            我不确定这题
          </label>
        ) : null}
        <div className="mt-4 rounded-2xl border border-slate-200 bg-white/80 p-4 text-sm text-slate-700">
          <p className="font-semibold text-slate-900">评分细则</p>
          <div className="mt-3 space-y-3">
            {(question.rubric ?? []).map((criterion) => {
              const rubricResult = rubricResultByCriterion(result?.rubric_results, criterion.criterion);

              return (
                <div className="rounded-2xl border border-slate-100 bg-slate-50 p-3" key={criterion.criterion}>
                  <p className="font-medium text-slate-900">
                    {criterion.criterion} ({formatPoints(criterion.points)} 分)
                  </p>
                  {criterion.description ? <p className="mt-1 text-slate-600">{criterion.description}</p> : null}
                  {rubricResult ? (
                    <p className="mt-2 text-slate-700">
                      实得 {formatPoints(rubricResult.earned_points)} / {formatPoints(rubricResult.max_points)}：{rubricResult.feedback}
                    </p>
                  ) : null}
                </div>
              );
            })}
          </div>
          {result ? (
            <div className="mt-4 border-t border-slate-200 pt-4">
              <p className="font-semibold text-slate-900">
                得分 {formatPoints(result.earned_points)} / {formatPoints(result.max_points)}
              </p>
              {result.error_reason ? <p className="mt-2 text-amber-700">扣分原因：{result.error_reason}</p> : null}
              {result.explanation ? <p className="mt-2">总体说明：{result.explanation}</p> : null}
            </div>
          ) : null}
        </div>
      </article>
    );
  };

  const currentStageTitle = currentStage ? stageTitleByStage[currentStage] ?? "阶段测试" : "阶段测试";
  const currentAssessmentTitle = expectedAssessmentType
    ? `${currentStageTitle}题目`
    : isReviewStage && reviewTitle
      ? reviewTitle
      : "当前测试";
  const emptyAssessmentMessage = expectedAssessmentType
    ? "当前阶段还没有生成测试，系统会自动生成，或者你也可以手动重试。"
    : isReviewStage
      ? "当前 review 还没有找到对应评分结果。"
      : "当前 workflow 不在阶段测试中。";

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4 rounded-3xl border border-slate-200 bg-white/85 p-6 shadow-sm">
        <div className="space-y-2">
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-accent">Assessments</p>
          <h2 className="text-3xl font-semibold">{currentStageTitle}</h2>
          <p className="max-w-3xl text-sm text-slate-600">{PAPER_SUMMARY}</p>
          <p className="max-w-3xl text-sm text-slate-600">{PASS_SUMMARY}</p>
        </div>
        <div className="flex flex-wrap gap-3">
          {expectedAssessmentType ? (
            <button
              className="rounded-full bg-accent px-5 py-3 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={!currentMicroPlan || generateAssessment.isPending}
              onClick={handleGenerateAssessment}
              type="button"
            >
              {generateAssessment.isPending ? "生成中..." : `重新生成${currentStageTitle}`}
            </button>
          ) : null}
          <Link className="rounded-full border border-slate-200 px-5 py-3 text-sm font-semibold text-slate-700" href="/workbench">
            返回工作台
          </Link>
        </div>
      </header>

      {!currentMicroPlan && !plan.isLoading ? (
        <QueryStateCard title="当前没有测试范围" empty={false} emptyMessage="unused">
          <div className="space-y-4 text-sm text-slate-600">
            <p>只有在当前微观计划存在时才能继续阶段测试或补学。请先在计划中心生成计划并完成一次学习。</p>
            <Link className="inline-flex rounded-full bg-accent px-5 py-3 font-semibold text-white" href="/plans">
              去计划中心
            </Link>
          </div>
        </QueryStateCard>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1.18fr_0.82fr]">
        <QueryStateCard
          title={currentAssessmentTitle}
          loading={workflow.isLoading || assessmentQuery.isLoading || (expectedAssessmentType ? generateAssessment.isPending : false)}
          error={
            workflow.error
              ? getErrorMessage(workflow.error)
              : assessmentQuery.error
                ? getErrorMessage(assessmentQuery.error)
                : generateAssessment.error
                  ? getErrorMessage(generateAssessment.error)
                  : null
          }
          empty={!assessmentQuery.data}
          emptyMessage={emptyAssessmentMessage}
        >
          {assessmentQuery.data ? (
            <div className="space-y-4">
              <div className="rounded-2xl bg-white p-4 text-sm text-slate-600">
                <p className="font-semibold text-slate-900">测试状态</p>
                <p className="mt-2" data-testid="assessment-id">ID: {assessmentQuery.data.id}</p>
                <p>Type: {assessmentQuery.data.type}</p>
                <p>Scope: {assessmentQuery.data.scope}</p>
                <p data-testid="assessment-status">Status: {assessmentQuery.data.status}</p>
                <p>Difficulty: {assessmentQuery.data.difficulty}</p>
              </div>

              {questions.map(renderQuestion)}

              {!evaluation && expectedAssessmentType ? (
                <div className="space-y-3">
                  {submitAssessment.error ? <p className="text-sm text-rose-600">{getErrorMessage(submitAssessment.error)}</p> : null}
                  <button
                    className="rounded-full bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={submitAssessment.isPending || unresolvedQuestions.length > 0}
                    onClick={handleSubmitAssessment}
                    type="button"
                  >
                    {submitAssessment.isPending ? "提交中..." : "提交答案"}
                  </button>
                  {unresolvedQuestions.length > 0 ? (
                    <p className="text-sm text-slate-500">请为每道题填写答案，或显式勾选“我不确定”。</p>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}
        </QueryStateCard>

        <QueryStateCard
          title={isReviewStage && reviewTitle ? reviewTitle : "评分结果"}
          loading={resultQuery.isLoading && shouldLoadResult && !localEvaluation}
          error={
            resultQuery.error
              ? getErrorMessage(resultQuery.error)
              : proceedWorkflow.error
                ? getErrorMessage(proceedWorkflow.error)
                : null
          }
          empty={!evaluation}
          emptyMessage="当前还没有评分结果。提交一次测试答案后，这里会展示逐题反馈、得分和下一步操作。"
        >
          {evaluation ? (
            <div className="space-y-4 text-sm text-slate-700">
              <div className="rounded-3xl bg-white p-5 text-center shadow-sm">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Result</p>
                <p className={`mt-3 text-2xl font-semibold ${evaluation.passed ? "text-emerald-700" : "text-amber-700"}`}>
                  {evaluation.passed ? "通过" : "未通过"}
                </p>
                <p className="mt-4 text-5xl font-semibold text-slate-900">{formatPoints(evaluation.earned_points)}</p>
                <p className="mt-2 text-slate-500">/ {formatPoints(evaluation.total_points)} 分</p>
                <p className="mt-3 text-sm text-slate-600">得分比例：{Math.round((evaluation.score_ratio ?? evaluation.score) * 100)}%</p>
              </div>
              <div className="rounded-2xl bg-white p-4">
                <p className="font-semibold text-slate-900">Feedback</p>
                <p className="mt-2">{evaluation.feedback}</p>
              </div>
              <div className="rounded-2xl bg-white p-4">
                <p className="font-semibold text-slate-900">Recommendations</p>
                <ul className="mt-2 space-y-2">
                  {(evaluation.recommendations ?? []).map((recommendation) => (
                    <li key={recommendation}>{recommendation}</li>
                  ))}
                </ul>
              </div>
              <div className="rounded-2xl bg-white p-4">
                <p className="font-semibold text-slate-900">Workflow</p>
                <p className="mt-2 text-slate-600" data-testid="assessment-workflow-status">
                  {workflow.data ? `${workflow.data.current_stage}: ${workflow.data.next_action}` : "等待 workflow 刷新"}
                </p>
              </div>
              {isReviewStage && currentStage ? (
                <button
                  className="rounded-full bg-accent px-5 py-3 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={proceedWorkflow.isPending}
                  onClick={handleProceed}
                  type="button"
                >
                  {proceedWorkflow.isPending ? "推进中..." : proceedLabelByStage[currentStage]}
                </button>
              ) : null}
              {!isReviewStage ? (
                <button
                  className="rounded-full bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
                  onClick={handleNextAction}
                  type="button"
                >
                  {evaluation.passed
                    ? workflow.data?.current_stage === "next_cycle"
                      ? "开启下一轮计划"
                      : "进入下一次微观学习"
                    : "返回当前微观学习"}
                </button>
              ) : null}
            </div>
          ) : null}
        </QueryStateCard>
      </div>
    </div>
  );
}
