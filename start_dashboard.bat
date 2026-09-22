@echo off
rem ============================================================
rem GPU Monitor - inicializacao (cenario: RTX 5070 Ti +
rem llama.cpp + monitor secundario 1920x480)
rem
rem 1) Sobe o server.py (minimizado no terminal)
rem 2) Espera o Flask ficar disponivel (max. 10s)
rem 3) Abre o Chrome em modo app no monitor secundario
rem ============================================================

rem ---- 1. Sobe o servidor (janela minimizada) ----
start "GPU Monitor" /min python server.py

rem ---- 2. Aguarda o dashboard ficar no ar (max. 10 tentativas) ----
set /a i=0
:wait_loop
set /a i+=1
curl -s -o nul http://127.0.0.1:5150/api/stats
if errorlevel 1 goto wait_check
goto open_chrome
:wait_check
if %i% LSS 10 (
  timeout /t 1 /nobreak >nul
  goto wait_loop
) else (
  echo [aviso] Server demorando para subir; abrindo Chrome mesmo assim.
)


rem ---- 3. Abre o Chrome no monitor secundario (1920x480) ---- o monitor 2 deve estar na posição obrigatória das configurações do windows abaixo e centralizado, em relação ao monitor 1
:open_chrome
start "" chrome --app="http://localhost:5150" --window-position=0,1080 --window-size=1920,480 --force-device-scale-factor=1 --start-fullscreen --user-data-dir="C:\temp\perfil_painel_f11"

rem ---- 3. Abre o Chrome no monitor secundario (1920x480) ---- o monitor 2 deve estar na posição obrigatória das configurações do windows ao lado direito e centralizado, em relação ao monitor 1
rem :open_chrome
rem start "" chrome --app="http://localhost:5150" --window-position=1920,0 --window-size=1920,480 --force-device-scale-factor=1 --start-fullscreen --user-data-dir="C:\temp\perfil_painel_f11"