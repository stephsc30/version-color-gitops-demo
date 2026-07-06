import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer


VERSION = os.getenv("APP_VERSION", "v3")
APP_NAME = os.getenv("APP_NAME", "GitOps Version Color Demo")
PORT = int(os.getenv("PORT", "8080"))


def color_for(version):
    digest = hashlib.sha256(version.encode("utf-8")).hexdigest()
    hue = int(digest[:2], 16) * 360 // 255
    return f"hsl({hue}, 80%, 45%)"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ["/healthz", "/readyz"]:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return

        color = color_for(VERSION)
        pod = os.getenv("HOSTNAME", "local")

        if self.path == "/api/version":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "app": APP_NAME,
                        "version": VERSION,
                        "pod": pod,
                        "color": color,
                    }
                ).encode("utf-8")
            )
            return

        html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{APP_NAME} {VERSION}</title>
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      font-family: Arial, Helvetica, sans-serif;
      color: #111827;
      background: {color};
    }}
    main {{
      width: min(720px, calc(100vw - 32px));
      padding: 40px 28px;
      background: rgba(255, 255, 255, 0.94);
      border: 1px solid rgba(17, 24, 39, 0.18);
      border-radius: 8px;
      text-align: center;
      box-shadow: 0 24px 80px rgba(17, 24, 39, 0.28);
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: clamp(44px, 10vw, 92px);
      letter-spacing: 0;
    }}
    p {{
      margin: 10px 0;
      font-size: 18px;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 42px;
      margin-top: 16px;
      padding: 0 18px;
      border-radius: 999px;
      color: white;
      background: {color};
      font-weight: 700;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{VERSION}</h1>
    <p>{APP_NAME}</p>
    <p>Pod: {pod}</p>
    <div class="badge">Image tag {VERSION}</div>
  </main>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    print(f"Starting {APP_NAME} {VERSION} on port {PORT}")
    HTTPServer(("", PORT), Handler).serve_forever()
