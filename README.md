#### rtsp-curl — Python RTSP client built on libcurl

![](https://img.shields.io/github/license/madyel/rtsp-curl.svg)
![](https://img.shields.io/github/last-commit/madyel/rtsp-curl.svg)
![](https://img.shields.io/pypi/v/rtsp-curl.svg)

A Python RTSP client ported from [rtsp.c][1] using [pycurl](https://pypi.org/project/pycurl/).

---

### Install

```
pip install rtsp-curl
```

<em>macOS (custom OpenSSL):</em>

```
PYCURL_SSL_LIBRARY=openssl \
  LDFLAGS="-L/usr/local/opt/openssl/lib" \
  CPPFLAGS="-I/usr/local/opt/openssl/include" \
  pip install --no-cache-dir pycurl
pip install rtsp-curl
```

---

### Example

```python
import time
from madyel import RtspCurl

stream_uri = 'rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov'

client = RtspCurl()
client.init(stream_uri, 'username:password')
client.rtsp_options()
client.auth()
client.rtsp_describe()
control = client.get_media_control_attribute()
client.rtsp_setup(control)
client.rtsp_play(stream_uri)

time.sleep(5)

client.rtsp_teardown()
client.rtsp_curl_close()
```

---

### Publish a new version to PyPI

Tag the release — GitHub Actions handles the rest:

```bash
git tag v0.9.1
git push origin v0.9.1
```

> Configure the PyPI Trusted Publisher once at:
> https://pypi.org/manage/project/rtsp-curl/settings/publishing/

[1]: https://curl.haxx.se/libcurl/c/rtsp.html
