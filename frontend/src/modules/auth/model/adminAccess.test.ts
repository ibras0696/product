import { adminAccessForRoles } from "./adminAccess";

it("keeps moderation, catalog and audit capabilities separated by admin role", () => {
  expect(adminAccessForRoles(["moderator"])).toEqual({
    moderation: "publish",
    catalog: { read: true, write: false, export: false, auditRead: false },
  });
  expect(adminAccessForRoles(["editor"])).toEqual({
    moderation: "none",
    catalog: { read: true, write: true, export: true, auditRead: false },
  });
  expect(adminAccessForRoles(["admin"])).toEqual({
    moderation: "publish",
    catalog: { read: true, write: true, export: true, auditRead: true },
  });
  expect(adminAccessForRoles([])).toEqual({
    moderation: "none",
    catalog: { read: false, write: false, export: false, auditRead: false },
  });
});
