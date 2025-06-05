import pytest

from charmed_service_mesh_helpers import charm_kubernetes_label


@pytest.mark.parametrize(
    "model_name, app_name, suffix, expected",
    [
        ("model", "app", None, "model-app"),
        ("model", "app", "svc", "model-app-svc"),
        # Not truncated
        (
            "m" * 31,
            "a" * 31,
            None,
            f"{'m'*31}-{'a'*31}",
        ),
        # Needs truncation
        (
            "m" * 32,
            "a" * 31,
            None,
            "mmmmmmmmmmmmmmmmmmmmmmmmmmm-aaaaaaaaaaaaaaaaaaaaaaaaaaaa-6014d8",
        ),
        # Needs truncation
        (
                "m" * 33,
                "a" * 31,
                None,
                "mmmmmmmmmmmmmmmmmmmmmmmmmmmm-aaaaaaaaaaaaaaaaaaaaaaaaaaa-928fe5",
        ),
        # Needs truncation with suffix
        (
            "m" * 40,
            "a" * 40,
            "suffix",
            "mmmmmmmmmmmmmmmmmmmmmmmm-aaaaaaaaaaaaaaaaaaaaaaaa-suffix-cce1b8",
        ),
    ],
)
def test_generate_label_cases(model_name, app_name, suffix, expected):
    if suffix is not None:
        label = charm_kubernetes_label(model_name, app_name, suffix)
    else:
        label = charm_kubernetes_label(model_name, app_name)
    assert label == expected
    assert len(label) <= 63


def test_truncated_labels_are_unique():
    # These would truncate to the same prefix, but should have different hashes
    label1 = charm_kubernetes_label("m" * 100, "a" * 100)
    label2 = charm_kubernetes_label("m" * 90, "a" * 90)
    assert label1 != label2
    assert len(label1) <= 63
    assert len(label2) <= 63


def test_error_on_empty_model_or_app():
    with pytest.raises(ValueError):
        charm_kubernetes_label("", "app")
    with pytest.raises(ValueError):
        charm_kubernetes_label("model", "")


@pytest.mark.parametrize(
    "model_name, app_name, suffix",
    [
        ("m", "a", "s" * 60),           # Suffix so long that only 1 char left for model/app
        ("m" * 60, "a", "s" * 53),      # Suffix + hash so long that only 1 char left for model/app
    ],
)
def test_error_on_fixed_length_too_long_cases(model_name, app_name, suffix):
    with pytest.raises(ValueError):
        charm_kubernetes_label(model_name, app_name, suffix)
