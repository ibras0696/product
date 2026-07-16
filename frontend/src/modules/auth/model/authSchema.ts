import { z } from "zod";

export const authSchema = z.object({
  email: z.email("Введите корректный email"),
  password: z
    .string()
    .min(12, "Минимум 12 символов")
    .max(128, "Максимум 128 символов"),
});

export type AuthFormValues = z.infer<typeof authSchema>;
