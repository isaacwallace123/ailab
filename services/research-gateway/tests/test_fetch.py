import pytest
from ailab_research_gateway.fetch import (
    FetchPolicyError,
    extract_readable_text,
    normalize_public_url,
    require_public_ip,
    safe_filename,
)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://user:secret@example.com/",
        "http://127.0.0.1/",
        "http://[::1]/",
        "http://169.254.169.254/latest/meta-data/",
        "http://192.168.0.221:8080/",
        "https://example.com:8443/",
    ],
)
def test_normalize_public_url_rejects_unsafe_destinations(url: str) -> None:
    with pytest.raises(FetchPolicyError):
        normalize_public_url(url)


def test_normalize_public_url_accepts_public_https() -> None:
    assert normalize_public_url("HTTPS://Example.COM/path?q=1#fragment") == (
        "https://example.com/path?q=1"
    )


@pytest.mark.parametrize("address", ["10.0.0.1", "100.64.0.1", "192.0.2.1", "fc00::1"])
def test_require_public_ip_rejects_non_global_ranges(address: str) -> None:
    with pytest.raises(FetchPolicyError):
        require_public_ip(address)


def test_html_extraction_removes_active_content() -> None:
    title, text = extract_readable_text(
        b"<html><head><title>Report</title><script>steal()</script></head>"
        b"<body><h1>Revenue</h1><p>Up 12 percent.</p></body></html>",
        "text/html",
        1000,
    )
    assert title == "Report"
    assert "Revenue" in text
    assert "Up 12 percent." in text
    assert "steal" not in text


def test_safe_filename_adds_a_content_extension() -> None:
    assert safe_filename("https://example.com/reports/latest", "application/pdf") == "latest.pdf"
