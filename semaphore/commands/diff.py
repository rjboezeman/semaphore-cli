import json as json_mod
from dataclasses import dataclass, field

from semaphore.client import SemaphoreClient
from semaphore.resources import (
    list_environments, list_inventory, list_keys,
    list_projects, list_repositories, list_templates,
)

_NEW       = "[+]"
_CHANGED   = "[~]"
_UNCHANGED = "[=]"


@dataclass
class ResourceDiff:
    status: str
    name: str
    changes: dict = field(default_factory=dict)   # field → (deployed, config)
    note: str = ""


def diff(client: SemaphoreClient, config: dict) -> None:
    """Compare a SemaphoreUI export file against the currently deployed state."""
    proj_name = config["meta"]["name"]
    deployed_projects = {p["name"]: p for p in list_projects(client)}
    counters: dict[str, list[int]] = {}

    if proj_name not in deployed_projects:
        print(f"\n{_NEW} Project: {proj_name}  (not deployed — all resources will be created on apply)")
        _count_all_new(config, counters)
        _print_summary(counters)
        return

    project_id = deployed_projects[proj_name]["id"]
    proj_changes = _compare({
        "alert":              (deployed_projects[proj_name].get("alert", False),          config["meta"].get("alert", False)),
        "max_parallel_tasks": (deployed_projects[proj_name].get("max_parallel_tasks", 0), config["meta"].get("max_parallel_tasks", 0)),
    })
    status = _CHANGED if proj_changes else _UNCHANGED
    print(f"\n{status} Project: {proj_name}")
    for f, (old, new) in proj_changes.items():
        print(f"    {f}: {old!r} → {new!r}")

    # Fetch deployed resources and build name→resource maps
    srv_keys  = {k["name"]: k for k in list_keys(client, project_id)}
    srv_repos = {r["name"]: r for r in list_repositories(client, project_id)}
    srv_invs  = {i["name"]: i for i in list_inventory(client, project_id)}
    srv_envs  = {e["name"]: e for e in list_environments(client, project_id)}
    srv_tmpls = {t["name"]: t for t in list_templates(client, project_id)}

    # Reverse id→name maps for resolving foreign keys in diff comparisons
    key_id_to_name  = {k["id"]: k["name"] for k in srv_keys.values()}
    repo_id_to_name = {r["id"]: r["name"] for r in srv_repos.values()}
    inv_id_to_name  = {i["id"]: i["name"] for i in srv_invs.values()}
    env_id_to_name  = {e["id"]: e["name"] for e in srv_envs.values()}

    print("  Keys:")
    diffs = _diff_keys(config.get("keys", []), srv_keys)
    _print_diffs(diffs, "    ")
    _tally("keys", diffs, counters)

    print("  Repositories:")
    diffs = _diff_repositories(config.get("repositories", []), srv_repos, key_id_to_name)
    _print_diffs(diffs, "    ")
    _tally("repositories", diffs, counters)

    print("  Inventory:")
    diffs = _diff_inventory(config.get("inventories", []), srv_invs, key_id_to_name)
    _print_diffs(diffs, "    ")
    _tally("inventory", diffs, counters)

    print("  Environments:")
    diffs = _diff_environments(config.get("environments", []), srv_envs)
    _print_diffs(diffs, "    ")
    _tally("environments", diffs, counters)

    print("  Templates:")
    diffs = _diff_templates(config.get("templates", []), srv_tmpls, repo_id_to_name, inv_id_to_name, env_id_to_name)
    _print_diffs(diffs, "    ")
    _tally("templates", diffs, counters)

    _print_summary(counters)


# ---------------------------------------------------------------------------
# Per-resource diff functions
# ---------------------------------------------------------------------------

def _diff_keys(keys_cfg: list[dict], srv_by_name: dict) -> list[ResourceDiff]:
    results = []
    for cfg in keys_cfg:
        name = cfg["name"]
        if name not in srv_by_name:
            results.append(ResourceDiff(_NEW, name))
            continue
        srv = srv_by_name[name]
        changes = _compare({"type": (srv["type"], cfg["type"])})
        note = "secret values are write-only and cannot be compared"
        results.append(ResourceDiff(_CHANGED if changes else _UNCHANGED, name, changes, note))
    return results


def _diff_repositories(repos_cfg: list[dict], srv_by_name: dict, key_id_to_name: dict) -> list[ResourceDiff]:
    results = []
    for cfg in repos_cfg:
        name = cfg["name"]
        if name not in srv_by_name:
            results.append(ResourceDiff(_NEW, name))
            continue
        srv = srv_by_name[name]
        changes = _compare({
            "git_url":    (srv["git_url"],    cfg["git_url"]),
            "git_branch": (srv["git_branch"], cfg.get("git_branch", "main")),
            "ssh_key":    (key_id_to_name.get(srv.get("ssh_key_id"), "None"), cfg.get("ssh_key", "None")),
        })
        results.append(ResourceDiff(_CHANGED if changes else _UNCHANGED, name, changes))
    return results


def _diff_inventory(inventory_cfg: list[dict], srv_by_name: dict, key_id_to_name: dict) -> list[ResourceDiff]:
    results = []
    for cfg in inventory_cfg:
        name = cfg["name"]
        if name not in srv_by_name:
            results.append(ResourceDiff(_NEW, name))
            continue
        srv = srv_by_name[name]
        changes = _compare({
            "type":       (srv["type"],      cfg.get("type", "static")),
            "inventory":  (srv["inventory"], cfg.get("inventory", "")),
            "ssh_key":    (key_id_to_name.get(srv.get("ssh_key_id"), "None"),    cfg.get("ssh_key", "None")),
            "become_key": (key_id_to_name.get(srv.get("become_key_id"), "None"), cfg.get("become_key", "None")),
        })
        results.append(ResourceDiff(_CHANGED if changes else _UNCHANGED, name, changes))
    return results


def _diff_environments(environments_cfg: list[dict], srv_by_name: dict) -> list[ResourceDiff]:
    results = []
    for cfg in environments_cfg:
        name = cfg["name"]
        if name not in srv_by_name:
            results.append(ResourceDiff(_NEW, name))
            continue
        srv = srv_by_name[name]
        changes = _compare({
            "json": (_parse_json_field(srv.get("json")), _parse_json_field(cfg.get("json"))),
            "env":  (_parse_json_field(srv.get("env")),  _parse_json_field(cfg.get("env"))),
        })
        results.append(ResourceDiff(_CHANGED if changes else _UNCHANGED, name, changes))
    return results


def _diff_templates(
    templates_cfg: list[dict],
    srv_by_name: dict,
    repo_id_to_name: dict,
    inv_id_to_name: dict,
    env_id_to_name: dict,
) -> list[ResourceDiff]:
    results = []
    for cfg in templates_cfg:
        name = cfg["name"]
        if name not in srv_by_name:
            results.append(ResourceDiff(_NEW, name))
            continue
        srv = srv_by_name[name]
        changes = _compare({
            "app":                           (srv.get("app", ""),                      cfg.get("app", "ansible")),
            "playbook":                      (srv.get("playbook", ""),                 cfg.get("playbook", "")),
            "repository":                    (repo_id_to_name.get(srv["repository_id"], "?"), cfg["repository"]),
            "inventory":                     (inv_id_to_name.get(srv["inventory_id"], "?"),   cfg["inventory"]),
            "environment":                   (env_id_to_name.get(srv["environment_id"], "?"), cfg["environment"]),
            "description":                   (srv.get("description", ""),              cfg.get("description", "")),
            "allow_override_args_in_task":   (srv.get("allow_override_args_in_task", False),   cfg.get("allow_override_args_in_task", False)),
            "allow_override_branch_in_task": (srv.get("allow_override_branch_in_task", False), cfg.get("allow_override_branch_in_task", False)),
            "allow_parallel_tasks":          (srv.get("allow_parallel_tasks", False),  cfg.get("allow_parallel_tasks", False)),
            "suppress_success_alerts":       (srv.get("suppress_success_alerts", False), cfg.get("suppress_success_alerts", False)),
            "autorun":                       (srv.get("autorun", False),               cfg.get("autorun", False)),
            "survey_vars":                   (srv.get("survey_vars") or [],            cfg.get("survey_vars") or []),
            "task_params":                   (srv.get("task_params") or {},            cfg.get("task_params") or {}),
        })
        results.append(ResourceDiff(_CHANGED if changes else _UNCHANGED, name, changes))
    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compare(fields: dict) -> dict:
    return {k: v for k, v in fields.items() if v[0] != v[1]}


def _parse_json_field(value: str | dict | None) -> dict | None:
    if value is None or value == "null":
        return None
    if isinstance(value, dict):
        return value
    try:
        return json_mod.loads(value)
    except (json_mod.JSONDecodeError, TypeError):
        return value


def _print_diffs(diffs: list[ResourceDiff], indent: str) -> None:
    for d in diffs:
        if d.status == _NEW:
            print(f"{indent}{_NEW} {d.name}  (not deployed)")
        elif d.status == _CHANGED:
            suffix = f"  ({d.note})" if d.note else ""
            print(f"{indent}{_CHANGED} {d.name}{suffix}")
            for f, (old, new) in d.changes.items():
                print(f"{indent}    {f}: {old!r} → {new!r}")
        else:
            suffix = f"  ({d.note})" if d.note else ""
            print(f"{indent}{_UNCHANGED} {d.name}{suffix}")


def _tally(resource_type: str, diffs: list[ResourceDiff], counters: dict) -> None:
    c = counters.setdefault(resource_type, [0, 0, 0])
    for d in diffs:
        if d.status == _NEW:       c[0] += 1
        elif d.status == _CHANGED: c[1] += 1
        else:                      c[2] += 1


def _count_all_new(config: dict, counters: dict) -> None:
    for resource_type, key in [
        ("keys", "keys"), ("repositories", "repositories"),
        ("inventory", "inventories"), ("environments", "environments"),
        ("templates", "templates"),
    ]:
        counters.setdefault(resource_type, [0, 0, 0])[0] += len(config.get(key, []))


def _print_summary(counters: dict) -> None:
    print("\nSummary:")
    labels = [
        ("keys",         "Keys"),
        ("repositories", "Repositories"),
        ("inventory",    "Inventory"),
        ("environments", "Environments"),
        ("templates",    "Templates"),
    ]
    for key, label in labels:
        if key not in counters:
            continue
        new, changed, unchanged = counters[key]
        parts = []
        if new:       parts.append(f"{new} new")
        if changed:   parts.append(f"{changed} changed")
        if unchanged: parts.append(f"{unchanged} unchanged")
        print(f"  {label:<14} {', '.join(parts) if parts else 'none'}")
