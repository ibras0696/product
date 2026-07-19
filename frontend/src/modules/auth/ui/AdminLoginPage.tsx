import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, type UseFormReturn } from "react-hook-form";
import { useNavigate, useSearchParams } from "react-router-dom";
import { z } from "zod";

import { AuthApiError } from "../api/errors";
import { safeAdminReturnPath, useAdminLogin } from "../model/adminSession";
import "./admin.css";

const adminLoginSchema = z.object({
  email: z.email("Введите корректный email"),
  password: z.string().min(12, "Минимум 12 символов"),
});

type AdminLoginValues = z.infer<typeof adminLoginSchema>;

export function AdminLoginPage() {
  const login = useAdminLogin();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const form = useForm<AdminLoginValues>({
    resolver: zodResolver(adminLoginSchema),
    defaultValues: { email: "", password: "" },
  });

  function submit(values: AdminLoginValues) {
    login.mutate(values, {
      onSuccess: () => {
        void navigate(safeAdminReturnPath(params.get("returnTo")), {
          replace: true,
        });
      },
      onError: () => {
        form.resetField("password");
        form.setFocus("password");
      },
    });
  }

  return (
    <main className="admin-login-page">
      <div className="admin-login-layout">
        <a className="admin-back-link" href="/">
          ← Вернуться к карте
        </a>
        <section
          className="admin-login-card"
          aria-labelledby="admin-login-title"
        >
          <header className="admin-login-header">
            <p>Паутина истории Чечни</p>
            <h1 id="admin-login-title">Вход в редакцию</h1>
            <span>Для редакторов, модераторов и администраторов проекта.</span>
          </header>
          <form
            onSubmit={(event) => void form.handleSubmit(submit)(event)}
            noValidate
            aria-busy={login.isPending}
          >
            <AdminLoginFields form={form} />
            {login.error ? (
              <p className="admin-login-error" role="alert">
                {adminLoginError(login.error)}
              </p>
            ) : null}
            <button type="submit" disabled={login.isPending}>
              {login.isPending ? "Проверяем…" : "Войти"}
            </button>
          </form>
        </section>
      </div>
    </main>
  );
}

function AdminLoginFields({ form }: { form: UseFormReturn<AdminLoginValues> }) {
  const { errors } = form.formState;
  return (
    <>
      <label>
        <span>Электронная почта</span>
        <input
          id="admin-email"
          type="email"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          aria-invalid={Boolean(errors.email)}
          aria-describedby={errors.email ? "admin-email-error" : undefined}
          {...form.register("email")}
        />
        {errors.email ? (
          <small id="admin-email-error" role="alert">
            {errors.email.message}
          </small>
        ) : null}
      </label>
      <label>
        <span>Пароль</span>
        <input
          id="admin-password"
          type="password"
          autoComplete="current-password"
          aria-invalid={Boolean(errors.password)}
          aria-describedby={
            errors.password ? "admin-password-error" : undefined
          }
          {...form.register("password")}
        />
        {errors.password ? (
          <small id="admin-password-error" role="alert">
            {errors.password.message}
          </small>
        ) : null}
      </label>
    </>
  );
}

function adminLoginError(error: Error): string {
  if (!(error instanceof AuthApiError))
    return "Не удалось связаться с сервером. Проверьте подключение и повторите попытку";
  if (error.code === "invalid_credentials") return "Неверный email или пароль";
  if (error.code === "forbidden")
    return "У аккаунта нет доступа к рабочему пространству";
  if (error.code === "rate_limited")
    return "Слишком много попыток. Попробуйте позже";
  if (error.code === "service_unavailable" || error.status >= 500)
    return "Сервис входа временно недоступен. Попробуйте позже";
  return "Не удалось войти. Попробуйте ещё раз";
}
