"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient, unwrapApiResponse } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";

export function useCurrentWorkflow() {
  return useQuery({
    queryKey: queryKeys.workflowCurrent,
    queryFn: async () => {
      const result = await apiClient.GET("/api/workflow/current");
      return unwrapApiResponse(result, "Failed to fetch workflow");
    },
  });
}

export function useProceedWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const result = await apiClient.POST("/api/workflow/proceed", {});
      return unwrapApiResponse(result, "Failed to proceed workflow");
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.workflowCurrent }),
        queryClient.invalidateQueries({ queryKey: queryKeys.currentPlan }),
      ]);
    },
  });
}
