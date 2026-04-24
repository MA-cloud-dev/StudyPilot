"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiBaseUrl, apiClient, unwrapApiResponse } from "@/lib/api/client";
import { buildApiError } from "@/lib/api/errors";
import { queryKeys } from "@/lib/api/query-keys";
import type { components } from "@/lib/api/schema";

type PlanAssistantMessageRequest = components["schemas"]["PlanAssistantMessageRequest"];

export function usePlans() {
  return useQuery({
    queryKey: queryKeys.plans,
    queryFn: async () => {
      const result = await apiClient.GET("/api/plans");
      return unwrapApiResponse(result, "Failed to fetch plans");
    },
  });
}

export function usePlanDetail(planId: string) {
  return useQuery({
    queryKey: queryKeys.planDetail(planId),
    queryFn: async () => {
      const result = await apiClient.GET("/api/plans/{plan_id}", {
        params: { path: { plan_id: planId } },
      });
      return unwrapApiResponse(result, "Failed to fetch plan detail");
    },
    enabled: Boolean(planId),
  });
}

export function usePlanAssistantSession() {
  return useMutation({
    mutationFn: async () => {
      const result = await apiClient.POST("/api/plans/assistant/sessions", {});
      return unwrapApiResponse(result, "Failed to create plan assistant session");
    },
  });
}

export function usePlanAssistantMessage() {
  return useMutation({
    mutationFn: async ({ sessionId, message }: { sessionId: string; message: PlanAssistantMessageRequest["message"] }) => {
      const result = await apiClient.POST("/api/plans/assistant/sessions/{session_id}/messages", {
        params: { path: { session_id: sessionId } },
        body: { message },
      });
      return unwrapApiResponse(result, "Failed to send plan assistant message");
    },
  });
}

export function useGeneratePlanFromAssistant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ sessionId }: { sessionId: string }) => {
      const result = await apiClient.POST("/api/plans/assistant/sessions/{session_id}/generate", {
        params: { path: { session_id: sessionId } },
      });
      return unwrapApiResponse(result, "Failed to generate plan from assistant session");
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.plans }),
        queryClient.invalidateQueries({ queryKey: queryKeys.currentPlan }),
        queryClient.invalidateQueries({ queryKey: queryKeys.workflowCurrent }),
      ]);
    },
  });
}

export function useActivatePlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ planId }: { planId: string }) => {
      const response = await fetch(`${apiBaseUrl}/api/plans/${planId}/activate`, {
        method: "POST",
      });
      const data = await response.json();
      if (!response.ok) {
        throw buildApiError(response.status, data, "Failed to activate plan");
      }
      return data;
    },
    onSuccess: async (_, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.plans }),
        queryClient.invalidateQueries({ queryKey: queryKeys.currentPlan }),
        queryClient.invalidateQueries({ queryKey: queryKeys.workflowCurrent }),
        queryClient.invalidateQueries({ queryKey: queryKeys.planDetail(variables.planId) }),
      ]);
    },
  });
}

export function useDeletePlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ planId }: { planId: string }) => {
      const response = await fetch(`${apiBaseUrl}/api/plans/${planId}`, {
        method: "DELETE",
      });
      const data = await response.json();
      if (!response.ok) {
        throw buildApiError(response.status, data, "Failed to delete plan");
      }
      return data;
    },
    onSuccess: async (_, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.plans }),
        queryClient.invalidateQueries({ queryKey: queryKeys.currentPlan }),
        queryClient.invalidateQueries({ queryKey: queryKeys.workflowCurrent }),
        queryClient.removeQueries({ queryKey: queryKeys.planDetail(variables.planId) }),
      ]);
    },
  });
}
