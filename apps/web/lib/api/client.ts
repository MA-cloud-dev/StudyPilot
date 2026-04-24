import createClient from "openapi-fetch";

import { buildApiError } from "./errors";
import type { paths } from "./schema";

export const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const apiClient = createClient<paths>({
  baseUrl: apiBaseUrl,
});

type ApiResult<TData> = {
  data?: TData;
  error?: unknown;
  response: Response;
};

export function unwrapApiResponse<TData>(result: ApiResult<TData>, fallbackMessage: string): TData {
  if (result.error) {
    throw buildApiError(result.response.status, result.error as never, fallbackMessage);
  }
  if (result.data === undefined) {
    throw buildApiError(result.response.status, undefined, fallbackMessage);
  }
  return result.data;
}

export async function uploadAssets(formData: FormData) {
  const response = await fetch(`${apiBaseUrl}/api/knowledge/assets`, {
    method: "POST",
    body: formData,
  });
  const data = await response.json();

  if (!response.ok) {
    throw buildApiError(response.status, data, "Failed to upload knowledge assets");
  }

  return data;
}
