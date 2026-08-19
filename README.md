# GPU Monitor — RTX 5070 Ti + llama.cpp

Dashboard fullscreen para monitor secundário (1920x480), exibindo em tempo real:
- **GPU** (via `nvidia-smi`): utilização, VRAM, temperatura, fan, power, clocks;
- **llama.cpp** (`llama-server`): modelo carregado, tok/s de prompt e geração,
  requisições ativas, uso de contexto;
- **Telemetria**: sparkline da última hora de utilização de GPU;
- **Tema** dark (padrão) e light, com persistência em `localStorage`.

## Versões em que a solução foi construída e testada

Matriz real do ambiente onde o dashboard foi desenvolvido e validado
(registrada em 2026-08-19). Use como referência ao atualizar qualquer
componente — se a lógica quebrar após um update, é provável que a mudança
esteja em um dos itens abaixo (especialmente o llama.cpp, cujas métricas
Prometheus variam entre builds — ver nota na seção 2).

| Componente | Versão | Observação |
|---|---|---|
| OS | Windows 11 Pro 10.0.26200 | |
| GPU | NVIDIA GeForce RTX 5070 Ti (16 GB) | single-GPU, WDDM |
| Driver NVIDIA | 610.88 (KMD 610.88, UMD 13.3) | fornece `nvidia-smi` |
| CUDA Toolkit | 13.3 (V13.3.73) | runtime do llama.cpp |
| llama.cpp | commit `ee4c505a4` (~`b10499`+6) | binário `llama-server.exe` compilado em 2026-08-17; flags do processo: `-c 131072 --cache-type-k q4_0 --cache-type-v q4_0 -kvu --cache-ram 12288 -ngl 99 -fa on --spec-type draft-mtp --metrics --host 0.0.0.0 --port 1234` |
| Modelo testado | Qwen3.8-27B-UD-IQ3_XXS (Q4_K) | 27.3B params, n_ctx 131072, spec-decode MTP (draft n-max 2) |
| Python | 3.11.15 | (mínimo aceito: 3.9+) |
| Flask | 3.1.3 | |
| requests | 2.33.0 | |
| Navegador do painel | Chrome, modo `--app` | perfil `C:\temp\perfil_painel_f11` |

### Pontos de ruptura conhecidos ao atualizar

1. **llama.cpp** — risco 1 (maior). Os nomes/semântica das métricas
   `llamacpp:*` variam entre builds (ex.: neste build os gauges
   `*_tokens_seconds` ficam em 0; o tok/s é derivado do delta dos
   contadores em `server.py`). Se quebrar, confira
   `http://localhost:1234/metrics` e ajuste `fetch_llama()`.
2. **Driver NVIDIA** — risco 2. As colunas de `--query-gpu` são estáveis
   entre versões recentes, mas o parser assume **ordem fixa** dos campos
   (ver `poll_gpu()`). Se quebrar, confira a saída de
   `nvidia-smi --query-gpu=... --format=csv,noheader,nounits`.
3. **Python/Flask** — risco 3 (baixo). API do Flask 3.x usada é estável;
   mantenha 3.9+ e `flask>=3.0.0`.

## 1. Instalar dependências

```bash
cd gpu-monitor
pip install -r requirements.txt
```

Requisitos mínimos:

| Requisito | Observação |
|---|---|
| Python 3.9+ | para o backend Flask |
| `flask`, `requests` | via `requirements.txt` |
| Driver NVIDIA | o `nvidia-smi` precisa estar no PATH (vem com o driver Windows/Linux) |
| CUDA + toolkit | somente para o llama.cpp rodar o modelo na GPU |
| `llama-server` (llama.cpp) | opcional, mas recomendado — sem ele o card do llama.cpp fica "offline" |

## 2. Habilitar métricas no llama.cpp (opcional, mas recomendado)

Ao subir o `llama-server`, adicione a flag `--metrics`:

```bash
llama-server -m seu_modelo.gguf --port 8080 --metrics
```

Sem essa flag, o dashboard ainda funciona normalmente — só mostra o card do
llama.cpp como "offline" e foca nas métricas de GPU.

Se seu servidor roda em outra porta, edite `LLAMA_SERVER_URL` no topo do
`server.py`.

> Nota: os nomes exatos das métricas Prometheus expostas pelo llama.cpp podem
> variar um pouco entre versões. Se os campos de tokens/s aparecerem como
> `--` mesmo com `--metrics` ativo, acesse `http://localhost:8080/metrics`
> no navegador, veja os nomes reais das métricas retornadas, e ajuste o
> dicionário `m.get(...)` em `poll_llama()` dentro de `server.py`.

## 3. Rodar o sistema

**Manual:**

```bash
python server.py
```

Ele sobe em `http://localhost:5150`.

**Automático (recomendado para este cenário):** rode `start_dashboard.bat`.
O script:

1. inicia o `server.py` numa janela minimizada;
2. espera o Flask ficar disponível (checando `http://127.0.0.1:5150/api/stats`);
3. abre o Chrome em modo app no monitor secundário (1920x480):

```bat
chrome --app="http://localhost:5150" --window-position=1920,0 --window-size=1920,480 --force-device-scale-factor=1 --start-fullscreen --user-data-dir="C:\temp\perfil_painel_f11"
```

## 4. Particularidades deste projeto (cenario atual)

Este projeto foi desenvolvido para o cenário específico:
**llama.cpp + RTX 5070 Ti + monitor secundário 1920x480** — um painel
sempre ligado ao lado da estação de inferência. Os comandos de janela
abaixo são ajustados para esse cenário; adapte se o seu for diferente.

### Chrome em modo app no monitor secundário

```bash
chrome --app="http://localhost:5150" --window-position=1920,0 --window-size=1920,480 --force-device-scale-factor=1 --start-fullscreen --user-data-dir="C:\temp\perfil_painel_f11"
```

- `--window-position=1920,0`: posicione onde seu segundo monitor começa
  (verifique em Configurações de Vídeo do Windows — se o monitor principal
  é 1920 de largura e o segundo fica à direita, X = 1920).
- `--force-device-scale-factor=1`: força escala 100%, evitando que o
  Windows DPI escalonamento distorja o tamanho da janela.
- `--user-data-dir`: perfil dedicado para o painel — evita conflitar com
  a sessão normal do Chrome e permite que a janela do app rode em paralelo.

### Inicialização automática

Coloque um atalho de `start_dashboard.bat` na pasta de Inicialização do
Windows (`shell:startup`) para subir junto com o PC.

## Estrutura do projeto

```
gpu-monitor/
├── server.py            # backend Flask: polling GPU + llama.cpp
├── requirements.txt
├── LICENSE              # MIT
├── start_dashboard.bat  # sobe o server e abre o Chrome no monitor secundário
├── static/
│   └── index.html       # dashboard (frontend, tema dark/light)
└── README.md
```

## Personalização rápida

- **Intervalo de atualização**: `POLL_INTERVAL_SECONDS` em `server.py` e
  `POLL_MS` em `index.html` (mantenha os dois em sincronia).
- **Porta do llama-server**: `LLAMA_SERVER_URL` em `server.py`.
- **Cores/tema**: variáveis CSS no topo de `index.html`
  (`:root { ... }` para dark, `[data-theme="light"] { ... }` para light).
- **Métricas adicionais do nvidia-smi**: adicione ao parâmetro
  `--query-gpu` em `poll_gpu()` — veja a lista completa com
  `nvidia-smi --help-query-gpu`.
