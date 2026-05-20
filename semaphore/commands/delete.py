import sys

from semaphore.client import SemaphoreClient
from semaphore.resources import (
    delete_environment, delete_inventory, delete_template,
    list_environments, list_inventory, list_projects, list_templates,
)


# resource_type -> (lister, deleter, plural_label)
_HANDLERS = {
    "template":    (list_templates,    delete_template,    "templates"),
    "inventory":   (list_inventory,    delete_inventory,   "inventories"),
    "environment": (list_environments, delete_environment, "environments"),
}


def delete(
    client: SemaphoreClient,
    project_ref: str,
    resource_type: str,
    resource_names: list[str],
) -> None:
    """Delete one or more named resources of a single type from a project.

    Resource type must be one of: template, inventory, environment.
    Names are matched exactly. Resolves every name before deleting anything;
    aborts if any name is missing or ambiguous. Asks for a single
    confirmation listing every resource to be deleted.

    Secret values (SSH keys, passwords) are never touched by this command —
    use the SemaphoreUI UI for those.
    """
    if resource_type not in _HANDLERS:
        print(
            f"ERROR: unknown resource type '{resource_type}'. "
            f"Supported: {', '.join(_HANDLERS)}.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not resource_names:
        print(f"ERROR: 'delete' requires at least one {resource_type} name.", file=sys.stderr)
        sys.exit(1)

    project = _find_project(client, project_ref)
    if project is None:
        print(f"ERROR: project '{project_ref}' not found.", file=sys.stderr)
        sys.exit(1)

    project_id = project["id"]
    project_name = project["name"]

    list_fn, delete_fn, plural = _HANDLERS[resource_type]
    deployed = list_fn(client, project_id)
    by_name: dict[str, list[dict]] = {}
    for r in deployed:
        by_name.setdefault(r.get("name", ""), []).append(r)

    # Resolve every requested name up front; do not delete anything if any
    # name is missing or ambiguous.
    resolved: list[tuple[str, dict]] = []
    errors: list[str] = []
    for name in resource_names:
        matches = by_name.get(name, [])
        if not matches:
            errors.append(f"  - {resource_type} '{name}' not found")
        elif len(matches) > 1:
            ids = ", ".join(str(m["id"]) for m in matches)
            errors.append(f"  - {resource_type} '{name}' is ambiguous (matches ids: {ids})")
        else:
            resolved.append((name, matches[0]))

    if errors:
        print(f"ERROR: cannot delete from project '{project_name}':", file=sys.stderr)
        for line in errors:
            print(line, file=sys.stderr)
        sys.exit(1)

    print(f"Project: {project_name}  (id={project_id})")
    print(f"About to PERMANENTLY delete {len(resolved)} {plural}:")
    for name, target in resolved:
        print(f"  - {name}  (id={target['id']})")
    print()

    answer = input("Type 'yes' to confirm: ").strip().lower()
    if answer != "yes":
        print("Aborted. Nothing was deleted.")
        sys.exit(1)

    print()
    for name, target in resolved:
        delete_fn(client, project_id, target["id"])
        print(f"  [deleted] {resource_type}: {name}  (id={target['id']})")

    print(f"\nDeleted {len(resolved)} {plural} from '{project_name}'.")


def _find_project(client: SemaphoreClient, ref: str) -> dict | None:
    projects = list_projects(client)
    if ref.isdigit():
        target_id = int(ref)
        return next((p for p in projects if p["id"] == target_id), None)
    return next((p for p in projects if p["name"] == ref), None)
