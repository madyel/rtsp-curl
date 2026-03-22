# rtsp-curl

[![PyPI version](https://img.shields.io/pypi/v/rtsp-curl-mad.svg)](https://pypi.org/project/rtsp-curl-mad/)
[![Python](https://img.shields.io/pypi/pyversions/rtsp-curl-mad.svg)](https://pypi.org/project/rtsp-curl-mad/)
[![License](https://img.shields.io/github/license/madyel/rtsp-curl.svg)](LICENSE)
[![CI](https://github.com/madyel/rtsp-curl/actions/workflows/ci.yml/badge.svg)](https://github.com/madyel/rtsp-curl/actions/workflows/ci.yml)

Python RTSP client built on [libcurl](https://curl.haxx.se/libcurl/c/rtsp.html) via [pycurl](https://pypi.org/project/pycurl/).
Supports OPTIONS / DESCRIBE / SETUP / PLAY / TEARDOWN over UDP (default) or TCP.

---

## Requirements

- Python 3.9+
- libcurl with RTSP support (`curl --version | grep rtsp`)
- `pycurl >= 7.45.0`

---

## Installation

```bash
pip install rtsp-curl-mad
```

**macOS** (custom OpenSSL required by pycurl):

```bash
PYCURL_SSL_LIBRARY=openssl \
  LDFLAGS="-L/usr/local/opt/openssl/lib" \
  CPPFLAGS="-I/usr/local/opt/openssl/include" \
  pip install --no-cache-dir pycurl

pip install rtsp-curl-mad
```

---

## Quick start

```python
import time
from madyel import RtspCurl

URL = "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov"

client = RtspCurl()
client.init(URL, "user:password")

client.rtsp_options()
client.auth()
client.rtsp_describe()

control = client.get_media_control_attribute()
client.rtsp_setup(control)
client.rtsp_play(URL)

time.sleep(10)          # stream for 10 seconds

client.rtsp_teardown()
client.rtsp_curl_close()
```

---

## API reference

### `RtspCurl(*, debug=False, tcp=False)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `debug`   | bool | `False` | Enable verbose curl logging |
| `tcp`     | bool | `False` | Use TCP transport instead of UDP |

#### Methods

| Method | Description |
|--------|-------------|
| `init(url, user_pwd)` | Initialise the curl handle. Must be called first. `user_pwd` format: `"user:password"` |
| `rtsp_options()` | Send RTSP OPTIONS |
| `auth()` | Perform DIGEST authentication |
| `rtsp_describe()` | Send RTSP DESCRIBE and save the SDP response to disk |
| `get_media_control_attribute()` | Parse the SDP and return the first media-level `a=control` value |
| `rtsp_setup(control)` | Send RTSP SETUP for the given track control URI |
| `rtsp_play(url)` | Send RTSP PLAY |
| `rtsp_teardown()` | Send RTSP TEARDOWN |
| `rtsp_curl_close()` | Close the underlying curl handle |

### `Storage`

Helper that accumulates pycurl callback data line by line.

```python
from madyel import Storage

buf = Storage()
# pass buf.store as pycurl WRITEFUNCTION / HEADERFUNCTION
print(buf)   # all accumulated lines
```

---

## Options

**Debug mode** — enables `pycurl.VERBOSE` (full headers and timing on stderr):

```python
client = RtspCurl(debug=True)
```

**TCP transport** — by default the client negotiates RTP over UDP:

```python
client = RtspCurl(tcp=True)
```

---

## Publishing a new release

Tag the commit — GitHub Actions builds and uploads to PyPI automatically:

```bash
git tag v0.9.1
git push origin v0.9.1
```

> One-time setup: configure the PyPI Trusted Publisher at
> https://pypi.org/manage/project/rtsp-curl-mad/settings/publishing/

---

## License

[MIT](LICENSE)
