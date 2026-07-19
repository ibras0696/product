import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, vi } from "vitest";

import { mockModerationSubmissions } from "../api/mockSeeds";
import type {
  ModerationSubmission,
  ModerationSubmissionType,
  PublishCommand,
} from "../domain/types";
import { PublishSubmissionForm } from "./PublishSubmissionForm";

const relatedId = "10000000-0000-4000-8000-000000000001";

function submission(type: ModerationSubmissionType): ModerationSubmission {
  const fixture = mockModerationSubmissions.find(
    (item) => item.status === "in_review",
  );
  if (!fixture) throw new Error("Missing moderation fixture");
  return { ...fixture, type, relatedEntityId: relatedId };
}

function renderForm(type: ModerationSubmissionType) {
  const onPublish = vi.fn<(input: PublishCommand) => Promise<unknown>>();
  onPublish.mockResolvedValue({});
  render(
    <PublishSubmissionForm
      submission={submission(type)}
      pending={false}
      errorMessage={null}
      onPublish={onPublish}
    />,
  );
  return onPublish;
}

afterEach(() => {
  vi.restoreAllMocks();
});

it("submits update_entity with the related UUID and a stable per-submission key", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const user = userEvent.setup();
  const publish = renderForm("update_entity");
  const button = screen.getByRole("button", {
    name: "Опубликовать обновление",
  });

  await user.click(button);
  await user.click(button);

  expect(publish).toHaveBeenCalledTimes(2);
  const first = publish.mock.calls[0][0];
  const second = publish.mock.calls[1][0];
  expect(first.action).toBe("update_entity");
  expect(first.idempotencyKey).toBe(second.idempotencyKey);
  if (first.action !== "update_entity") throw new Error("Unexpected action");
  expect(first.payload.entityId).toBe(relatedId);
});

it("submits create_relation only after both explicit entity UUIDs are valid", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const user = userEvent.setup();
  const publish = renderForm("new_relation");
  await user.type(
    screen.getByLabelText("UUID целевой сущности"),
    "10000000-0000-4000-8000-000000000002",
  );
  await user.click(screen.getByRole("button", { name: "Опубликовать связь" }));

  const command = publish.mock.calls[0][0];
  expect(command.action).toBe("create_relation");
  if (command.action !== "create_relation")
    throw new Error("Unexpected action");
  expect(command.payload.relation).toMatchObject({
    sourceEntityId: relatedId,
    targetEntityId: "10000000-0000-4000-8000-000000000002",
  });
});

it("submits add_source with an editable related target", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const user = userEvent.setup();
  const publish = renderForm("new_source");
  await user.click(screen.getByRole("button", { name: "Добавить источник" }));

  const command = publish.mock.calls[0][0];
  expect(command.action).toBe("add_source");
  if (command.action !== "add_source") throw new Error("Unexpected action");
  expect(command.payload.targetId).toBe(relatedId);
});

it("publishes only checked attached media UUIDs", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const user = userEvent.setup();
  const publish = renderForm("new_media");
  await user.click(
    screen.getByRole("checkbox", { name: "Первый выпуск школы" }),
  );
  await user.click(
    screen.getByRole("button", { name: "Опубликовать фотографии" }),
  );

  const command = publish.mock.calls[0][0];
  expect(command.action).toBe("publish_media");
  if (command.action !== "publish_media") throw new Error("Unexpected action");
  expect(command.payload).toEqual({
    targetEntityId: relatedId,
    approvedMediaIds: ["51000000-0000-4000-8000-000000000002"],
  });
});

it("submits resolve_report archive mode without inventing an entity patch", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const user = userEvent.setup();
  const publish = renderForm("report_error");
  await user.click(screen.getByLabelText("Архивировать сущность"));
  await user.click(screen.getByRole("button", { name: "Завершить проверку" }));

  const command = publish.mock.calls[0][0];
  expect(command.action).toBe("resolve_report");
  if (command.action !== "resolve_report") throw new Error("Unexpected action");
  expect(command.payload).toMatchObject({ archiveEntityId: relatedId });
  expect(command.payload.entityPatch).toBeUndefined();
});
