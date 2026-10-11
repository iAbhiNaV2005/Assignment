import pytest
from agent.netsafe import SSRFValidationError, validate_url_safety, is_safe_ip


def test_rejects_non_http_scheme():
    with pytest.raises(SSRFValidationError, match="Invalid URL scheme"):
        validate_url_safety("ftp://example.com/file.txt")

    with pytest.raises(SSRFValidationError, match="Invalid URL scheme"):
        validate_url_safety("file:///etc/passwd")


def test_rejects_localhost():
    with pytest.raises(SSRFValidationError, match="Forbidden host"):
        validate_url_safety("http://localhost:8000")

    with pytest.raises(SSRFValidationError, match="Forbidden host"):
        validate_url_safety("http://127.0.0.1:3000")


def test_is_safe_ip_blocks_private_ranges():
    assert is_safe_ip("127.0.0.1") is False
    assert is_safe_ip("10.0.0.1") is False
    assert is_safe_ip("172.16.0.1") is False
    assert is_safe_ip("192.168.1.1") is False
    assert is_safe_ip("169.254.169.254") is False  # AWS metadata IP
    assert is_safe_ip("::1") is False

    # Public IPs should be safe
    assert is_safe_ip("8.8.8.8") is True
    assert is_safe_ip("1.1.1.1") is True
    assert is_safe_ip("104.26.10.1") is True
