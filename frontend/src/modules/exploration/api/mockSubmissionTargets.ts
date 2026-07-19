import { mapEntities } from "../model/entities";

export interface MockSubmissionTargetOption {
  id: string;
  title: string;
}

export const mockSubmissionTargets: MockSubmissionTargetOption[] =
  mapEntities.map(({ id, name }) => ({ id, title: name }));

export const mockSubmissionSettlements: MockSubmissionTargetOption[] =
  mapEntities
    .filter(({ kind }) => kind === "place")
    .map(({ id, name }) => ({ id, title: name }));
