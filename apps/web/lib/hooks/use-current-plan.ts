"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient, unwrapApiResponse } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";
import type { components } from "@/lib/api/schema";

type PlanGenerateRequest = components["schemas"]["PlanGenerateRequest"];

export function useCurrentPlan() {
  return useQuery({
    queryKey: queryKeys.currentPlan,
    queryFn: async () => {
      const result = await apiClient.GET("/api/plans/current");
      return unwrapApiResponse(result, "Failed to fetch current plan");
    },
  });
}

export function useGeneratePlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: PlanGenerateRequest) => {
      const result = await apiClient.POST("/api/plans/generate", {
        body: payload,
      });
      return unwrapApiResponse(result, "Failed to generate plan");
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.currentPlan }),
        queryClient.invalidateQueries({ queryKey: queryKeys.workflowCurrent }),
      ]);
    },
  });
}
