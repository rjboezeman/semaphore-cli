# semaphore-cli

A command-line tool for managing [SemaphoreUI](https://semaphoreui.com) (Ansible Semaphore) configuration as code.

`semaphore-cli` works with **SemaphoreUI's own export format** — the JSON file you get from *Project → Settings → Export*. You can use it to apply that file to any SemaphoreUI instance, compare it against what is deployed, or restore a project after a `purge`.

```
semaphore-cli apply  config.json   # create or update all resources
semaphore-cli diff   config.json   # compare config against deployed state
semaphore-cli check                # verify connectivity and access rights
semaphore-cli purge                # delete everything (with confirmation)
semaphore-cli list                 # list deployed projects
```

---

## Features

- **Apply** — server-side apply from a SemaphoreUI export file. Creates new resources and updates existing ones, matched by name. Never deletes anything not in the file.
- **Diff** — compare a config file against the live state and report what is new `[+]`, changed `[~]`, or already in sync `[=]`.
- **Check** — verify that the API is reachable, login works, and the account has sufficient rights to create and update resources. Reports per-project roles and resource counts.
- **Purge** — delete all projects and their resources. Requires typing a very convincing confirmation phrase.
- **Schema validation** — every config file is validated against a JSON schema before any API call is made. Invalid files are rejected with the exact field path that is wrong.
- **Native export format** — no custom schema to learn. Use the file SemaphoreUI already generates.
- **Secret-aware** — export files never contain credentials. Existing keys are left untouched on apply to preserve live credentials. New keys are created with placeholder values and flagged for manual update.

---

## Requirements

- Python 3.12 or newer
- A running [SemaphoreUI](https://semaphoreui.com) instance
- An admin account on that instance

---

## Installation

```bash
git clone https://github.com/rjboezeman/semaphore-cli.git
cd semaphore-cli
pip install .
```

For development (changes take effect immediately without reinstalling):

```bash
pip install -e .
```

This installs a `semaphore-cli` command on your `PATH`.

---

## Configuration

Create a `.env` file in the directory where you run the tool (use `.env.example` as a template):

```bash
cp .env.example .env
```

```ini
semaphore_url=https://semaphore.example.com
username=admin@example.com
password=your-password-here
```

The `.env` file is listed in `.gitignore` and will never be committed.

---

## Usage

### `semaphore-cli check`

Verify that the API is reachable, that login succeeds, and that the configured account has the rights needed to create and update resources. Lists all deployed projects with their resource counts and per-project role. Safe to run at any time — makes no changes.

```
$ semaphore-cli check

Connectivity
  [ok]   Logged in as 'Admin' (admin@example.com)

Account rights
  [ok]   Global admin — full rights on all projects
  [ok]   Can create new projects

Projects
  [ok]   2 project(s) found

  Project: Web Infrastructure  (id=1)
    [ok]   Role: owner       (full access)
    [ok]   Resources: 3 keys, 2 repositories, 3 inventory, 2 environments, 7 templates

  Project: Terraform Infrastructure  (id=2)
    [ok]   Role: owner       (full access)
    [ok]   Resources: 1 keys, 1 repositories, 1 inventory, 2 environments, 5 templates

[ok]   All checks passed — ready to apply.
```

---

### `semaphore-cli apply <config.json>`

Apply a SemaphoreUI export file to the instance. The project is identified by the `name` field in `meta`. Resources are matched by name:

- If a resource with that name already exists → it is updated.
- If it does not exist → it is created.
- Resources present on the server but not in the file → left untouched.

**Note on keys:** Export files never contain secret values (SSH private keys, passwords). Existing keys are skipped to preserve live credentials. New keys are created with `PLACEHOLDER` values — you must update them via the SemaphoreUI UI before running tasks.

```
$ semaphore-cli apply web-infrastructure.json

Project: Web Infrastructure
  [created] id=1
  Keys:
    [created] Deploy SSH Key  (⚠ placeholder credentials — update via UI before use)
    [created] Sudo Credentials  (⚠ placeholder credentials — update via UI before use)
  Repositories:
    [created] Ansible Playbooks
    [created] Ansible Roles
  Inventory:
    [created] Production
    [created] Staging
  Environments:
    [updated] Empty
    [created] Production
  Templates:
    [created] Deploy Application (Production)
    [created] Rolling Restart (Production)
    ...

Done.
```

---

### `semaphore-cli diff <config.json>`

Compare a config file against the currently deployed state without making any changes.

```
[+]  resource is new — will be created on next apply
[~]  resource exists but one or more fields differ
[=]  resource matches the deployed state
```

**Note:** Secret values (SSH keys, passwords) are write-only in the SemaphoreUI API and cannot be compared. Key entries always show as `[=]` as long as name and type match.

```
$ semaphore-cli diff web-infrastructure.json

[=] Project: Web Infrastructure
  Keys:
    [=] Deploy SSH Key  (secret values are write-only and cannot be compared)
    [=] Sudo Credentials  (secret values are write-only and cannot be compared)
  Repositories:
    [~] Ansible Playbooks
        git_branch: 'main' → 'develop'
    [=] Ansible Roles
  Inventory:
    [=] Production
    [+] DR Site  (not deployed)
  Environments:
    [~] Production
        json: {'app_version': '1.4.2'} → {'app_version': '1.5.0'}
  Templates:
    [=] Deploy Application (Production)

Summary:
  Keys           2 unchanged
  Repositories   1 changed, 1 unchanged
  Inventory      1 new, 1 unchanged
  Environments   1 changed
  Templates      1 unchanged
```

---

### `semaphore-cli purge`

Delete **all** projects and their resources from the SemaphoreUI instance. This is irreversible. You will be asked to prove you really mean it:

```
$ semaphore-cli purge

You are about to PERMANENTLY delete 2 project(s):
  - Web Infrastructure
  - Terraform Infrastructure

To confirm, please type exactly:
  "Yes, I am totally sure and I know what I am doing and I accept all consequences and my mom said it was ok"

>
```

---

### `semaphore-cli list`

List all projects currently deployed on the instance.

```
$ semaphore-cli list

Found 2 project(s):

  [1] Web Infrastructure
  [2] Terraform Infrastructure
```

---

## Config file format

`semaphore-cli` uses the **native SemaphoreUI export format** — the file you get from *Project → Settings → Export* in the SemaphoreUI interface. One file represents one project.

See [`config.example.json`](config.example.json) for a full example. The top-level structure is:

```json
{
  "meta": {
    "name": "My Project",
    "alert": false,
    "alert_chat": "",
    "max_parallel_tasks": 0
  },
  "keys": [
    { "name": "Deploy SSH Key", "type": "ssh", "owner": "" },
    { "name": "Vault Password", "type": "login_password", "owner": "" }
  ],
  "repositories": [
    {
      "name": "Ansible Playbooks",
      "git_url": "https://github.com/myorg/ansible.git",
      "git_branch": "main",
      "ssh_key": "None"
    }
  ],
  "inventories": [
    {
      "name": "Production",
      "type": "static",
      "inventory": "[web]\nweb1 ansible_host=10.0.0.1",
      "ssh_key": "Deploy SSH Key",
      "become_key": "None"
    }
  ],
  "environments": [
    {
      "name": "Production",
      "json": "{\"app_version\": \"1.0.0\"}",
      "env": "{\"ANSIBLE_FORCE_COLOR\": \"1\"}"
    }
  ],
  "templates": [
    {
      "name": "Deploy",
      "app": "ansible",
      "playbook": "deploy.yml",
      "repository": "Ansible Playbooks",
      "inventory": "Production",
      "environment": "Production",
      "description": "Deploy the application"
    }
  ]
}
```

Resources reference each other by **name** (the same names used in the SemaphoreUI UI). Two names are always available without being defined:

| Name | Description |
|------|-------------|
| `None` | The auto-created key with no credentials |
| `Empty` | The auto-created empty environment |

Supported values for `template.app`: `ansible`, `terraform`, `tofu`, `bash`, `powershell`.  
Supported values for `inventory.type`: `static`, `file`.

The file is validated against a JSON schema before any API calls are made. If the file is invalid, the exact field path is reported:

```
ERROR: Invalid export file — 'invalid_app' is not one of ['ansible', 'terraform', 'tofu', 'bash', 'powershell']
       at: templates → 0 → app
```

---

## Project structure

```
semaphore/
├── client.py          # SemaphoreClient — thin wrapper around requests.Session
├── cli.py             # Entry point, subcommand routing, .env loading
├── schema.py          # JSON schema definition and validation
├── commands/
│   ├── apply.py       # Server-side apply logic
│   ├── diff.py        # Diff reporting logic
│   ├── check.py       # Connectivity and rights check
│   └── purge.py       # Purge with confirmation
└── resources/
    ├── projects.py    # list_projects, create_project, update_project
    ├── keys.py        # list_keys, create_key, update_key
    ├── repositories.py
    ├── inventory.py
    ├── environments.py
    └── templates.py
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE).
