def test_package_exposes_version():
    import pepper

    assert pepper.__version__ == "0.1.0"
