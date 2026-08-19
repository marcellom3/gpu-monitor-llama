"""Probe 4: gera via /v1/chat/completions (OpenAI-compat) + amostra /metrics a cada 100ms."""
import random
import string
import threading
import time
import requests

BASE = "http://127.0.0.1:1234"

random.seed(7)
user_prompt = "Write a very long poem about mountains. Begin now.\n" + " ".join(
    "".join(random.choices(string.ascii_lowercase, k=7)) for _ in range(200)
)

done = threading.Event()
resp_info = {}

def gen():
    try:
        r = requests.post(
            f"{BASE}/v1/chat/completions",
            json={
                "model": "default",
                "messages": [{"role": "user", "content": user_prompt}],
                "max_tokens": 2000,
                "temperature": 0.3,
            },
            stream=False, timeout=600,
        )
        resp_info["status"] = r.status_code
        if r.status_code != 200:
            resp_info["body"] = r.text[:300]
        else:
            j = r.json()
            resp_info["usage"] = j.get("usage")
            resp_info["finish"] = j.get("choices", [{}])[0].get("finish_reason")
    except Exception as e:
        resp_info["error"] = str(e)
    finally:
        done.set()

t = threading.Thread(target=gen, daemon=True)
t.start()

t0 = time.time()
while not done.wait(0.1):
    m = requests.get(f"{BASE}/metrics", timeout=1)
    lines = {}
    for line in m.text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        k, _, v = line.rpartition(" ")
        lines[k.split("{")[0]] = v
    print(
        f"t={time.time()-t0:7.2f} ",
        f"p_tps={str(lines.get('llamacpp:prompt_tokens_seconds')):>9} ",
        f"g_tps={str(lines.get('llamacpp:predicted_tokens_seconds')):>9} ",
        f"req={lines.get('llamacpp:requests_processing')}",
        flush=True,
    )

print("--- after done ---")
print(resp_info)
