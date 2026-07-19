import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import type { ModerationDecisionInput } from "../domain/types";

const decisionSchema = z.object({
  comment: z.string().trim().min(1, "Комментарий обязателен"),
});

type DecisionValues = z.infer<typeof decisionSchema>;

interface Props {
  mode: "revision" | "reject";
  expectedVersion: number;
  pending: boolean;
  errorMessage: string | null;
  onDecision: (input: ModerationDecisionInput) => Promise<unknown>;
}

export function DecisionForm({
  mode,
  expectedVersion,
  pending,
  errorMessage,
  onDecision,
}: Props) {
  const form = useForm<DecisionValues>({
    resolver: zodResolver(decisionSchema),
    defaultValues: { comment: "" },
  });
  const isRevision = mode === "revision";
  const title = isRevision ? "Запросить исправления" : "Отклонить заявку";

  async function submit(values: DecisionValues) {
    if (
      mode === "reject" &&
      !window.confirm("Отклонить заявку? Это решение увидит автор.")
    )
      return;
    try {
      await onDecision({ expectedVersion, comment: values.comment });
      form.reset();
    } catch {
      // Mutation exposes a typed visible error; input intentionally stays intact.
    }
  }

  return (
    <form
      className="mod-decision-form"
      onSubmit={(event) => void form.handleSubmit(submit)(event)}
      noValidate
    >
      <h3>{title}</h3>
      <label>
        <span>Комментарий для автора</span>
        <textarea
          rows={4}
          aria-invalid={Boolean(form.formState.errors.comment)}
          {...form.register("comment")}
        />
        <small role="alert">{form.formState.errors.comment?.message}</small>
      </label>
      {errorMessage ? <p role="alert">{errorMessage}</p> : null}
      <button
        type="submit"
        disabled={pending}
        className={isRevision ? "" : "mod-danger"}
      >
        {pending ? "Сохраняем…" : title}
      </button>
    </form>
  );
}
