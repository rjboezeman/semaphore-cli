# Contributing

Contributions are welcome. This document explains how to get started.

## Development setup

```bash
git clone https://github.com/rjboezeman/semaphore-cli.git
cd semaphore-cli

# Create and activate a virtual environment (Python 3.12+)
python -m venv .venv
source .venv/bin/activate

# Install in editable mode with all dependencies
pip install -e .

# Copy the environment template and fill in your SemaphoreUI details
cp .env.example .env
```

## Project structure

```
semaphore/
├── client.py          # SemaphoreClient — wraps requests.Session
├── cli.py             # Entry point, subcommand routing
├── schema.py          # JSON schema for SemaphoreUI export format
├── commands/
│   ├── apply.py       # Server-side apply (create or update, never delete)
│   ├── diff.py        # Compare config vs deployed state
│   ├── check.py       # Connectivity and rights check
│   └── purge.py       # Delete all projects
└── resources/
    ├── projects.py
    ├── keys.py
    ├── repositories.py
    ├── inventory.py
    ├── environments.py
    └── templates.py
```

## Making changes

- Resource CRUD lives in `semaphore/resources/`. Each module exposes `list_*`, `create_*`, and `update_*` functions that take a `SemaphoreClient` instance.
- Commands orchestrate resource modules and handle user output. Keep I/O out of resource modules.
- The `SemaphoreClient` in `client.py` is the only place that calls `requests`. Keep it that way.
- The JSON schema in `schema.py` must stay in sync with the SemaphoreUI export format. If SemaphoreUI adds new fields to its export, update the schema to allow them (`additionalProperties: true` is set on most objects for forward compatibility).

## Testing against a real instance

The tool does not have a mock-based test suite — it is tested against a live SemaphoreUI instance. A useful workflow:

```bash
semaphore check                        # verify connectivity
semaphore apply config.example.json   # apply the example config
semaphore diff config.example.json    # should show all [=]
semaphore purge                        # clean up
```

## Submitting changes

1. Fork the repository and create a branch from `main`.
2. Make your changes and test them against a live SemaphoreUI instance.
3. Open a pull request with a clear description of what you changed and why.

## Reporting bugs

Open an issue at https://github.com/rjboezeman/semaphore-cli/issues. Include:
- Your SemaphoreUI version
- The command you ran
- The full error output
- The relevant section of your config file (redact any secrets)
