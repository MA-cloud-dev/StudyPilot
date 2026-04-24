"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient, unwrapApiResponse } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";
import type { components } from "@/lib/api/schema";

type UserProfileCreate = components["schemas"]["UserProfileCreate"];

export function useProfile() {
  return useQuery({
    queryKey: queryKeys.profile,
    queryFn: async () => {
      const result = await apiClient.GET("/api/profile");
      if (result.error && result.response.status === 404) {
        return null;
      }
      return unwrapApiResponse(result, "Failed to fetch learner profile");
    },
  });
}

export function useUpsertProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: UserProfileCreate) => {
      const result = await apiClient.POST("/api/profile", {
        body: payload,
      });
      return unwrapApiResponse(result, "Failed to save learner profile");
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.profile }),
        queryClient.invalidateQueries({ queryKey: queryKeys.workflowCurrent }),
      ]);
    },
  });
}
