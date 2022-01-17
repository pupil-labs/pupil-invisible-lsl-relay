import pupil_labs.invisible_lsl_relay as this_project


def test_package_metadata() -> None:
    assert hasattr(this_project, "__version__")
    assert hasattr(this_project, "__version_info__")
