export const queryKeys = {
  profile: ["profile"] as const,
  workflowCurrent: ["workflow", "current"] as const,
  currentPlan: ["plans", "current"] as const,
  plans: ["plans"] as const,
  planDetail: (planId: string) => ["plans", planId] as const,
  planAssistantSession: (sessionId: string) => ["plans", "assistant", sessionId] as const,
  knowledgeAssets: ["knowledge", "assets"] as const,
  assessment: (assessmentId: string) => ["assessments", assessmentId] as const,
  assessmentResult: (assessmentId: string) => ["assessments", assessmentId, "result"] as const,
};
