"""Unit tests for madyel.rtsp_curl (no live RTSP server required)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from madyel import RtspCurl, Storage, __version__

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------


class TestVersion:
    def test_version_string(self):
        assert isinstance(__version__, str)
        parts = __version__.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


class TestStorage:
    def test_empty(self):
        s = Storage()
        assert str(s) == ""
        assert s.line == 0

    def test_single_store(self):
        s = Storage()
        s.store(b"hello\n")
        assert s.line == 1
        assert "hello" in str(s)

    def test_multiple_stores(self):
        s = Storage()
        s.store(b"line1\n")
        s.store(b"line2\n")
        assert s.line == 2
        text = str(s)
        assert "line1" in text
        assert "line2" in text


# ---------------------------------------------------------------------------
# RtspCurl — initialisation
# ---------------------------------------------------------------------------


class TestRtspCurlInit:
    def test_requires_init_before_methods(self):
        client = RtspCurl()
        with pytest.raises(RuntimeError, match="init()"):
            client.auth()

    def test_requires_init_before_options(self):
        client = RtspCurl()
        with pytest.raises(RuntimeError, match="init()"):
            client.rtsp_options()

    @patch("madyel.rtsp_curl.pycurl.Curl")
    def test_init_sets_url(self, MockCurl):
        mock_curl = MagicMock()
        MockCurl.return_value = mock_curl

        client = RtspCurl()
        client.init("rtsp://192.0.2.1/stream", "user:pass")

        assert client.url == "rtsp://192.0.2.1/stream"
        assert client.user_pwd == "user:pass"

    @patch("madyel.rtsp_curl.pycurl.Curl")
    def test_init_allocates_even_port_pair(self, MockCurl):
        MockCurl.return_value = MagicMock()
        client = RtspCurl()
        client.init("rtsp://192.0.2.1/stream", "user:pass")
        assert client._port_f % 2 == 0
        assert client._port_t == client._port_f + 1

    @patch("madyel.rtsp_curl.pycurl.Curl")
    def test_init_udp_transport(self, MockCurl):
        MockCurl.return_value = MagicMock()
        client = RtspCurl(tcp=False)
        client.init("rtsp://192.0.2.1/stream", "user:pass")
        assert client.transport.startswith("RTP/AVP")

    @patch("madyel.rtsp_curl.pycurl.Curl")
    def test_init_tcp_transport(self, MockCurl):
        MockCurl.return_value = MagicMock()
        client = RtspCurl(tcp=True)
        client.init("rtsp://192.0.2.1/stream", "user:pass")
        assert client.transport.startswith("RTSP")

    @patch("madyel.rtsp_curl.pycurl.Curl")
    def test_close_clears_handle(self, MockCurl):
        mock_curl = MagicMock()
        MockCurl.return_value = mock_curl
        client = RtspCurl()
        client.init("rtsp://192.0.2.1/stream", "user:pass")
        client.rtsp_curl_close()
        assert client._curl is None
        mock_curl.close.assert_called_once()

    def test_double_close_is_safe(self):
        client = RtspCurl()
        client.rtsp_curl_close()  # never initialised — should not raise


# ---------------------------------------------------------------------------
# RtspCurl — SDP parsing
# ---------------------------------------------------------------------------


class TestGetMediaControlAttribute:
    def _make_client_with_sdp(self, sdp_content: str) -> RtspCurl:
        client = RtspCurl()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sdp", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(sdp_content)
            client._sdp_path = Path(fh.name)
        return client

    def teardown_method(self, _method):
        # Clean up any temp files created during the test
        pass

    def test_returns_media_control(self):
        sdp = (
            "v=0\n"
            "o=- 0 0 IN IP4 127.0.0.1\n"
            "s=Test\n"
            "a=control:*\n"
            "m=video 0 RTP/AVP 96\n"
            "a=control:trackID=1\n"
        )
        client = self._make_client_with_sdp(sdp)
        try:
            assert client.get_media_control_attribute() == "trackID=1"
        finally:
            os.unlink(client._sdp_path)

    def test_raises_when_only_session_control(self):
        sdp = "a=control:*\n"
        client = self._make_client_with_sdp(sdp)
        try:
            with pytest.raises(ValueError, match="No media-level"):
                client.get_media_control_attribute()
        finally:
            os.unlink(client._sdp_path)

    def test_raises_when_sdp_missing(self):
        client = RtspCurl()
        client._sdp_path = Path("/nonexistent/no_such_file.sdp")
        with pytest.raises(FileNotFoundError):
            client.get_media_control_attribute()


# ---------------------------------------------------------------------------
# RtspCurl — write SDP callback
# ---------------------------------------------------------------------------


class TestWriteSdp:
    def test_write_sdp_writes_to_open_file(self):
        client = RtspCurl()
        mock_file = MagicMock()
        client._sdp_file = mock_file
        client._write_sdp(b"v=0\n")
        mock_file.write.assert_called_once_with("v=0\n")

    def test_write_sdp_no_file_does_not_raise(self):
        client = RtspCurl()
        client._sdp_file = None
        client._write_sdp(b"v=0\n")  # should be a no-op
