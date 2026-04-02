import json
import os
import sys

from dotenv import load_dotenv

from semaphore.client import SemaphoreClient
from semaphore.commands import apply, check, diff, purge
from semaphore.resources import list_projects
from semaphore.schema import validate_export

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

_BASE_URL = os.getenv("semaphore_url", "https://semaphoreui.services.notarieelbetalen.nl")
_USERNAME = os.getenv("username")
_PASSWORD = os.getenv("password")

_USAGE = """\
SemaphoreUI configuration tool

Usage:
  semaphore-cli <command> [arguments]

Commands:
  apply  <config.json>
        Server-side apply: create or update every resource defined in the
        config file. Resources not present in the config are left untouched.
        Resources are matched by name; existing ones are updated in-place.

  diff   <config.json>
        Compare the config file against the currently deployed state and
        print a summary of differences.
          [+]  resource is new and will be created on next apply
          [~]  resource exists but one or more fields differ
          [=]  resource matches the deployed state (no change needed)
        Note: secret values (SSH keys, passwords) are write-only in the
        SemaphoreUI API and cannot be compared.

  check
        Verify that the API is reachable, login succeeds, and the configured
        account has sufficient rights to create and update resources.
        Lists all deployed projects with their resource counts and per-project
        role. Safe to run at any time — makes no changes.

  purge
        Delete ALL projects and their resources from SemaphoreUI.
        This operation is irreversible. You will be asked to prove
        you really mean it before anything is touched.

  list
        List all projects currently deployed in SemaphoreUI.

Config file format:
  See config.example.json for a full example. Supported resource types
  per project: keys, repositories, inventory, environments, templates.
  Resources reference each other by 'ref' (a local name you define).
  Two built-in refs are always available:
    "none"   — the auto-created key with no credentials
    "empty"  — the auto-created empty environment
"""


def main() -> None:
    if not _USERNAME or not _PASSWORD:
        print("ERROR: username and password must be set in .env", file=sys.stderr)
        sys.exit(1)

    args = sys.argv[1:]

    if not args:
        print(_USAGE)
        sys.exit(0)

    subcommand = args[0]

    with SemaphoreClient(_BASE_URL, _USERNAME, _PASSWORD) as client:
        client.login()

        if subcommand == "list":
            projects = list_projects(client)
            if not projects:
                print("No projects found.")
            else:
                print(f"Found {len(projects)} project(s):\n")
                for p in projects:
                    print(f"  [{p['id']}] {p['name']}")

        elif subcommand == "check":
            check(client)

        elif subcommand == "purge":
            purge(client)

        elif subcommand in ("apply", "diff"):
            if len(args) < 2:
                print(f"ERROR: '{subcommand}' requires a config file argument.", file=sys.stderr)
                sys.exit(1)
            config_path = args[1]
            if not os.path.exists(config_path):
                print(f"ERROR: config file not found: {config_path}", file=sys.stderr)
                sys.exit(1)
            with open(config_path) as f:
                config = json.load(f)
            validate_export(config)
            if subcommand == "apply":
                apply(client, config)
            else:
                diff(client, config)

        else:
            print(f"ERROR: unknown subcommand '{subcommand}'\n", file=sys.stderr)
            print(_USAGE)
            sys.exit(1)
