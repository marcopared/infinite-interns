import infinite_interns


def test_package_has_version() -> None:
    assert getattr(infinite_interns, "__version__", None) == "0.1.0"
