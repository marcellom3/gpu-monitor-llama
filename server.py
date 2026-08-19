"""
GPU Monitor Dashboard - servidor local
----------------------------------------
Faz polling de:
  1) GPU via `nvidia-smi` (utilização, VRAM, temperatura, power, clocks)
  2) llama.cpp server via endpoint /metrics (Prometheus text format)

Requisitos:
  pip install flask requests

Uso:
  python server.py
  Depois abra http://localhost:5150 no navegador (janela posicionada no
  monitor secundário 1920x480).

Ajuste LLAMA_SERVER_URL abaixo se seu llama-server não estiver na porta 8080.
Para o llama.cpp expor métricas, inicie o servidor com a flag --metrics, ex:
  llama-server -m modelo.gguf --port 8080 --metrics
"""

import subprocess
import threading
import time
import requests
from flask import Flask, jsonify, send_from_directory

# ---- CONFIG ----
LLAMA_SERVER_URL = "http://localhost:1234"
POLL_INTERVAL_SECONDS = 1.0
DASHBOARD_PORT = 5150
HISTORY_LENGTH = 60  # pontos guardados para o mini-gráfico (1 por segundo = 60s)

app = Flask(__name__, static_folder="static")

state = {
    "gpu": {"online": False},
    "llama": {"online": False},
    "gpu_history": [],
    "timestamp": 0,
}
lock = threading.Lock()


def poll_gpu():
    query = (
        "utilization.gpu,utilization.memory,memory.used,memory.total,"
        "temperature.gpu,power.draw,power.limit,clocks.sm,clocks.mem,fan.speed"
    )
    while True:
        try:
            out = subprocess.check_output(
                ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"],
                encoding="utf-8",
                timeout=2,
            )
            vals = [v.strip() for v in out.strip().split(",")]

            def safe_float(v):
                try:
                    return float(v)
                except ValueError:
                    return None

            gpu_data = {
                "online": True,
                "util_gpu": safe_float(vals[0]),
                "util_mem": safe_float(vals[1]),
                "vram_used": safe_float(vals[2]),
                "vram_total": safe_float(vals[3]),
                "temp": safe_float(vals[4]),
                "power_draw": safe_float(vals[5]),
                "power_limit": safe_float(vals[6]),
                "clock_sm": safe_float(vals[7]),
                "clock_mem": safe_float(vals[8]),
                "fan": safe_float(vals[9]),
            }
        except Exception as e:
            gpu_data = {"online": False, "error": str(e)}

        with lock:
            state["gpu"] = gpu_data
            if gpu_data.get("online"):
                state["gpu_history"].append(gpu_data.get("util_gpu") or 0)
                if len(state["gpu_history"]) > HISTORY_LENGTH:
                    state["gpu_history"].pop(0)
            state["timestamp"] = time.time()

        time.sleep(POLL_INTERVAL_SECONDS)


def parse_prometheus(text):
    """Parser simples para o formato de texto do Prometheus."""
    metrics = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.rsplit(" ", 1)
        if len(parts) != 2:
            continue
        key, value = parts
        key = key.split("{")[0]
        try:
            metrics[key] = float(value)
        except ValueError:
            continue
    return metrics


_llama_prev = None
_llama_last_tps = {"prompt": None, "predicted": None}


def fetch_llama():
    """Consulta /metrics do llama-server.

    Neste build do llama.cpp:
      - os gauges `*_tokens_seconds` ficam sempre em 0;
      - os contadores `*_tokens_total` / `*_seconds_total` só são
        atualizados no /metrics ao final de cada requisição (não em tempo
        real — `n_decode_total` sim atualiza em tempo real, mas não é
        tokens/s com spec-decode).
    Por isso os tokens/s são derivados do delta dos contadores entre duas
    amostras, e o último valor medido é mantido (sticky) para o card não
    voltar a "--" no meio de uma geração.
    """
    global _llama_prev
    try:
        r = requests.get(f"{LLAMA_SERVER_URL}/metrics", timeout=1.5)
        r.raise_for_status()
        m = parse_prometheus(r.text)

        cur = {
            "prompt_tokens": m.get("llamacpp:prompt_tokens_total"),
            "prompt_secs": m.get("llamacpp:prompt_seconds_total"),
            "predicted_tokens": m.get("llamacpp:tokens_predicted_total"),
            "predicted_secs": m.get("llamacpp:tokens_predicted_seconds_total"),
        }

        if _llama_prev is not None:
            if None not in (cur["prompt_tokens"], cur["prompt_secs"],
                            _llama_prev["prompt_tokens"], _llama_prev["prompt_secs"]):
                d_tok = cur["prompt_tokens"] - _llama_prev["prompt_tokens"]
                d_sec = cur["prompt_secs"] - _llama_prev["prompt_secs"]
                if d_tok >= 0 and d_sec > 1e-9:
                    _llama_last_tps["prompt"] = d_tok / d_sec
            if None not in (cur["predicted_tokens"], cur["predicted_secs"],
                            _llama_prev["predicted_tokens"], _llama_prev["predicted_secs"]):
                d_tok = cur["predicted_tokens"] - _llama_prev["predicted_tokens"]
                d_sec = cur["predicted_secs"] - _llama_prev["predicted_secs"]
                if d_tok >= 0 and d_sec > 1e-9:
                    _llama_last_tps["predicted"] = d_tok / d_sec
        # Servidor reiniciou (contador zerou)? A referência é atualizada
        # para `cur` no final; o guard `d_tok >= 0` acima já ignora o delta.
        _llama_prev = cur

        prompt_tps = _llama_last_tps["prompt"]
        predicted_tps = _llama_last_tps["predicted"]

        # Fallback para versões do llama.cpp em que os gauges funcionam
        # (neste build eles ficam sempre em 0)
        if prompt_tps is None:
            prompt_tps = m.get("llamacpp:prompt_tokens_seconds") or None
        if predicted_tps is None:
            predicted_tps = m.get("llamacpp:predicted_tokens_seconds") or None

        return {
            "online": True,
            "prompt_tps": prompt_tps,
            "predicted_tps": predicted_tps,
            # Não exposta por este build do llama.cpp (o front mostra "--")
            "kv_cache_usage": m.get("llamacpp:kv_cache_usage_ratio"),
            "requests_processing": m.get("llamacpp:requests_processing"),
            "requests_deferred": m.get("llamacpp:requests_deferred"),
        }
    except Exception:
        return {"online": False}


def poll_llama():
    while True:
        data = fetch_llama()
        with lock:
            state["llama"] = data
        time.sleep(POLL_INTERVAL_SECONDS)


@app.route("/api/stats")
def api_stats():
    with lock:
        return jsonify(state)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


if __name__ == "__main__":
    threading.Thread(target=poll_gpu, daemon=True).start()
    threading.Thread(target=poll_llama, daemon=True).start()
    print(f"Dashboard rodando em http://localhost:{DASHBOARD_PORT}")
    app.run(host="127.0.0.1", port=DASHBOARD_PORT, debug=False)
