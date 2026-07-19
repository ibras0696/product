import type { ResearchStatus } from "../api/viewModels";

export const researchStatusLabels: Record<ResearchStatus, string> = {
  verified: "Проверено",
  needs_review: "Требует проверки",
};
