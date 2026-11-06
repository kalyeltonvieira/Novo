@echo off
echo ==============================================
echo Iniciando IA Analisadora - Dashboard Web
echo ==============================================
echo.

echo Iniciando o servidor FastAPI (Backend) na porta 8000...
start cmd /k "python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000"

echo.
echo Iniciando o servidor Next.js (Frontend) na porta 3000...
cd frontend
start cmd /k "npm run dev"

echo.
echo Ambos os servidores estao iniciando.
echo Acesse o frontend em: http://localhost:3000
echo Acesse a API em: http://localhost:8000/docs
echo.
pause
