"""
Exemplo de Uso com API de IA - IA Analisadora
=============================================
Demonstra como usar diferentes provedores de IA (OpenAI, Anthropic, Google, Cohere)
para análise avançada de documentos.
"""

import os
import sys

# Garante que a raiz do projeto está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ai_providers import (
    AIProvider, AIManager, get_ai_manager,
    MODELS_CATALOG
)
from core.leitor_universal import LeitorUniversal
from core.detector_anomalias import DetectorAnomalias


def listar_provedores_disponiveis():
    """Lista todos os provedores de IA disponíveis."""
    print("=" * 60)
    print("PROVEDORES DE IA DISPONÍVEIS")
    print("=" * 60)
    
    ai_manager = get_ai_manager()
    catalogo = ai_manager.get_available_models()
    
    for provider, modelos in catalogo.items():
        print(f"\n📦 {provider.value.upper()}:")
        for modelo in modelos:
            print(f"   • {modelo.display_name} ({modelo.model_name})")
    
    print("\n" + "=" * 60)


def verificar_provedores_configurados():
    """Verifica quais provedores têm API keys configuradas."""
    print("\n" + "=" * 60)
    print("PROVEDORES CONFIGURADOS (com API Key)")
    print("=" * 60)
    
    ai_manager = get_ai_manager()
    disponiveis = ai_manager.get_available_providers()
    
    for provider in disponiveis:
        status = "✅ Configurado" if provider != AIProvider.LOCAL else "✅ Local (spaCy)"
        print(f"  {provider.value.upper()}: {status}")
    
    if len(disponiveis) == 1:
        print("\n⚠️  Nenhum provedor de API configurado.")
        print("   Configure as API keys no arquivo .env:")
        print("   - OPENAI_API_KEY")
        print("   - ANTHROPIC_API_KEY")
        print("   - GOOGLE_API_KEY")
        print("   - COHERE_API_KEY")
    
    print("=" * 60)


def testar_provedor_especifico(provider: AIProvider):
    """Testa um provedor específico com uma chamada simples."""
    print(f"\n🧪 Testando provedor: {provider.value}")
    print("-" * 60)
    
    ai_manager = get_ai_manager()
    ai_manager.set_provider(provider)
    
    client = ai_manager.get_client()
    
    if not client.is_available():
        print(f"❌ Provedor {provider.value} não disponível (API key não configurada)")
        return False
    
    print(f"✅ Provedor {provider.value} disponível")
    
    # Testa uma chamada simples
    try:
        resultado = client.chat_completion(
            prompt="Responda em uma frase: O que é transparência pública?",
            temperature=0.7,
            max_tokens=100,
        )
        
        if resultado:
            print(f"✅ Chamada bem-sucedida!")
            print(f"   Resposta: {resultado[:100]}...")
            return True
        else:
            print(f"❌ Chamada falhou (sem resposta)")
            return False
    
    except Exception as e:
        print(f"❌ Erro na chamada: {e}")
        return False


def analisar_documento_com_ia(caminho_documento: str, provider: AIProvider):
    """Analisa um documento usando um provedor específico de IA."""
    print(f"\n📄 Analisando documento com IA ({provider.value})")
    print("-" * 60)
    
    # Configura o provedor
    ai_manager = get_ai_manager()
    ai_manager.set_provider(provider)
    
    # Configura leitor com IA
    leitor = LeitorUniversal(config={"use_ai": True})
    
    # Processa documento
    print(f"🔍 Processando: {caminho_documento}")
    documento = leitor.processar_documento(caminho_documento)
    
    if not documento:
        print("❌ Não foi possível processar o documento")
        return None
    
    print(f"✅ Documento processado")
    print(f"   Tipo: {documento.tipo.value}")
    print(f"   Entidades extraídas: {len(documento.entidades)}")
    
    # Conta entidades por tipo
    from collections import Counter
    tipos = Counter([e.tipo.value for e in documento.entidades])
    print(f"   Distribuição: {dict(tipos)}")
    
    # Mostra algumas entidades
    print("\n📋 Entidades principais:")
    for ent in documento.entidades[:10]:
        print(f"   • [{ent.tipo.value}] {ent.valor}")
    
    return documento


def detectar_anomalias_com_ia(documento, provider: AIProvider):
    """Detecta anomalias usando IA."""
    print(f"\n⚠️  Detectando anomalias com IA ({provider.value})")
    print("-" * 60)
    
    # Configura o provedor
    ai_manager = get_ai_manager()
    ai_manager.set_provider(provider)
    
    # Configura detector com IA
    detector = DetectorAnomalias(config={"use_ai": True})
    
    # Detecta anomalias
    alertas = detector.processar(
        documentos=[documento],
        relacionamentos=[],
        pessoas={},
        empresas={},
    )
    
    print(f"✅ Detecção concluída")
    print(f"   Alertas encontrados: {len(alertas)}")
    
    if alertas:
        print("\n🚨 Alertas:")
        for alerta in alertas[:5]:
            print(f"   • [{alerta.severidade.upper()}] {alerta.titulo}")
            print(f"     {alerta.descricao[:100]}...")
    
    return alertas


def exemplo_uso_openai():
    """Exemplo de uso com OpenAI."""
    print("\n" + "=" * 60)
    print("EXEMPLO: OpenAI (GPT-4)")
    print("=" * 60)
    
    if not testar_provedor_especifico(AIProvider.OPENAI):
        print("⚠️  OpenAI não configurado. Configure OPENAI_API_KEY no .env")
        return


def exemplo_uso_anthropic():
    """Exemplo de uso com Anthropic Claude."""
    print("\n" + "=" * 60)
    print("EXEMPLO: Anthropic (Claude)")
    print("=" * 60)
    
    if not testar_provedor_especifico(AIProvider.ANTHROPIC):
        print("⚠️  Anthropic não configurado. Configure ANTHROPIC_API_KEY no .env")
        return


def exemplo_uso_google():
    """Exemplo de uso com Google Gemini."""
    print("\n" + "=" * 60)
    print("EXEMPLO: Google (Gemini)")
    print("=" * 60)
    
    if not testar_provedor_especifico(AIProvider.GOOGLE):
        print("⚠️  Google não configurado. Configure GOOGLE_API_KEY no .env")
        return


def exemplo_uso_cohere():
    """Exemplo de uso com Cohere."""
    print("\n" + "=" * 60)
    print("EXEMPLO: Cohere")
    print("=" * 60)
    
    if not testar_provedor_especifico(AIProvider.COHERE):
        print("⚠️  Cohere não configurado. Configure COHERE_API_KEY no .env")
        return


def exemplo_uso_local():
    """Exemplo de uso com spaCy local (sem API)."""
    print("\n" + "=" * 60)
    print("EXEMPLO: Local (spaCy)")
    print("=" * 60)
    
    testar_provedor_especifico(AIProvider.LOCAL)


def exemplo_analise_completa(caminho_documento: str, provider: AIProvider):
    """Exemplo de análise completa com um provedor específico."""
    print("\n" + "=" * 60)
    print(f"ANÁLISE COMPLETA: {provider.value.upper()}")
    print("=" * 60)
    
    # Testa provedor
    if not testar_provedor_especifico(provider):
        print(f"⚠️  {provider.value} não disponível")
        return
    
    # Analisa documento
    documento = analisar_documento_com_ia(caminho_documento, provider)
    if not documento:
        return
    
    # Detecta anomalias
    alertas = detectar_anomalias_com_ia(documento, provider)
    
    print("\n" + "=" * 60)
    print("✅ Análise concluída!")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    print("🧠 IA Analisadora - Exemplo de Uso com APIs de IA")
    print("=" * 60)
    
    # Lista provedores disponíveis
    listar_provedores_disponiveis()
    
    # Verifica provedores configurados
    verificar_provedores_configurados()
    
    # Se um documento foi passado como argumento
    if len(sys.argv) > 1:
        caminho_documento = sys.argv[1]
        
        # Se um provedor foi especificado
        if len(sys.argv) > 2:
            provider_str = sys.argv[2].lower()
            provider_map = {
                "openai": AIProvider.OPENAI,
                "anthropic": AIProvider.ANTHROPIC,
                "google": AIProvider.GOOGLE,
                "cohere": AIProvider.COHERE,
                "local": AIProvider.LOCAL,
            }
            provider = provider_map.get(provider_str, AIProvider.LOCAL)
        else:
            provider = AIProvider.LOCAL
        
        # Executa análise completa
        exemplo_analise_completa(caminho_documento, provider)
    else:
        # Testa todos os provedores
        print("\n🧪 Testando todos os provedores...")
        exemplo_uso_openai()
        exemplo_uso_anthropic()
        exemplo_uso_google()
        exemplo_uso_cohere()
        exemplo_uso_local()
        
        print("\n" + "=" * 60)
        print("💡 Para analisar um documento:")
        print("   python examples/exemplo_ia_api.py documento.pdf openai")
        print("   python examples/exemplo_ia_api.py documento.txt anthropic")
        print("=" * 60)
