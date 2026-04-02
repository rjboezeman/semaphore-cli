"""
JSON schema for the SemaphoreUI project export format.

This is the native format produced by SemaphoreUI's own Export function
(Project → Settings → Export). One file = one project.
"""

import jsonschema

EXPORT_SCHEMA: dict = {
    "type": "object",
    "required": ["meta", "keys", "repositories", "inventories", "environments", "templates"],
    "additionalProperties": True,
    "properties": {
        "meta": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name":                {"type": "string",  "minLength": 1},
                "alert":               {"type": "boolean"},
                "alert_chat":          {"type": "string"},
                "max_parallel_tasks":  {"type": "integer", "minimum": 0},
                "type":                {"type": "string"},
            },
        },
        "keys": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "type"],
                "properties": {
                    "name":  {"type": "string", "minLength": 1},
                    "type":  {"type": "string", "enum": ["ssh", "login_password", "none"]},
                    "owner": {"type": "string"},
                },
            },
        },
        "repositories": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "git_url", "git_branch", "ssh_key"],
                "properties": {
                    "name":       {"type": "string", "minLength": 1},
                    "git_url":    {"type": "string", "minLength": 1},
                    "git_branch": {"type": "string", "minLength": 1},
                    "ssh_key":    {"type": "string", "minLength": 1},
                },
            },
        },
        "inventories": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "type"],
                "properties": {
                    "name":       {"type": "string", "minLength": 1},
                    "type":       {"type": "string", "enum": ["static", "file"]},
                    "inventory":  {"type": "string"},
                    "ssh_key":    {"type": "string"},
                    "become_key": {"type": "string"},
                },
            },
        },
        "environments": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "json": {"type": ["string", "null"]},
                    "env":  {"type": ["string", "null"]},
                },
            },
        },
        "templates": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "app", "playbook", "repository", "inventory", "environment"],
                "properties": {
                    "name":                          {"type": "string", "minLength": 1},
                    "app":                           {"type": "string", "enum": ["ansible", "terraform", "tofu", "bash", "powershell"]},
                    "type":                          {"type": "string"},
                    "playbook":                      {"type": "string"},
                    "repository":                    {"type": "string", "minLength": 1},
                    "inventory":                     {"type": "string", "minLength": 1},
                    "environment":                   {"type": "string", "minLength": 1},
                    "description":                   {"type": "string"},
                    "allow_override_args_in_task":   {"type": "boolean"},
                    "allow_override_branch_in_task": {"type": "boolean"},
                    "allow_parallel_tasks":          {"type": "boolean"},
                    "suppress_success_alerts":       {"type": "boolean"},
                    "autorun":                       {"type": "boolean"},
                    "survey_vars":                   {"type": "array"},
                    "vaults":                        {"type": "array"},
                    "task_params":                   {"type": "object"},
                },
            },
        },
        # Optional fields present in real exports
        "schedules":          {"type": "array"},
        "views":              {"type": "array"},
        "integrations":       {"type": "array"},
        "integration_aliases":{"type": "array"},
        "secret_storages":    {"type": "array"},
    },
}


def validate_export(data: dict) -> None:
    """Validate a parsed JSON export against the schema.

    Raises ``SystemExit`` with a human-readable message on failure.
    """
    import sys

    try:
        jsonschema.validate(instance=data, schema=EXPORT_SCHEMA)
    except jsonschema.ValidationError as exc:
        path = " → ".join(str(p) for p in exc.absolute_path) or "(root)"
        print(f"ERROR: Invalid export file — {exc.message}", file=sys.stderr)
        print(f"       at: {path}", file=sys.stderr)
        sys.exit(1)
    except jsonschema.SchemaError as exc:
        print(f"ERROR: Internal schema error — {exc.message}", file=sys.stderr)
        sys.exit(1)
