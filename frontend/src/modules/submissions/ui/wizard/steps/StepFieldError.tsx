import type { FieldError } from "react-hook-form";

export function StepFieldError({
  id,
  error,
}: {
  id: string;
  error?: FieldError;
}) {
  if (!error?.message) return null;
  return (
    <span className="submission-field-error" id={id} role="alert">
      {error.message}
    </span>
  );
}
