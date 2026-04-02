import sys

from semaphore.client import SemaphoreClient
from semaphore.resources import list_projects

_CONFIRMATION = "Yes, I am totally sure and I know what I am doing and I accept all consequences and my mom said it was ok"


def purge(client: SemaphoreClient) -> None:
    """Delete all projects and their resources from SemaphoreUI."""
    projects = list_projects(client)

    if not projects:
        print("Nothing to purge.")
        return

    print(f"You are about to PERMANENTLY delete {len(projects)} project(s):")
    for p in projects:
        print(f"  - {p['name']}")

    print(f'\nTo confirm, please type exactly:\n  "{_CONFIRMATION}"\n')
    answer = input("> ").strip()

    if answer != _CONFIRMATION:
        print("\nAborted. Your data lives to see another day.")
        sys.exit(1)

    print()
    for project in projects:
        client.delete(f"/api/project/{project['id']}")
        print(f"  [deleted] {project['name']}  (id={project['id']})")

    print(f"\nPurged {len(projects)} project(s). Hope you meant to do that.")
