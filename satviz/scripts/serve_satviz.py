#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2020 Debopam Bhattacherjee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import argparse
import errno
import functools
import http.server
import os
import shutil
import socketserver
import time
import webbrowser


class ReuseHTTPServer(http.server.HTTPServer):
    allow_reuse_address = True


class ReuseThreadingHTTPServer(socketserver.ThreadingMixIn, ReuseHTTPServer):
    daemon_threads = True


class SafeSimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """
    Retry transient read failures observed on some mounted filesystems.
    """

    def copyfile(self, source, outputfile):
        for attempt in range(5):
            try:
                shutil.copyfileobj(source, outputfile)
                return
            except OSError as exc:
                if exc.errno not in (errno.EAGAIN, getattr(errno, "EDEADLK", -1)):
                    raise
                if attempt == 4:
                    raise
                time.sleep(0.05 * (attempt + 1))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Serve SatViz output reliably, including workspaces with Errno 35 transient reads."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host/interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8081, help="Preferred bind port (default: 8081)")
    parser.add_argument(
        "--max-port-attempts",
        type=int,
        default=20,
        help="Number of consecutive ports to try if bind fails (default: 20)",
    )
    parser.add_argument(
        "--file",
        default="viz_output/Starlink.html",
        help="Path relative to satviz root to open (default: viz_output/Starlink.html)",
    )
    parser.add_argument("--open-browser", action="store_true", help="Open URL in default browser after start")
    parser.add_argument(
        "--threaded",
        action="store_true",
        help="Use one thread per request. Default is non-threaded for reliability.",
    )
    return parser.parse_args()


def bind_server(host, port, max_attempts, serve_dir, threaded):
    retry_errnos = {
        errno.EADDRINUSE,
        errno.EACCES,
        errno.EAGAIN,
        getattr(errno, "EDEADLK", -1),
    }
    handler = functools.partial(SafeSimpleHTTPRequestHandler, directory=serve_dir)
    server_cls = ReuseThreadingHTTPServer if threaded else ReuseHTTPServer
    last_exc = None
    for selected_port in range(port, port + max_attempts):
        try:
            return server_cls((host, selected_port), handler), selected_port
        except OSError as exc:
            last_exc = exc
            if exc.errno in retry_errnos:
                continue
            raise
    raise RuntimeError(
        "Failed to start server after ports "
        + str(port)
        + "-"
        + str(port + max_attempts - 1)
        + ". Last error: "
        + str(last_exc)
    ) from last_exc


def main():
    args = parse_args()
    satviz_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    target_rel = args.file.lstrip("/")
    target_abs = os.path.join(satviz_root, target_rel)

    if not os.path.exists(target_abs):
        raise FileNotFoundError("Target file not found: " + target_abs)

    server, bound_port = bind_server(
        args.host,
        args.port,
        args.max_port_attempts,
        satviz_root,
        args.threaded,
    )

    url = "http://" + args.host + ":" + str(bound_port) + "/" + target_rel
    print("Serving SatViz root:", satviz_root)
    print("Open:", url)
    print("Threaded mode:", "on" if args.threaded else "off")
    print("Press Ctrl+C to stop.")

    if args.open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("SatViz server stopped.")


if __name__ == "__main__":
    main()
