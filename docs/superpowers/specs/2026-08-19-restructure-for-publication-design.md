# Design: Reestruturação do gpu-monitor para publicação (gpu-monitor-llama)

**Data:** 2026-08-19
**Status:** Aprovado pelo usuário
**Alvo:** publicação no GitHub como `gpu-monitor-llama`

## Decisões alinhadas

| Item | Decisão |
|---|---|
| Escopo | Intermediário (B): package Python organizado, tests, CI. Sem packaging pip, sem Docker. |
| GPUs | Single-GPU (mantém o atual; documentado no README). |
| License | MIT |
| Python | 3.9+ (conforme README atual) |
| CI | GitHub Actions: Windows + Linux |

## Estrutura de diretórios (após reestruturação)

```
gpu-monitor-llama/
├── gpu_monitor/               # package Python
│   ├── __init__.py            # __version__, docstring curta
│   ├── __main__.py            # entry point: python -m gpu_monitor
│   ├── app.py                 # Flask app, rotas /api/stats e /
│   ├── config.py              # LLAMA_SERVER_URL, POLL_INTERVAL, PORT, HISTORY_LENGTH
│   ├── gpu.py                 # parser do nvidia-smi + loop de polling
│   ├── llama.py               # fetch_llama() + parse_prometheus() + derivação de tok/s
│   └── static/
│       └── index.html         # dashboard (sem mudanças funcionais)
├── scripts/
│   └── probes/                # _probe_api.py, _probe_cadence.py, _probe_metrics.py
├── tests/
│   ├── test_gpu_parser.py     # parser nvidia-smi com string fake (sem GPU real)
│   ├── test_prometheus.py     # parser Prometheus com texto fake
│   └── test_api.py            # smoke: GET /api/stats via Flask test client
├── .github/workflows/ci.yml   # CI: Windows + Linux
├── .gitignore
├── LICENSE                    # MIT
├── README.md                  # reescrito: badges, setup, estrutura, contribuição
└── requirements.txt
```

## Arquitetura interna (mudanças em relação ao server.py atual)

O `server.py` (204 linhas, tudo em 1 arquivo) vira o package `gpu_monitor/` com separação por responsabilidade:

1. **`config.py`** — constantes de configuração: `LLAMA_SERVER_URL`, `POLL_INTERVAL_SECONDS`, `DASHBOARD_PORT`, `HISTORY_LENGTH`, `SUPPORTED_GPU_COUNT` (1). Centraliza o que o README chama de "personalização rápida".
2. **`gpu.py`** — função pura `parse_nvidia_smi_csv(csv_text) -> dict` (testável) + `poll_gpu(state, lock)` que faz `subprocess.check_output` e chama o parser. O parse assume 1 GPU (documentado).
3. **`llama.py`** — `parse_prometheus(text) -> dict` (já existe, move + docstring) + classe/estado `LlamaMetrics` encapsulando `_llama_prev`/`_llama_last_tps` que hoje são globals de módulo + `fetch_llama()`.
4. **`app.py`** — cria o app Flask, rota `/api/stats` (jsonify do state com lock), rota `/`, e `run()` que sobe as 2 threads daemon. Estado compartilhado (dict `state` + `threading.Lock`) fica aqui ou em `state.py` — decisão de implementação.
5. **`__main__.py`** — `if __package__: run()` permitindo `python -m gpu_monitor`.

## Testes

- **`tests/test_gpu_parser.py`**: passa strings CSV fake (incluindo caso `[N/A]` do nvidia-smi) para `parse_nvidia_smi_csv` e valida o dict.
- **`tests/test_prometheus.py`**: texto Prometheus fake com métricas `llamacpp:*`, valida parser (keys com labels, valores numéricos, linhas `#` ignoradas).
- **`tests/test_api.py`**: Flask test client + app em modo "offline" (sem GPU/llama reais), valida que `GET /api/stats` retorna 200 com a estrutura esperada (`gpu`, `llama`, `gpu_history`, `timestamp`).

Sem mocks de GPU/llama reais — apenas dados de entrada fake nos parsers.

## CI (`.github/workflows/ci.yml`)

- Matrix: `windows-latest`, `ubuntu-latest`
- Python: 3.9, 3.10, 3.11 (matrix de versões)
- Job: `pip install -r requirements.txt pytest` → `pytest`
- (Flask test client não precisa de GPU nem de llama-server rodando — só os parsers são exercidos.)

## .gitignore

```
__pycache__/
*.pyc
.venv/
venv/
*.log
.pytest_cache/
```

## Limpeza da raiz

- Remover `server.py` da raiz (vira o package).
- Mover `_probe_*.py` para `scripts/probes/` (sem prefixo `_`, renomeados para `probe_api.py`, `probe_cadence.py`, `probe_metrics.py`).
- Remover `dashboard.log` (deletado; `*.log` entra no .gitignore).

## README (reescrito)

Seções:
1. **Badge de CI** + tagline curta
2. **Screenshot** (placeholder — usuário adiciona depois)
3. **Features** (bullets)
4. **Requirements** (Python 3.9+, driver NVIDIA, llama.cpp opcional)
5. **Install** (venv + pip)
6. **Quick start** (3 comandos)
7. **Monitor secundário 1920x480** (mantido do README atual, com o `.bat` de inicialização)
8. **Estrutura do projeto** (nova)
9. **Personalização** (aponta para `gpu_monitor/config.py`)
10. **Limitações** (single-GPU, métricas do llama.cpp podem variar por build — nota do README atual)
11. **License** (MIT)

## Fora de escopo (YAGNI)

- Multi-GPU, packaging pip/pyproject, Docker, WebSocket (mantém polling), tema claro, i18n do dashboard.

## Riscos / notas de implementação

- `nvidia-smi` em Windows retorna `[N/A]` para `fan.speed` sem fan — o parser já trata com `safe_float` (mantém).
- A derivação de tokens/s via delta de contadores (sticky) é o comportamento mais sutil do código atual; testar os casos de borda (contador zerado após restart do servidor) em `test_prometheus.py`/`test_llama_metrics`.
- `index.html` não muda funcionalmente — apenas move para `gpu_monitor/static/`.
