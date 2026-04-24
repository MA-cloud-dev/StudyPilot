import type { components } from "./schema";

type ErrorResponse = components["schemas"]["ErrorResponse"];

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: Record<string, unknown>;

  constructor(message: string, options: { status: number; code?: string; details?: Record<string, unknown> }) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code;
    this.details = options.details;
  }
}

export function buildApiError(
  status: number,
  payload: ErrorResponse | undefined,
  fallbackMessage: string,
): ApiError {
  return new ApiError(payload?.message ?? fallbackMessage, {
    status,
    code: payload?.code,
    details: payload?.details,
  });
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.code ? `${error.code}: ${error.message}` : error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unexpected error";
}
