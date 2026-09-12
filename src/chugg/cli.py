"""uv run chugg: build, serve, and regenerate the static application."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from chugg.build import ROOT, build, configured_base


def serve(directory: Path, base: str, host: str, port: int) -> None:
    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if base != "/" and path == base.rstrip("/"):
                self.send_response(302)
                self.send_header("Location", base)
                self.end_headers()
                return
            if not path.startswith(base):
                self.send_error(404)
                return
            self.path = "/" + self.path[len(base) :]
            super().do_GET()

        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-cache")
            super().end_headers()

    print(f"Chugg: http://{host}:{port}{base}", flush=True)
    server = ThreadingHTTPServer((host, port), partial(Handler, directory=str(directory)))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    for name, port in [("dev", 5173), ("preview", 4173)]:
        command = sub.add_parser(name)
        command.add_argument("--host", default="0.0.0.0")
        command.add_argument("--port", type=int, default=port)
    catalog = sub.add_parser("catalog-build")
    catalog.add_argument("paths", nargs="*", type=Path)
    sub.add_parser("icons-build")
    args = parser.parse_args()
    base = configured_base()
    match args.command:
        case "build":
            build(base=base)
        case "dev" | "preview":
            output = ROOT / "dist"
            if args.command == "dev":
                output = build(base=base)
                # Development previews deliberately do not register an offline worker.
                bootstrap = output / "bootstrap.js"
                bootstrap.write_text(bootstrap.read_text().replace("await registerOffline();", ""))
            elif not output.exists():
                parser.error("Run uv run chugg build before preview.")
            serve(output, base, args.host, args.port)
        case "catalog-build":
            from chugg.catalog_build import build_catalog

            build_catalog(args.paths)
        case "icons-build":
            from chugg.icons import build_icons

            build_icons()

        case _:
            parser.error("Unknown command")
