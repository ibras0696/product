import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm, type UseFormRegister } from "react-hook-form";

import { AuthApiError } from "../api/errors";
import { authSchema, type AuthFormValues } from "../model/authSchema";

interface AuthFormProps {
  mode: "login" | "register";
  isPending: boolean;
  error: Error | null;
  onSubmit: (values: AuthFormValues) => void;
}

export function AuthForm({ mode, isPending, error, onSubmit }: AuthFormProps) {
  const [passwordVisible, setPasswordVisible] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AuthFormValues>({ resolver: zodResolver(authSchema) });

  return (
    <form
      className="auth-form"
      onSubmit={(event) => {
        void handleSubmit(onSubmit)(event);
      }}
      noValidate
    >
      <div className="auth-heading">
        <span>Закрытый контур</span>
        <h2 id="auth-dialog-title">{formTitle(mode)}</h2>
        <p>
          Сессия хранится в защищённой HttpOnly cookie и не доступна JavaScript.
        </p>
      </div>
      <label>
        <span>Email</span>
        <input
          type="email"
          required
          autoComplete="email"
          aria-invalid={Boolean(errors.email)}
          aria-describedby={errors.email ? "auth-email-error" : undefined}
          {...register("email")}
        />
        {errors.email ? (
          <small id="auth-email-error" role="alert">
            {errors.email.message}
          </small>
        ) : null}
      </label>
      <PasswordField
        mode={mode}
        visible={passwordVisible}
        errorMessage={errors.password?.message}
        register={register}
        onToggle={() => {
          setPasswordVisible((visible) => !visible);
        }}
      />
      {error ? (
        <p className="auth-error" role="alert">
          {publicError(error)}
        </p>
      ) : null}
      <button className="auth-submit" type="submit" disabled={isPending}>
        {submitLabel(mode, isPending)}
      </button>
    </form>
  );
}

interface PasswordFieldProps {
  mode: "login" | "register";
  visible: boolean;
  errorMessage?: string;
  register: UseFormRegister<AuthFormValues>;
  onToggle: () => void;
}

function PasswordField({
  mode,
  visible,
  errorMessage,
  register,
  onToggle,
}: PasswordFieldProps) {
  return (
    <>
      <label htmlFor="auth-password">
        <span>Пароль</span>
      </label>
      <div className="auth-password-field">
        <input
          id="auth-password"
          type={visible ? "text" : "password"}
          required
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          aria-invalid={Boolean(errorMessage)}
          aria-describedby={errorMessage ? "auth-password-error" : undefined}
          {...register("password")}
        />
        <button type="button" aria-pressed={visible} onClick={onToggle}>
          {visible ? "Скрыть" : "Показать"}
        </button>
      </div>
      {errorMessage ? (
        <small id="auth-password-error" role="alert">
          {errorMessage}
        </small>
      ) : null}
    </>
  );
}

function formTitle(mode: "login" | "register"): string {
  return mode === "login" ? "Войти в Product Lab" : "Создать аккаунт";
}

function submitLabel(mode: "login" | "register", pending: boolean): string {
  if (pending) return "Проверяем…";
  return mode === "login" ? "Войти" : "Зарегистрироваться";
}

function publicError(error: Error): string {
  if (!(error instanceof AuthApiError)) return "Сервис временно недоступен";
  if (error.code === "invalid_credentials") return "Неверный email или пароль";
  if (error.code === "email_already_registered")
    return "Этот email уже зарегистрирован";
  if (error.code === "rate_limited")
    return "Слишком много попыток. Попробуйте позже";
  return error.message;
}
