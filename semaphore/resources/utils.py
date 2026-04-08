import sys


def resolve_key(key_map: dict[str, int], key_name: str, resource_type: str, resource_name: str) -> int:
    """Look up a key name in key_map and return its id.

    Exits with a human-readable error if the key does not exist, listing the
    available key names so the user knows what to fix in their config file.
    """
    if key_name not in key_map:
        available = ", ".join(sorted(key_map.keys())) or "(none)"
        print(
            f"ERROR: {resource_type} '{resource_name}' references key '{key_name}' which does not exist in this project.",
            file=sys.stderr,
        )
        print(f"       Available keys: {available}", file=sys.stderr)
        sys.exit(1)
    return key_map[key_name]
