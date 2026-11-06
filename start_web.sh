#!/bin/bash
# ==============================================
# Iniciando IA Analisadora - Dashboard Web
# ==============================================

echo "=============================================="
echo " Iniciando IA Analisadora - Dashboard Web"
echo "=============================================="
echo ""

# Verifica se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Instale Python 3.8+ primeiro."
    exit 1
fi

# Verifica se Node.js está instalado
if ! command -v node &> /dev/null; then
    echo "❌ Node.js não encontrado. Instale Node.js 18+ primeiro."
    exit 1
fi

# Verifica se o ambiente virtual existe
if [ ! -d ".venv" ]; then
    echo "🔧 Criando ambiente virtual Python..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    python -m spacy download pt_core_news_lg
else
    source .venv/bin/activate
fi

# Inicia o servidor FastAPI (Backend) na porta 8000
echo "🚀 Iniciando servidor FastAPI (Backend) na porta 8000..."
python3 -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Aguarda o backend iniciar
sleep 3

# Inicia o servidor Next.js (Frontend) na porta 3000
echo "🚀 Iniciando servidor Next.js (Frontend) na porta 3000..."
cd frontend
npm install --silent 2>/dev/null
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Ambos os servidores estão iniciando."
echo "📊 Acesse o frontend em: http://localhost:3000"
echo "🔌 Acesse a API em: http://localhost:8000/docs"
echo "📋 Documentação da API: http://localhost:8000/redoc"
echo ""

# Trap para matar os processos ao sair
trap "echo 'Encerrando servidores...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# Aguarda os processos
wait