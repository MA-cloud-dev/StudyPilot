"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient, unwrapApiResponse, uploadAssets } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";

export function useKnowledgeAssets() {
  return useQuery({
    queryKey: queryKeys.knowledgeAssets,
    queryFn: async () => {
      const result = await apiClient.GET("/api/knowledge/assets");
      return unwrapApiResponse(result, "Failed to fetch knowledge assets");
    },
  });
}

export function useUploadKnowledgeAssets() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: uploadAssets,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.knowledgeAssets });
    },
  });
}

export function useDeleteKnowledgeAsset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (assetId: string) => {
      const result = await apiClient.DELETE("/api/knowledge/assets/{asset_id}", {
        params: {
          path: {
            asset_id: assetId,
          },
        },
      });
      return unwrapApiResponse(result, "Failed to delete knowledge asset");
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.knowledgeAssets });
    },
  });
}

export function useRetryKnowledgeAsset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (assetId: string) => {
      const result = await apiClient.POST("/api/knowledge/assets/{asset_id}/retry", {
        params: {
          path: {
            asset_id: assetId,
          },
        },
      });
      return unwrapApiResponse(result, "Failed to retry knowledge asset");
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.knowledgeAssets });
    },
  });
}
