"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient, unwrapApiResponse } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";
import type { components } from "@/lib/api/schema";

type AssessmentGenerateRequest = components["schemas"]["AssessmentGenerateRequest"];
type AssessmentSubmitRequest = components["schemas"]["AssessmentSubmitRequest"];

export function useAssessment(assessmentId: string | null) {
  return useQuery({
    queryKey: assessmentId ? queryKeys.assessment(assessmentId) : ["assessments", "idle"],
    enabled: Boolean(assessmentId),
    queryFn: async () => {
      const result = await apiClient.GET("/api/assessments/{assessment_id}", {
        params: {
          path: {
            assessment_id: assessmentId as string,
          },
        },
      });
      return unwrapApiResponse(result, "Failed to fetch assessment");
    },
  });
}

export function useAssessmentResult(assessmentId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: assessmentId ? queryKeys.assessmentResult(assessmentId) : ["assessments", "result", "idle"],
    enabled: Boolean(assessmentId) && enabled,
    queryFn: async () => {
      const result = await apiClient.GET("/api/assessments/{assessment_id}/result", {
        params: {
          path: {
            assessment_id: assessmentId as string,
          },
        },
      });
      return unwrapApiResponse(result, "Failed to fetch assessment result");
    },
  });
}

export function useGenerateAssessment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: AssessmentGenerateRequest) => {
      const result = await apiClient.POST("/api/assessments/generate", {
        body: payload,
      });
      return unwrapApiResponse(result, "Failed to generate assessment");
    },
    onSuccess: async (assessment) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.workflowCurrent }),
        queryClient.invalidateQueries({ queryKey: queryKeys.assessment(assessment.id) }),
      ]);
    },
  });
}

export function useSubmitAssessment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: { assessmentId: string; body: AssessmentSubmitRequest }) => {
      const result = await apiClient.POST("/api/assessments/{assessment_id}/submit", {
        params: {
          path: {
            assessment_id: payload.assessmentId,
          },
        },
        body: payload.body,
      });
      return unwrapApiResponse(result, "Failed to submit assessment");
    },
    onSuccess: async (_, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.workflowCurrent }),
        queryClient.invalidateQueries({ queryKey: queryKeys.currentPlan }),
        queryClient.invalidateQueries({ queryKey: queryKeys.assessment(variables.assessmentId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.assessmentResult(variables.assessmentId) }),
      ]);
    },
  });
}
