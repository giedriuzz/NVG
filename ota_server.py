"""
Lightweight Wi-Fi Access Point (AP) Web OTA Updater for ESP32-C3 (MicroPython).
Starts a local Wi-Fi hotspot and serves a dark-mode web interface at http://192.168.4.1
for uploading, backing up, validating, and updating MicroPython files without internet.
"""

import network
import socket
import os
import gc
import time
import machine

HTML_PAGE = """<!DOCTYPE html>
<html lang="lt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NVG OTA Atnaujinimas</title>
<style>
  :root { --bg:#0d1117; --card:#161b22; --border:#30363d; --accent:#2ea043; --text:#e6edf3; --muted:#8b949e; --danger:#f85149; }
  * { box-sizing:border-box; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  body { margin:0; padding:16px; background:var(--bg); color:var(--text); max-width:600px; margin-inline:auto; }
  h1 { font-size:1.25rem; margin:0 0 4px 0; color:#58a6ff; }
  .sub { font-size:0.85rem; color:var(--muted); margin-bottom:16px; }
  .card { background:var(--card); border:1px solid var(--border); border-radius:8px; padding:14px; margin-bottom:14px; }
  .stats { display:flex; gap:12px; font-size:0.88rem; flex-wrap:wrap; }
  .stat { background:#21262d; padding:6px 10px; border-radius:6px; }
  .btn { display:inline-block; background:var(--accent); color:#fff; border:none; padding:10px 16px; border-radius:6px; font-weight:600; cursor:pointer; font-size:0.92rem; text-decoration:none; }
  .btn:disabled { opacity:0.5; cursor:not-allowed; }
  .btn-reboot { background:#d29922; width:100%; margin-top:6px; }
  input[type="file"] { display:block; width:100%; margin:10px 0; padding:8px; background:#0d1117; border:1px dashed var(--border); border-radius:6px; color:var(--text); }
  table { width:100%; border-collapse:collapse; font-size:0.88rem; margin-top:8px; }
  th, td { text-align:left; padding:7px 6px; border-bottom:1px solid var(--border); }
  th { color:var(--muted); font-weight:500; }
  a.dl { color:#58a6ff; text-decoration:none; }
  #log { font-family:monospace; font-size:0.82rem; white-space:pre-wrap; margin-top:10px; padding:8px; background:#0d1117; border-radius:6px; display:none; }
</style>
</head>
<body>
  <h1>NVG Valdiklio OTA Atnaujinimas</h1>
  <div class="sub">ESP32-C3 vietinis atnaujinimo serveris (192.168.4.1)</div>

  <div class="card">
    <div class="stats">
      <div class="stat">🔋 Baterija: <b>__BAT_V__</b></div>
      <div class="stat">💾 Laisva vieta: <b>__FREE_KB__ KB</b></div>
    </div>
  </div>

  <div class="card">
    <b>1. Įkelti atnaujintus failus (.py, .md)</b>
    <input type="file" id="files" multiple accept=".py,.md,.json,.txt">
    <button class="btn" id="upBtn" onclick="uploadFiles()">Įkelti į ESP32-C3</button>
    <div id="log"></div>
  </div>

  <div class="card">
    <b>2. Esami failai įrenginyje</b>
    <table>
      <thead><tr><th>Failas</th><th>Dydis</th><th>Veiksmas</th></tr></thead>
      <tbody>__FILE_ROWS__</tbody>
    </table>
  </div>

  <div class="card">
    <b>3. Baigus atnaujinimą</b>
    <button class="btn btn-reboot" onclick="rebootDevice()">Perkrauti įrenginį (Grįžti į darbo režimą)</button>
  </div>

<script>
function logMsg(msg, isErr) {
  const el = document.getElementById('log');
  el.style.display = 'block';
  el.style.color = isErr ? '#f85149' : '#7ee787';
  el.textContent += msg + '\\n';
}

async function uploadFiles() {
  const input = document.getElementById('files');
  const btn = document.getElementById('upBtn');
  if (!input.files.length) { alert('Pasirinkite bent vieną failą!'); return; }
  document.getElementById('log').textContent = '';
  btn.disabled = true;

  for (const file of input.files) {
    logMsg('⏳ Įkeliama: ' + file.name + ' (' + file.size + ' B)...', false);
    try {
      const buf = await file.arrayBuffer();
      const res = await fetch('/upload?name=' + encodeURIComponent(file.name), {
        method: 'POST',
        headers: {'Content-Type': 'application/octet-stream'},
        body: buf
      });
      const txt = await res.text();
      if (res.ok) {
        logMsg('✅ ' + file.name + ': ' + txt, false);
      } else {
        logMsg('❌ Klaida (' + file.name + '): ' + txt, true);
      }
    } catch (e) {
      logMsg('❌ Ryšio klaida (' + file.name + '): ' + e, true);
    }
  }
  btn.disabled = false;
  setTimeout(() => location.reload(), 1200);
}

async function rebootDevice() {
  if (!confirm('Perkrauti ESP32-C3 ir išjungti Wi-Fi?')) return;
  try {
    await fetch('/reboot', {method: 'POST'});
  } catch (e) {}
  document.body.innerHTML = '<div class="card" style="margin-top:40px;text-align:center;"><h2>✅ Įrenginys perkraunamas...</h2><p>Wi-Fi išjungtas. NVG valdiklis grįžo į įprastą darbo režimą.</p></div>';
}
</script>
</body>
</html>
"""


def _url_decode(s: str) -> str:
    res = ""
    i = 0
    while i < len(s):
        if s[i] == "%" and i + 2 < len(s):
            try:
                res += chr(int(s[i + 1 : i + 3], 16))
                i += 3
                continue
            except ValueError:
                pass
        elif s[i] == "+":
            res += " "
            i += 1
            continue
        res += s[i]
        i += 1
    return res


def _sanitize_filename(name: str) -> str:
    name = _url_decode(name).strip().replace("\\", "/")
    if "/" in name:
        name = name.split("/")[-1]
    # Prevent hidden or path-traversal filenames
    if not name or name.startswith(".") or ".." in name:
        return ""
    return name


def _get_free_kb() -> int:
    try:
        st = os.statvfs("/")
        return (st[0] * st[3]) // 1024
    except Exception:
        return 0


def _build_file_rows() -> str:
    rows = []
    try:
        files = sorted(os.listdir("/"))
        for f in files:
            try:
                st = os.stat("/" + f)
                # st[0] & 0x4000 checks if directory
                if not (st[0] & 0x4000):
                    size = st[6]
                    rows.append(
                        f'<tr><td><b>{f}</b></td><td>{size} B</td>'
                        f'<td><a class="dl" href="/download?name={f}" download="{f}">Atsisiųsti</a></td></tr>'
                    )
            except Exception:
                pass
    except Exception:
        pass
    return "".join(rows) if rows else '<tr><td colspan="3">Failų nerasta</td></tr>'


def _send_response(conn, status="200 OK", content_type="text/plain; charset=utf-8", body=b""):
    if isinstance(body, str):
        body = body.encode("utf-8")
    header = (
        f"HTTP/1.1 {status}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n\r\n"
    )
    conn.sendall(header.encode("utf-8"))
    if body:
        conn.sendall(body)


def disable_wifi():
    """Ensures both STA and AP Wi-Fi interfaces are completely turned off to save battery."""
    try:
        ap = network.WLAN(network.AP_IF)
        ap.active(False)
    except Exception:
        pass
    try:
        sta = network.WLAN(network.STA_IF)
        sta.active(False)
    except Exception:
        pass


def run_ota_portal(ssid="NVG-OTA", password="nvgupdate", set_led_duty=None, read_battery_fn=None, debug=False):
    """
    Starts the Wi-Fi AP and blocking HTTP OTA server loop with non-blocking LED heartbeat.
    Reboots the device when requested via the web UI.
    """
    gc.collect()
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    if password and len(password) >= 8:
        ap.config(essid=ssid, password=password, authmode=network.AUTH_WPA_WPA2_PSK)
    else:
        ap.config(essid=ssid, authmode=network.AUTH_OPEN)

    if debug:
        ip = ap.ifconfig()[0]
        print(f"[OTA] AP '{ssid}' started at http://{ip}")

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", 80))
    srv.listen(2)
    srv.settimeout(0.05)  # Non-blocking accept for LED heartbeat animation

    should_reboot = False

    try:
        while not should_reboot:
            # Distinct double-blink heartbeat on Status LED while in OTA mode
            if set_led_duty:
                phase = time.ticks_ms() % 1200
                if phase < 80 or (180 <= phase < 260):
                    set_led_duty(50000)
                else:
                    set_led_duty(0)

            try:
                conn, addr = srv.accept()
            except OSError:
                continue

            try:
                conn.settimeout(5.0)
                req_data = b""
                while b"\r\n\r\n" not in req_data and len(req_data) < 2048:
                    chunk = conn.recv(512)
                    if not chunk:
                        break
                    req_data += chunk

                if not req_data:
                    conn.close()
                    continue

                header_part, body_initial = req_data.split(b"\r\n\r\n", 1)
                lines = header_part.decode("utf-8", "ignore").split("\r\n")
                req_line = lines[0].split(" ")
                method = req_line[0] if len(req_line) > 0 else "GET"
                path = req_line[1] if len(req_line) > 1 else "/"

                content_length = 0
                for line in lines[1:]:
                    if line.lower().startswith("content-length:"):
                        content_length = int(line.split(":", 1)[1].strip())

                if method == "GET" and (path == "/" or path.startswith("/index")):
                    bat_str = "N/A"
                    if read_battery_fn:
                        v = read_battery_fn()
                        bat_str = f"{v:.2f} V" if v >= 1.0 else "USB / Neprijungta"
                    html = (
                        HTML_PAGE.replace("__BAT_V__", bat_str)
                        .replace("__FREE_KB__", str(_get_free_kb()))
                        .replace("__FILE_ROWS__", _build_file_rows())
                    )
                    _send_response(conn, "200 OK", "text/html; charset=utf-8", html)

                elif method == "GET" and path.startswith("/download?name="):
                    raw_name = path.split("name=", 1)[1].split("&")[0]
                    fname = _sanitize_filename(raw_name)
                    if fname and fname in os.listdir("/"):
                        st = os.stat("/" + fname)
                        fsize = st[6]
                        header = (
                            f"HTTP/1.1 200 OK\r\n"
                            f"Content-Type: application/octet-stream\r\n"
                            f"Content-Disposition: attachment; filename=\"{fname}\"\r\n"
                            f"Content-Length: {fsize}\r\n"
                            f"Connection: close\r\n\r\n"
                        )
                        conn.sendall(header.encode("utf-8"))
                        with open("/" + fname, "rb") as f:
                            while True:
                                buf = f.read(512)
                                if not buf:
                                    break
                                conn.sendall(buf)
                    else:
                        _send_response(conn, "404 Not Found", body="Failas nerastas")

                elif method == "POST" and path.startswith("/upload?name="):
                    raw_name = path.split("name=", 1)[1].split("&")[0]
                    fname = _sanitize_filename(raw_name)
                    if not fname:
                        _send_response(conn, "400 Bad Request", body="Netinkamas failo pavadinimas")
                    elif content_length <= 0 or content_length > 250_000:
                        _send_response(conn, "400 Bad Request", body="Netinkamas failo dydis")
                    else:
                        tmp_name = "/_ota_tmp_" + fname
                        written = 0
                        with open(tmp_name, "wb") as f:
                            if body_initial:
                                f.write(body_initial)
                                written += len(body_initial)
                            while written < content_length:
                                chunk = conn.recv(min(1024, content_length - written))
                                if not chunk:
                                    break
                                f.write(chunk)
                                written += len(chunk)

                        if written != content_length:
                            try:
                                os.remove(tmp_name)
                            except Exception:
                                pass
                            _send_response(conn, "400 Bad Request", body="Nepavyko pilnai priimti failo")
                        else:
                            # Validate Python syntax before overwriting if it's a .py file
                            syntax_ok = True
                            err_msg = ""
                            if fname.endswith(".py"):
                                try:
                                    gc.collect()
                                    with open(tmp_name, "r") as f:
                                        src = f.read()
                                    compile(src, fname, "exec")
                                    src = None
                                    gc.collect()
                                except SyntaxError as se:
                                    syntax_ok = False
                                    err_msg = f"Sintaksės klaida ({se})"
                                except MemoryError:
                                    # File too big to compile in RAM at once, allow saving anyway
                                    gc.collect()

                            if not syntax_ok:
                                try:
                                    os.remove(tmp_name)
                                except Exception:
                                    pass
                                _send_response(conn, "400 Bad Request", body=err_msg)
                            else:
                                try:
                                    os.rename(tmp_name, "/" + fname)
                                    if debug:
                                        print(f"[OTA] Updated file: {fname} ({written} bytes)")
                                    _send_response(conn, "200 OK", body=f"Išsaugota ({written} B)")
                                except Exception as e:
                                    _send_response(conn, "500 Internal Server Error", body=str(e))

                elif method == "POST" and path.startswith("/reboot"):
                    _send_response(conn, "200 OK", body="Rebooting")
                    should_reboot = True

                else:
                    _send_response(conn, "404 Not Found", body="Not Found")

            except Exception as e:
                if debug:
                    print(f"[OTA] Request error: {e}")
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
                gc.collect()

    finally:
        if set_led_duty:
            set_led_duty(0)
        try:
            srv.close()
        except Exception:
            pass
        disable_wifi()

    if debug:
        print("[OTA] Rebooting ESP32-C3 into Normal Mode...")
    time.sleep_ms(400)
    machine.reset()

