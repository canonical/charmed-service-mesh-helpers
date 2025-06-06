"""Helpers for generating and managing Kubernetes labels."""

import hashlib


def charm_kubernetes_label(
        model_name: str,
        app_name: str,
        prefix: str="",
        suffix: str="",
        max_length: int=63,
        separator: str="."
) -> str:
    """Generate a Kubernetes label string in the form "{prefix}{model_name}{separator}{app_name}{suffix}".

    If the label exceeds 63 characters, model_name and app_name will be truncated and a hash of
    "{model_name}{separator}{app_name}" will be appended to the label to ensure uniqueness. The hash is only included if
     truncation occurs.

    Args:
        model_name (str): The name of the model (must be at least 1 character).
        app_name (str): The name of the application (must be at least 1 character).
        prefix (str, optional): An optional prefix to prepend.
        suffix (str, optional): An optional suffix to append.
        max_length (int, optional): The maximum length of the label string (default is 63).
        separator (str, optional): The separator between model_name and app_name (default is ".").

    Returns:
        str: The generated label string, at most 63 characters long.

    Raises:
        ValueError: If model_name or app_name is empty, or if the fixed label portion is too long.
    """
    hash_length = 6
    min_characters_per_truncatable_part = 1

    if not model_name or not app_name:
        raise ValueError("Both model_name and app_name must be at least 1 character long.")

    label = f"{prefix}{model_name}{separator}{app_name}{suffix}"
    if len(label) <= max_length:
        return label

    # If the un-truncated parts are too long, raise an error
    fixed_length = len(prefix) + len(suffix) + hash_length + 2  # 2 for the separators between model, app, and hash
    if fixed_length + 2 * min_characters_per_truncatable_part > max_length:
        raise ValueError(
            f"Fixed label portion (prefix, suffix, hash, and separator) is too long ({fixed_length} chars); "
            f"must leave at least 1 character each for model_name and app_name to fit within "
            f"the 63 character limit."
        )

    # Generate a short hash for uniqueness
    hash_digest = hashlib.sha1(f"{model_name}{separator}{app_name}".encode()).hexdigest()[:hash_length]

    available = max_length - fixed_length
    total = len(model_name) + len(app_name)
    model_len = max(min_characters_per_truncatable_part, int(available * len(model_name) / total))
    app_len = max(min_characters_per_truncatable_part, available - model_len)
    truncated_model = model_name[:model_len]
    truncated_app = app_name[:app_len]

    return f"{prefix}{truncated_model}{separator}{truncated_app}{separator}{hash_digest}{suffix}"
