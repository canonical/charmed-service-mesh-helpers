"""Helpers for generating and managing Kubernetes labels."""

import hashlib
from typing import Optional


def charm_kubernetes_label(model_name: str, app_name: str, suffix: Optional[str] = None) -> str:
    """Generate a Kubernetes label string in the form "{model_name}-{app_name}-{suffix}".

    If the label exceeds 63 characters, truncate model_name and app_name, and append a hash of model_name-app_name to the end
    ensure uniqueness. The hash is only included if truncation occurs.

    Args:
        model_name (str): The name of the model (must be at least 1 character).
        app_name (str): The name of the application (must be at least 1 character).
        suffix (str, optional): An optional suffix to append.  If omitted, there will be no trailing "-" on the label

    Returns:
        str: The generated label string, at most 63 characters long.

    Raises:
        ValueError: If model_name or app_name is empty, or if the fixed label portion is too long.
    """
    if not model_name or not app_name:
        raise ValueError("Both model_name and app_name must be at least 1 character long.")

    if suffix:
        label = f"{model_name}-{app_name}-{suffix}"
        base = label
    else:
        label = f"{model_name}-{app_name}"
        base = label

    max_length = 63
    if len(label) <= max_length:
        return label

    # Generate a short hash for uniqueness
    hash_digest = hashlib.sha1(base.encode()).hexdigest()[:6]
    # Reserve space for hash and dashes
    if suffix:
        fixed_length = len(suffix) + len(hash_digest) + 3  # 3 dashes
    else:
        fixed_length = len(hash_digest) + 2  # 2 dashes

    # Leave at least 1 character for each of truncated_model and truncated_app
    min_variable_length = 2
    if fixed_length + min_variable_length > max_length:
        raise ValueError(
            f"Fixed label portion (dashes, suffix, hash) is too long ({fixed_length} chars); "
            f"must leave at least 1 character each for model_name and app_name to fit within "
            f"the 63 character limit."
        )

    available = max_length - fixed_length
    total = len(model_name) + len(app_name)
    model_len = max(1, int(available * len(model_name) / total))
    app_len = max(1, available - model_len)
    truncated_model = model_name[:model_len]
    truncated_app = app_name[:app_len]

    if suffix:
        return f"{truncated_model}-{truncated_app}-{suffix}-{hash_digest}"
    else:
        return f"{truncated_model}-{truncated_app}-{hash_digest}"
