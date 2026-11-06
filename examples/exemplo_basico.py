"""
Exemplo Básico - IA Analisadora
================================
Demonstra o uso básico do pipeline de análise de documentos.
"""

from core.leitor_universal import LeitorUniversal
from core.correlacionador import Correlacionador
from core.detector_anomalias import DetectorAnomalias
from core.base_conhecimento import BaseConhecimento
from core.camada_reports import CamadaReports


def analisar_documento(caminho_arquivo: str):
    """
    Analisa um único documento usando o pipeline completo.
    """
    print(f"🔍 Analisando documento: {caminho_arquivo}")
    
    # 1. Leitura e extração de entidades
    leitor = LeitorUniversal()
    documento = leitor.processar_documento(caminho_arquivo)
    
    if not documento:
        print("❌ Não foi possível processar o documento.")
        return
    
    print(f"✅ Documento processado")
    print(f"   - {len(documento.entidades)} entidades extraídas")
    print(f"   - Tipo: {documento.tipo.value}")
    
    # 2. Correlação de entidades
    correlacionador = Correlacionador()
    relacionamentos = correlacionador.processar_documentos([documento])
    
    print(f"✅ Correlação realizada")
    print(f"   - {len(relacionamentos)} relacionamentos encontrados")
    print(f"   - {len(correlacionador.pessoas)} pessoas identificadas")
    print(f"   - {len(correlacionador.empresas)} empresas identificadas")
    
    # 3. Detecção de anomalias
    detector = DetectorAnomalias()
    alertas = detector.processar(
        [documento],
        relacionamentos,
        correlacionador.pessoas,
        correlacionador.empresas,
    )
    
    print(f"✅ Detecção de anomalias realizada")
    print(f"   - {len(alertas)} alertas gerados")
    
    # Mostra alertas
    for alerta in alertas[:5]:
        print(f"   ⚠️ [{alerta.severidade.upper()}] {alerta.titulo}")
    
    # 4. Base de conhecimento
    base = BaseConhecimento()
    base.adicionar_entidades(documento.entidades)
    base.adicionar_relacionamentos(relacionamentos)
    base.adicionar_pessoas(correlacionador.pessoas)
    base.adicionar_empresas(correlacionador.empresas)
    base.adicionar_alertas(alertas)
    base.salvar()
    
    print(f"✅ Base de conhecimento atualizada")
    
    # 5. Relatórios
    reports = CamadaReports()
    dados = reports.gerar_dashboard(
        [documento],
        alertas,
        relacionamentos,
        correlacionador.pessoas,
        correlacionador.empresas,
    )
    
    caminho_html = reports.exportar_html(dados)
    caminho_json = reports.exportar_json(dados)
    
    print(f"✅ Relatórios gerados")
    print(f"   - HTML: {caminho_html}")
    print(f"   - JSON: {caminho_json}")
    
    return documento, alertas, relacionamentos


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python exemplo_basico.py <caminho_do_documento>")
        print("\nExemplo:")
        print("  python exemplo_basico.py documento.pdf")
        print("  python exemplo_basico.py contrato.txt")
        sys.exit(1)
    
    caminho = sys.argv[1]
    analisar_documento(caminho)
