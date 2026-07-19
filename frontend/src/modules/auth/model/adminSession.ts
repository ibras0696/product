import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getAdminAccount,
  loginAdmin,
  logout,
  type Credentials,
} from "../api/authApi";
import { authQueryKeys } from "./authQueryKeys";

export const adminSessionKey = authQueryKeys.adminSession;

export function useAdminSession() {
  return useQuery({
    queryKey: adminSessionKey,
    queryFn: getAdminAccount,
    retry: false,
  });
}

export function useAdminLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (credentials: Credentials) => loginAdmin(credentials),
    onSuccess: (account) => {
      queryClient.setQueryData(adminSessionKey, account);
      queryClient.setQueryData(authQueryKeys.currentAccount, account);
    },
  });
}

export function useAdminLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.setQueryData(adminSessionKey, null);
      queryClient.setQueryData(authQueryKeys.currentAccount, null);
    },
  });
}

export function safeAdminReturnPath(value: string | null): string {
  if (!value?.startsWith("/admin") || value.startsWith("//")) return "/admin";
  return value;
}
