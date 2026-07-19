import type { AdminRole } from "../api/authApi";

export interface AdminFeatureAccess {
  moderation: "none" | "read" | "decide" | "publish";
  catalog: {
    read: boolean;
    write: boolean;
    export: boolean;
    auditRead: boolean;
  };
}

export function adminAccessForRoles(
  roles: readonly AdminRole[],
): AdminFeatureAccess {
  const isAdmin = roles.includes("admin");
  const isModerator = roles.includes("moderator");
  const isEditor = roles.includes("editor");
  return {
    moderation: isAdmin || isModerator ? "publish" : "none",
    catalog: {
      read: isAdmin || isModerator || isEditor,
      write: isAdmin || isEditor,
      export: isAdmin || isEditor,
      auditRead: isAdmin,
    },
  };
}
