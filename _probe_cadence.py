"""Probe 5: cadência de atualização dos contadores do /metrics (amostra 100ms)."""
import random
import string
import threading
import time
import requests

BASE = "http://127.0.0.1:1234"

random.seed(99)
user_prompt = "Write a long story. Begin.\n" + " ".join(
    "".join(random.choices(string.ascii_lowercase, k=7)) for _ in range(100)
)

done = threading.Event()

def gen():
    r = requests.post(
        f"{BASE}/v1/chat/completions",
        json={
            "model": "default",
            "messages": [{"role": "user", "content": user_prompt}],
            "max_tokens": 100,
            "temperature": 0.3,
        },
        stream=False, timeout=300,
    )
    print("GEN done:", r.status_code, r.json().get("usage", {}), flush=True)
    done.set()

t = threading.Thread(target=gen, daemon=True)
t.start()

t0 = time.time()
last = {}
while time.time() - t0 < 15:
    m = requests.get(f"{BASE}/metrics", timeout=1)
    lines = {}
    for line in m.text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        k, _, v = line.rpartition(" ")
        lines[k.split("{")[0]] = v
    cur = {
        "pred_tok": lines.get("llamacpp:tokens_predicted_total"),
        "pred_sec": lines.get("llamacpp:tokens_predicted_seconds_total"),
        "req": lines.get("llamacpp:requests_processing"),
        "ndec": lines.get("llamacpp:n_decode_total"),
    }
    if cur != last:
        print(
            f"t={time.time()-t0:6.2f} "
            f"pred_tok={cur['pred_tok']} pred_sec={cur['pred_sec']} "
            f"req={cur['req']} ndec={cur['ndec']}",
            flush=True,
        )
        last = cur
    if done.is_set() and time.time() - t0 > 8:
        break
    time.sleep(0.1)
