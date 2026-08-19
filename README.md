# GPU Monitor Dashboard — RTX 5070 Ti + llama.cpp

Dashboard local para o monitor secundário 1920x480, mostrando GPU (via `nvidia-smi`)
e métricas do `llama-server` (llama.cpp) em tempo real.

## 1. Instalar dependências

```bash
cd gpu-monitor
pip install -r requirements.txt
```

Requer Python 3.9+ e o driver NVIDIA instalado (para o `nvidia-smi` estar no PATH —
já vem por padrão em qualquer instalação de driver Windows/Linux).

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

## 3. Rodar o servidor

```bash
python server.py
```

Ele sobe em `http://localhost:5150`.

## 4. Exibir no monitor secundário (1920x480)

A forma mais simples é abrir o Chrome/Edge em modo app, sem bordas, já
posicionado e dimensionado no monitor errado — ajuste `X` para a posição X
onde seu segundo monitor começa (verifique em Configurações de Vídeo do
Windows, ex: se o monitor principal é 1920 de largura e o segundo fica à
direita, X = 1920):

```bash
# Windows (Edge ou Chrome)
start msedge --app=http://localhost:5150 --window-size=1920,480 --window-position=1920,0
```

ou, no Chrome:

```bash
start chrome --app=http://localhost:5150 --window-size=1920,480 --window-position=1920,0
```

Isso abre uma janela sem barra de endereço, do tamanho exato do monitor,
já posicionada nele.

### Rodar tudo automaticamente na inicialização

Crie um `.bat` (ex: `start_dashboard.bat`) na pasta do projeto:

```bat
@echo off
start /min python server.py
timeout /t 2 >nul
start msedge --app=http://localhost:5150 --window-size=1920,480 --window-position=1920,0
```

E, se quiser, coloque um atalho dele na pasta de Inicialização do Windows
(`shell:startup`) para subir junto com o PC.

## Estrutura do projeto

```
gpu-monitor/
├── server.py          # backend Flask: polling GPU + llama.cpp
├── requirements.txt
├── static/
│   └── index.html      # dashboard (frontend)
└── README.md
```

## Personalização rápida

- **Intervalo de atualização**: `POLL_INTERVAL_SECONDS` em `server.py` e
  `POLL_MS` em `index.html` (mantenha os dois em sincronia).
- **Cores/tema**: variáveis CSS no topo de `index.html` (`:root { ... }`).
- **Métricas adicionais do nvidia-smi**: adicione ao parâmetro `--query-gpu`
  em `poll_gpu()` — veja a lista completa com `nvidia-smi --help-query-gpu`.
