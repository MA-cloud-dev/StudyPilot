import { describe, expect, it } from "vitest";

import { ApiError, buildApiError, getErrorMessage } from "./errors";

describe("api errors", () => {
  it("builds an ApiError from structured payloads", () => {
    const error = buildApiError(
      404,
      {
        code: "PROFILE_NOT_FOUND",
        message: "Learner profile has not been created yet.",
        details: {},
      },
      "fallback",
    );

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(404);
    expect(error.code).toBe("PROFILE_NOT_FOUND");
  });

  it("formats api error messages with their codes", () => {
    const error = new ApiError("Learner profile has not been created yet.", {
      status: 404,
      code: "PROFILE_NOT_FOUND",
    });

    expect(getErrorMessage(error)).toBe("PROFILE_NOT_FOUND: Learner profile has not been created yet.");
  });
});
