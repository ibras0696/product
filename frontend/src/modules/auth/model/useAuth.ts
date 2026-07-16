import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getCurrentAccount,
  login,
  logout,
  register,
  type Credentials,
  type CurrentAccount,
} from "../api/authApi";

const currentAccountKey = ["auth", "current-account"] as const;

export function useCurrentAccount() {
  return useQuery({ queryKey: currentAccountKey, queryFn: getCurrentAccount });
}

export function useLogin() {
  return useSessionMutation(login);
}

export function useRegister() {
  return useSessionMutation(register);
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: logout,
    onSuccess: () => queryClient.setQueryData(currentAccountKey, null),
  });
}

function useSessionMutation(
  action: (credentials: Credentials) => Promise<CurrentAccount>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: action,
    onSuccess: (account) =>
      queryClient.setQueryData(currentAccountKey, account),
  });
}
