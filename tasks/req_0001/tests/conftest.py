try:
    from http.server import HTTPServer, SimpleHTTPRequestHandler
except ImportError:
    from BaseHTTPServer import HTTPServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler

import ssl
import threading

import pytest

from requests.compat import urljoin


def prepare_url(value):
    # Issue #1483: Make sure the URL always has a trailing slash
    httpbin_url = value.url.rstrip("/") + "/"

    def inner(*suffix):
        return urljoin(httpbin_url, "/".join(suffix))

    return inner


@pytest.fixture
def httpbin(httpbin):
    return prepare_url(httpbin)


@pytest.fixture
def httpbin_secure(httpbin_secure):
    return prepare_url(httpbin_secure)


@pytest.fixture
def nosan_server(tmp_path_factory):
    # delay importing until the fixture in order to make it possible
    # to deselect the test via command-line when trustme is not available
    import trustme

    tmpdir = tmp_path_factory.mktemp("certs")
    ca = trustme.CA()
    # only commonName, no subjectAltName
    server_cert = ca.issue_cert(common_name="localhost")
    ca_bundle = str(tmpdir / "ca.pem")
    ca.cert_pem.write_to_path(ca_bundle)

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    server_cert.configure_cert(context)
    server = HTTPServer(("localhost", 0), SimpleHTTPRequestHandler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()

    yield "localhost", server.server_address[1], ca_bundle

    server.shutdown()
    server_thread.join()


# ===== 隐藏测试的入口 =====
# 模型调 run_tests 时只跑这两条相关测试（含它们的全部参数组合）。
# tests_hidden/ 里是完整的一套，只有 harness 的判据会跑，模型看不到。
_VISIBLE = {
    "test_content_type_parsing",
    "test_get_encoding_from_headers",
}


def pytest_collection_modifyitems(config, items):
    items[:] = [i for i in items if i.originalname in _VISIBLE]
