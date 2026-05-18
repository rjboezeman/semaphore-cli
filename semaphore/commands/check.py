import sys

from semaphore.client import SemaphoreClient
from semaphore.resources import (
    list_environments, list_inventory, list_keys,
    list_projects, list_repositories, list_templates,
)

# Project roles in ascending order of privilege
_ROLE_WRITE = {"owner", "manager"}
_ROLE_LABEL = {
    "owner":       "owner       (full access)",
    "manager":     "manager     (can update resources)",
    "task_runner": "task_runner (can run tasks, no resource updates)",
    "guest":       "guest       (read-only)",
}

_OK   = "[ok]"
_WARN = "[warn]"
_FAIL = "[fail]"


def check(client: SemaphoreClient) -> None:
    """Check connectivity, authentication, and access rights."""
    all_ok = True

    # ------------------------------------------------------------------
    # 1. Login (already done by caller, but verify with /api/user)
    # ------------------------------------------------------------------
    print("Connectivity")
    try:
        user = client.get("/api/user")
        print(f"  {_OK}   Logged in as '{user['name']}' ({user['email']})")
    except Exception as exc:
        print(f"  {_FAIL} Could not reach API: {exc}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 2. Global account rights
    # ------------------------------------------------------------------
    print("\nAccount rights")
    if user.get("admin"):
        print(f"  {_OK}   Global admin — full rights on all projects")
    else:
        print(f"  {_WARN} Not a global admin — rights are per-project (see below)")
        all_ok = False

    if user.get("can_create_project"):
        print(f"  {_OK}   Can create new projects")
    else:
        print(f"  {_WARN} Cannot create new projects")
        all_ok = False

    # ------------------------------------------------------------------
    # 3. Projects
    # ------------------------------------------------------------------
    print("\nProjects")
    projects = list_projects(client)

    if not projects:
        print(f"  {_WARN} No projects found — nothing to check")
    else:
        print(f"  {_OK}   {len(projects)} project(s) found\n")

    for project in projects:
        pid   = project["id"]
        pname = project["name"]

        # Per-project role
        try:
            role_data   = client.get(f"/api/project/{pid}/role")
            role        = role_data.get("role", "unknown")
            role_label  = _ROLE_LABEL.get(role, role)
            can_write   = role in _ROLE_WRITE or user.get("admin", False)
            rights_icon = _OK if can_write else _WARN
            if not can_write:
                all_ok = False
        except Exception:
            role_label  = "unknown"
            rights_icon = _WARN
            can_write   = False
            all_ok      = False

        print(f"  Project: {pname}  (id={pid})")
        print(f"    {rights_icon}   Role: {role_label}")

        # Resource counts
        try:
            counts = {
                "keys":         len([k for k in list_keys(client, pid) if k["type"] != "none"]),
                "repositories": len(list_repositories(client, pid)),
                "inventory":    len(list_inventory(client, pid)),
                "environments": len([e for e in list_environments(client, pid) if e["name"] != "Empty"]),
                "templates":    len(list_templates(client, pid)),
            }
            summary = ", ".join(f"{v} {k}" for k, v in counts.items())
            print(f"    {_OK}   Resources: {summary}")
        except Exception as exc:
            print(f"    {_FAIL} Could not read project resources: {exc}")
            all_ok = False

        print()

    # ------------------------------------------------------------------
    # 4. Overall verdict
    # ------------------------------------------------------------------
    if all_ok:
        print(f"{_OK}   All checks passed — ready to apply.")
    else:
        print(f"{_WARN} Some checks failed — review the warnings above before running apply.")
