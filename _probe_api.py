"""Teste final: gera 3000 tokens e amostra /api/stats do dashboard a cada 1s."""
import random
import string
import threading
import time
import requests

BASE = "http://127.0.0.1:1234"
DASH = "http://127.0.0.1:5150"

random.seed(42)
user_prompt = "Write a very long poem about mountains. Begin now.\n" + " ".join(
    "".join(random.choices(string.ascii_lowercase, k=7)) for _ in range(200)
)

done = threading.Event()

def gen():
    try:
        r = requests.post(
            f"{BASE}/v1/chat/completions",
            json={
                "model": "default",
                "messages": [{"role": "user", "content": user_prompt}],
                "max_tokens": 3000,
                "temperature": 0.3,
            },
            stream=False, timeout=900,
        )
        if r.status_code == 200:
            u = r.json().get("usage", {})
            print("GEN DONE:", u.get("completion_tokens"), "tokens")
        else:
            print("GEN FAIL:", r.status_code, r.text[:200])
    except Exception as e:
        print("GEN ERR:", e)
    finally:
        done.set()

t = threading.Thread(target=gen, daemon=True)
t.start()

t0 = time.time()
while not done.wait(1.0):
    d = requests.get(f"{DASH}/api/stats", timeout=2).json()
    l = d.get("llama", {})
    print(
        f"t={time.time()-t0:6.1f}  "
        f"p_tps={l.get('prompt_tps')}  "
        f"g_tps={l.get('predicted_tps')}  "
        f"req={l.get('requests_processing')}  "
        f"gpu={d.get('gpu', {}).get('util_gpu')}%",
        flush=True,
    )

# aguarda mais 3s para ver decaimento pós-gera
end = time.time()
while time.time() - end < 3:
    time.sleep(1)
d = requests.get(f"{DASH}/api/stats", timeout=2).json()
print("final:", d.get("llama"))
