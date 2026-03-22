"""RTSP client implementation using libcurl (pycurl)."""

from __future__ import annotations

import logging
import os
import random
import time
from pathlib import Path
from typing import Optional, Tuple

import pycurl
from scanf import scanf

logger = logging.getLogger(__name__)

# Default user agent string
USER_AGENT = "MadYel RTSP"

# SDP file location alongside this module
_SDP_PATH = Path(__file__).resolve().parent / "file_tmp.sdp"

__all__ = ["RtspCurl", "Storage"]


def _random_port_pair(low: int = 49152, high: int = 65534) -> Tuple[int, int]:
    """Return a consecutive (even, odd) port pair in the ephemeral range."""
    port = random.randint(low, high - 1)
    if port % 2 != 0:
        port += 1
    return port, port + 1


class Storage:
    """Accumulate response data from pycurl callbacks."""

    def __init__(self) -> None:
        self.contents: str = ""
        self.line: int = 0

    def store(self, buf: bytes) -> None:
        self.line += 1
        self.contents = f"{self.contents}{self.line}: {buf.decode()}"

    def __str__(self) -> str:
        return self.contents


class RtspCurl:
    """RTSP client backed by libcurl.

    Example::

        client = RtspCurl()
        client.init("rtsp://camera.local/stream", "user:password")
        client.rtsp_options()
        client.auth()
        client.rtsp_describe()
        control = client.get_media_control_attribute()
        client.rtsp_setup(control)
        client.rtsp_play(client.url)
        time.sleep(60)
        client.rtsp_teardown()
        client.rtsp_curl_close()
    """

    def __init__(self, *, debug: bool = False, tcp: bool = False) -> None:
        """Create a new RtspCurl instance.

        Args:
            debug: Enable verbose curl logging.
            tcp: Use TCP transport; defaults to UDP.
        """
        self.debug = debug
        self.tcp = tcp
        self._curl: Optional[pycurl.Curl] = None
        self._sdp_file = None
        self._sdp_path = _SDP_PATH

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def init(self, url: str, user_pwd: str) -> None:
        """Initialise the curl handle and set common options.

        Args:
            url: RTSP stream URL (``rtsp://…``).
            user_pwd: Credentials in ``user:password`` format.
        """
        port_f, port_t = _random_port_pair()
        if self.tcp:
            transport = f"RTSP;unicast;client_port={port_f}-{port_t}"
        else:
            transport = f"RTP/AVP;unicast;client_port={port_f}-{port_t}"

        self._port_f = port_f
        self._port_t = port_t
        self.transport = transport
        self.url = url
        self.user_pwd = user_pwd

        self._curl = pycurl.Curl()
        if self.debug:
            self._curl.setopt(pycurl.VERBOSE, 1)
            self._curl.setopt(pycurl.NOPROGRESS, 1)

        self._curl.setopt(pycurl.USERAGENT, USER_AGENT)
        self._curl.setopt(pycurl.TCP_NODELAY, 0)
        self._curl.setopt(pycurl.URL, self.url)
        self._curl.setopt(pycurl.OPT_RTSP_STREAM_URI, self.url)
        logger.debug("RtspCurl initialised: url=%s ports=%d-%d", url, port_f, port_t)

    def auth(self) -> None:
        """Perform DIGEST authentication."""
        self._require_init()
        self._curl.setopt(pycurl.USERPWD, self.user_pwd)
        self._curl.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_DIGEST)
        self._curl.perform()

    def rtsp_describe(self) -> None:
        """Send RTSP DESCRIBE and write the returned SDP to disk."""
        self._require_init()
        self._sdp_file = open(self._sdp_path, "w+", encoding="utf-8")
        try:
            self._curl.setopt(pycurl.WRITEFUNCTION, self._write_sdp)
            self._curl.setopt(pycurl.OPT_RTSP_REQUEST, pycurl.RTSPREQ_DESCRIBE)
            self._curl.perform()
        finally:
            self._sdp_file.close()
            self._sdp_file = None

    def rtsp_options(self) -> None:
        """Send RTSP OPTIONS."""
        self._require_init()
        self._curl.setopt(pycurl.OPT_RTSP_REQUEST, pycurl.RTSPREQ_OPTIONS)
        self._curl.perform()

    def rtsp_setup(self, control: str) -> None:
        """Send RTSP SETUP for the given control track.

        Args:
            control: Track control identifier (e.g. ``trackID=1``).
        """
        self._require_init()
        uri = f"{self.url}/{control}"
        body = Storage()
        headers = Storage()
        self._curl.setopt(pycurl.OPT_RTSP_STREAM_URI, uri)
        self._curl.setopt(pycurl.OPT_RTSP_REQUEST, pycurl.RTSPREQ_SETUP)
        self._curl.setopt(pycurl.OPT_RTSP_TRANSPORT, self.transport)
        self._curl.setopt(pycurl.WRITEFUNCTION, body.store)
        self._curl.setopt(pycurl.HEADERFUNCTION, headers.store)
        self._curl.perform()
        logger.debug("SETUP body:\n%s", body)
        logger.debug("SETUP headers:\n%s", headers)

    def rtsp_play(self, url: str) -> None:
        """Send RTSP PLAY.

        Args:
            url: Stream URL (may differ from the base URL).
        """
        self._require_init()
        self._curl.setopt(pycurl.OPT_RTSP_STREAM_URI, url)
        self._curl.setopt(pycurl.RANGE, "npt=0.000-")
        self._curl.setopt(pycurl.OPT_RTSP_REQUEST, pycurl.RTSPREQ_PLAY)
        self._curl.perform()

    def rtsp_teardown(self) -> None:
        """Send RTSP TEARDOWN."""
        self._require_init()
        self._curl.setopt(pycurl.OPT_RTSP_REQUEST, pycurl.RTSPREQ_TEARDOWN)
        self._curl.perform()

    def rtsp_curl_close(self) -> None:
        """Close the underlying curl handle."""
        if self._curl is not None:
            self._curl.close()
            self._curl = None

    def get_media_control_attribute(self) -> str:
        """Parse the SDP file and return the first media-level control URI.

        Waits up to a few seconds for the SDP file to appear on disk.

        Returns:
            The control attribute value (e.g. ``trackID=1``).

        Raises:
            FileNotFoundError: If the SDP file is not found within the timeout.
            ValueError: If no media-level control attribute is present.
        """
        for _ in range(5):
            if self._sdp_path.exists():
                break
            time.sleep(1)
        else:
            raise FileNotFoundError(f"SDP file not found: {self._sdp_path}")

        controls: list[str] = []
        with open(self._sdp_path, encoding="utf-8") as fh:
            for line in fh:
                result = scanf("a=control:%s", line)
                if result is not None:
                    controls.append(result[0])

        # The first entry is typically the session-level wildcard ("*").
        # The second entry is the first media-level control attribute.
        if len(controls) < 2:
            raise ValueError("No media-level control attribute found in SDP.")
        return controls[1]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _require_init(self) -> None:
        if self._curl is None:
            raise RuntimeError("Call init() before using this method.")

    def _write_sdp(self, data: bytes) -> None:
        """pycurl WRITEFUNCTION callback — appends data to the SDP file."""
        if self._sdp_file is not None:
            self._sdp_file.write(data.decode("utf-8"))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    _url = "rtsp://10.10.100.180:554/test.mp4"
    client = RtspCurl(debug=True)
    client.init(_url, "admin:admin")
    client.rtsp_options()
    client.auth()
    client.rtsp_describe()
    _control = client.get_media_control_attribute()
    client.rtsp_setup(_control)
    client.rtsp_play(_url)
    logger.info("Streaming on ports %d-%d", client._port_f, client._port_t)
    time.sleep(60)
    client.rtsp_teardown()
    client.rtsp_curl_close()
