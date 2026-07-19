import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getCurrentAccount,
  login,
  logout,
  register,
  type Credentials,
  type CurrentAccount,
} from "../api/authApi";
import { authQueryKeys } from "./authQueryKeys";

export function useCurrentAccount() {
  return useQuery({
    queryKey: authQueryKeys.currentAccount,
    queryFn: getCurrentAccount,
  });
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
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: authQueryKeys.adminSession });
      queryClient.setQueryData(authQueryKeys.currentAccount, null);
    },
  });
}

function useSessionMutation(
  action: (credentials: Credentials) => Promise<CurrentAccount>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: action,
    onSuccess: (account) => {
      queryClient.removeQueries({ queryKey: authQueryKeys.adminSession });
      queryClient.setQueryData(authQueryKeys.currentAccount, account);
    },
  });
}
