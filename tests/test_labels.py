import pytest

from charmed_service_mesh_helpers import charm_kubernetes_label


@pytest.mark.parametrize(
    "model_name, app_name, prefix, suffix, expected",
    [
        ("model", "app", "", "", "model.app"),
        ("model", "app", "prefix/", "-suffix", "prefix/model.app-suffix"),
        # Not truncated
        (
            "m" * 31,
            "a" * 31,
            "",
            "",
            f"{'m'*31}.{'a'*31}",
        ),
        # Needs truncation
        (
            "m" * 32,
            "a" * 31,
            "",
            "",
            "mmmmmmmmmmmmmmmmmmmmmmmmmmm.aaaaaaaaaaaaaaaaaaaaaaaaaaaa.c4949d",
        ),
        # Needs truncation
        (
            "m" * 33,
            "a" * 31,
            "",
            "",
            "mmmmmmmmmmmmmmmmmmmmmmmmmmmm.aaaaaaaaaaaaaaaaaaaaaaaaaaa.a4e680",
        ),
        # Needs truncation with prefix and suffix
        (
            "m" * 40,
            "a" * 40,
            "prefix/",
            "-suffix",
            "prefix/mmmmmmmmmmmmmmmmmmmm.aaaaaaaaaaaaaaaaaaaaa.499dc0-suffix",
        ),
    ],
)
def test_generate_label_cases(model_name, app_name, prefix, suffix, expected):
    label = charm_kubernetes_label(model_name, app_name, prefix, suffix)
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
    "model_name, app_name, prefix, suffix",
    [
        ("m", "a", "", "s" * 61),           # Suffix so long that only 1 char left for model/app
        ("m" * 60, "a", "", "s" * 54),      # Suffix + hash so long that only 1 char left for model/app
        ("m" * 60, "a", "p"*20, "s" * 34),  # Suffix + prefix + hash so long that only 1 char left for model/app
    ],
)
def test_error_on_fixed_length_too_long_cases(model_name, app_name, prefix, suffix):
    with pytest.raises(ValueError):
        charm_kubernetes_label(model_name, app_name, prefix, suffix)
