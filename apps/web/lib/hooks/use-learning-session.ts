"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiClient, unwrapApiResponse } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";
import type { components } from "@/lib/api/schema";

type LearningSessionCompleteRequest = components["schemas"]["LearningSessionCompleteRequest"];
type LearningSessionMessageRequest = components["schemas"]["LearningSessionMessageRequest"];
type LearningSessionStartRequest = components["schemas"]["LearningSessionStartRequest"];

export function useStartLearningSession() {
  return useMutation({
    mutationFn: async (payload: LearningSessionStartRequest) => {
      const result = await apiClient.POST("/api/learning/session/start", {
        body: payload,
      });
      return unwrapApiResponse(result, "Failed to start learning session");
    },
  });
}

export function useSendLearningMessage() {
  return useMutation({
    mutationFn: async (payload: LearningSessionMessageRequest) => {
      const result = await apiClient.POST("/api/learning/session/message", {
        body: payload,
      });
      return unwrapApiResponse(result, "Failed to send learning message");
    },
  });
}

export function useCompleteLearningSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: LearningSessionCompleteRequest) => {
      const result = await apiClient.POST("/api/learning/session/complete", {
        body: payload,
      });
      return unwrapApiResponse(result, "Failed to complete learning session");
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.workflowCurrent });
    },
  });
}
