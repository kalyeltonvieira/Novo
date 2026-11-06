"""
Camada de Reports - Visualização e Relatórios
==============================================
Gera dashboards, alertas, rankings, PDFs de evidência e denúncias.
"""

import os
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict, Counter
import statistics

from .entidades import (
    Documento, Alerta, Relatorio, Pessoa, Empresa, Contrato,
    Relacionamento, TipoAnomalia
)

# Importação do sistema de monitoring centralizado
try:
    from utils.monitoring import get_logger, get_metrics
    logger = get_logger("core.camada_reports")
    metrics = get_metrics()
    MONITORING_AVAILABLE = True
except ImportError:
    import logging
    logger = logging.getLogger("ia_analisadora.reports")
    metrics = None
    MONITORING_AVAILABLE = False


class CamadaReports:
    """
    Camada de geração de relatórios e visualizações.
    
    Este módulo é responsável por gerar dashboards interativos,
    relatórios HTML/PDF, rankings e visualizações dos dados analisados.
    
    Funcionalidades:
    - Dashboard com resumo executivo
    - Rankings de entidades por valor/alertas
    - Gráficos interativos (Plotly)
    - Tabelas detalhadas
    - Linha do tempo de eventos
    - Mapa de gastos
    - Organização de evidências
    - Exportação HTML/JSON/PDF
    
    Attributes:
        config (Dict[str, Any]): Configurações do gerador de relatórios
        output_dir (str): Diretório de saída para os relatórios
    
    Example:
        >>> reports = CamadaReports(config={"output_dir": "data/reports"})
        >>> dados = reports.gerar_dashboard(documentos, alertas, relacionamentos, pessoas, empresas)
        >>> html_path = reports.exportar_html(dados)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.output_dir = self.config.get("output_dir", os.path.join("data", "reports"))
        os.makedirs(self.output_dir, exist_ok=True)

    def gerar_dashboard(
        self,
        documentos: List[Documento],
        alertas: List[Alerta],
        relacionamentos: List[Relacionamento],
        pessoas: Dict[str, Pessoa],
        empresas: Dict[str, Empresa],
    ) -> Dict[str, Any]:
        """
        Gera dados completos para dashboard interativo.
        
        Args:
            documentos: Lista de documentos processados
            alertas: Lista de alertas de anomalias
            relacionamentos: Lista de relacionamentos entre entidades
            pessoas: Dicionário de pessoas identificadas
            empresas: Dicionário de empresas identificadas
        
        Returns:
            Dicionário com todos os dados do dashboard:
            - resumo: Resumo executivo
            - alertas: Resumo de alertas por tipo/severidade
            - rankings: Rankings de entidades
            - graficos: Dados para gráficos Plotly
            - tabelas: Tabelas detalhadas
            - linha_tempo: Linha do tempo de eventos
            - mapa_gastos: Mapa de gastos por região
            - evidencias: Evidências organizadas
        """
        if MONITORING_AVAILABLE and metrics:
            metrics.increment("dashboard_gerado")
        start_time = datetime.now()
        res = {
            "resumo": self._gerar_resumo(documentos, alertas),
            "alertas": self._resumo_alertas(alertas),
            "rankings": self._gerar_rankings(documentos, pessoas, empresas),
            "graficos": self._gerar_dados_graficos(documentos, alertas),
            "tabelas": self._gerar_tabelas(alertas, empresas, pessoas),
            "linha_tempo": self._gerar_linha_tempo(documentos, alertas),
            "mapa_gastos": self._gerar_mapa_gastos(documentos, empresas),
            "evidencias": self._organizar_evidencias(alertas),
        }
        duration = (datetime.now() - start_time).total_seconds()
        if MONITORING_AVAILABLE and metrics:
            metrics.record_timing("tempo_geracao_dashboard", duration)
        logger.info(f"Dashboard gerado com sucesso em {duration:.2f}s")
        return res

    def _gerar_resumo(self, documentos: List[Documento], alertas: List[Alerta]) -> Dict[str, Any]:
        """Gera resumo executivo."""
        total_valores = 0
        qtd_valores = 0
        for doc in documentos:
            for ent in doc.entidades:
                if ent.tipo.value == "valor":
                    try:
                        total_valores += abs(float(ent.normalizado))
                        qtd_valores += 1
                    except ValueError:
                        continue

        return {
            "total_documentos": len(documentos),
            "total_entidades": sum(len(d.entidades) for d in documentos),
            "total_alertas": len(alertas),
            "alertas_criticos": sum(1 for a in alertas if a.severidade == "critica"),
            "alertas_altos": sum(1 for a in alertas if a.severidade == "alta"),
            "valor_total_envolvido": total_valores,
            "qtd_valores_encontrados": qtd_valores,
            "data_analise": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }

    def _resumo_alertas(self, alertas: List[Alerta]) -> Dict[str, Any]:
        """Resumo detalhado dos alertas."""
        por_tipo = defaultdict(list)
        por_severidade = defaultdict(list)

        for alerta in alertas:
            por_tipo[alerta.tipo.value].append(alerta)
            por_severidade[alerta.severidade].append(alerta)

        return {
            "total": len(alertas),
            "por_tipo": {
                tipo: {
                    "total": len(lista),
                    "descricao": self._descricao_tipo_alerta(tipo),
                }
                for tipo, lista in por_tipo.items()
            },
            "por_severidade": {
                sev: len(lista) for sev, lista in por_severidade.items()
            },
            "lista_alertas": [
                {
                    "id": a.id,
                    "tipo": a.tipo.value,
                    "titulo": a.titulo,
                    "severidade": a.severidade,
                    "score": a.score_confianca,
                    "data": a.data_deteccao.strftime("%d/%m/%Y"),
                    "valor": a.valor_envolvido,
                }
                for a in sorted(alertas, key=lambda x: x.score_confianca, reverse=True)
            ],
        }

    def _gerar_rankings(
        self,
        documentos: List[Documento],
        pessoas: Dict[str, Pessoa],
        empresas: Dict[str, Empresa],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Gera rankings de entidades."""
        # Ranking de fornecedores (empresas)
        fornecedores = []
        for emp_id, empresa in empresas.items():
            fornecedores.append({
                "nome": empresa.nome,
                "cnpj": empresa.cnpj,
                "contratos": len(empresa.contratos),
                "score_suspeita": empresa.score_suspeita,
                "alertas": empresa.alertas,
            })
        fornecedores.sort(key=lambda x: x["contratos"], reverse=True)

        # Ranking de maiores contratos
        maiores_contratos = []
        for doc in documentos:
            for ent in doc.entidades:
                if ent.tipo.value == "valor":
                    try:
                        valor = abs(float(ent.normalizado))
                        if valor > 10000:
                            maiores_contratos.append({
                                "valor": valor,
                                "contexto": ent.contexto[:150],
                                "fonte": doc.fonte,
                            })
                    except ValueError:
                        continue
        maiores_contratos.sort(key=lambda x: x["valor"], reverse=True)

        # Ranking por município/órgão
        orgaos = defaultdict(lambda: {"gasto_total": 0, "qtd": 0, "contratos": []})
        for doc in documentos:
            orgao = doc.orgao_origem or "Não identificado"
            for ent in doc.entidades:
                if ent.tipo.value == "valor":
                    try:
                        valor = abs(float(ent.normalizado))
                        orgaos[orgao]["gasto_total"] += valor
                        orgaos[orgao]["qtd"] += 1
                    except ValueError:
                        continue

        ranking_orgaos = [
            {"orgao": nome, **dados}
            for nome, dados in orgaos.items()
        ]
        ranking_orgaos.sort(key=lambda x: x["gasto_total"], reverse=True)

        return {
            "fornecedores": fornecedores[:50],
            "maiores_contratos": maiores_contratos[:50],
            "orgaos": ranking_orgaos[:50],
        }

    def _gerar_dados_graficos(
        self,
        documentos: List[Documento],
        alertas: List[Alerta],
    ) -> Dict[str, Any]:
        """Gera dados para gráficos."""
        # Gráfico de alertas por tipo
        alertas_tipo = Counter(a.tipo.value for a in alertas)

        # Gráfico de alertas por severidade
        alertas_severidade = Counter(a.severidade for a in alertas)

        # Gráfico de evolução temporal
        alertas_tempo = defaultdict(int)
        for a in alertas:
            dia = a.data_deteccao.strftime("%d/%m")
            alertas_tempo[dia] += 1

        # Distribuição de valores
        valores = []
        for doc in documentos:
            for ent in doc.entidades:
                if ent.tipo.value == "valor":
                    try:
                        v = abs(float(ent.normalizado))
                        if 100 < v < 1_000_000_000:
                            valores.append(v)
                    except ValueError:
                        continue

        return {
            "alertas_por_tipo": dict(alertas_tipo),
            "alertas_por_severidade": dict(alertas_severidade),
            "alertas_por_dia": dict(sorted(alertas_tempo.items())),
            "distribuicao_valores": {
                "media": statistics.mean(valores) if valores else 0,
                "mediana": statistics.median(valores) if valores else 0,
                "max": max(valores) if valores else 0,
                "min": min(valores) if valores else 0,
                "total": sum(valores),
            },
        }

    def _gerar_tabelas(
        self,
        alertas: List[Alerta],
        empresas: Dict[str, Empresa],
        pessoas: Dict[str, Pessoa],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Gera tabelas de dados."""
        return {
            "alertas_recentes": [
                {
                    "data": a.data_deteccao.strftime("%d/%m/%Y"),
                    "tipo": a.tipo.value,
                    "titulo": a.titulo,
                    "severidade": a.severidade.upper(),
                    "score": f"{a.score_confianca:.0%}",
                }
                for a in sorted(alertas, key=lambda x: x.data_deteccao, reverse=True)[:100]
            ],
            "empresas_suspeitas": [
                {
                    "nome": e.nome,
                    "cnpj": e.cnpj or "-",
                    "contratos": len(e.contratos),
                    "score": f"{e.score_suspeita:.2f}",
                    "alertas": len(e.alertas),
                }
                for e in sorted(
                    empresas.values(),
                    key=lambda x: x.score_suspeita,
                    reverse=True,
                )[:50]
            ],
        }

    def _gerar_linha_tempo(
        self,
        documentos: List[Documento],
        alertas: List[Alerta],
    ) -> List[Dict[str, Any]]:
        """Gera linha do tempo de eventos."""
        eventos = []

        for doc in documentos:
            eventos.append({
                "data": doc.data_processamento.strftime("%d/%m/%Y %H:%M"),
                "tipo": "documento",
                "descricao": f"Documento processado: {os.path.basename(doc.fonte)}",
                "severidade": "info",
            })

        for alerta in alertas:
            eventos.append({
                "data": alerta.data_deteccao.strftime("%d/%m/%Y %H:%M"),
                "tipo": "alerta",
                "descricao": alerta.titulo,
                "severidade": alerta.severidade,
            })

        eventos.sort(key=lambda x: x["data"], reverse=True)
        return eventos[:200]

    def _gerar_mapa_gastos(
        self,
        documentos: List[Documento],
        empresas: Dict[str, Empresa],
    ) -> Dict[str, Any]:
        """
        Gera dados de gastos agrupados geograficamente.
        """
        gastos_uf = defaultdict(float)
        gastos_municipio = defaultdict(float)

        for doc in documentos:
            uf = doc.metadados.get("uf", "")
            municipio = doc.metadados.get("municipio", "")
            for ent in doc.entidades:
                if ent.tipo.value == "valor":
                    try:
                        valor = abs(float(ent.normalizado))
                        if uf:
                            gastos_uf[uf] += valor
                        if municipio:
                            gastos_municipio[municipio] += valor
                    except ValueError:
                        continue

        return {
            "gastos_por_uf": dict(sorted(gastos_uf.items(), key=lambda x: -x[1])),
            "gastos_por_municipio": dict(sorted(gastos_municipio.items(), key=lambda x: -x[1])[:20]),
        }

    def _organizar_evidencias(self, alertas: List[Alerta]) -> Dict[str, List[Dict[str, Any]]]:
        """Organiza evidências por tipo de alerta."""
        evidencias = defaultdict(list)

        for alerta in alertas:
            evidencias[alerta.tipo.value].append({
                "id": alerta.id,
                "titulo": alerta.titulo,
                "descricao": alerta.descricao,
                "severidade": alerta.severidade,
                "confianca": f"{alerta.score_confianca:.0%}",
                "data": alerta.data_deteccao.strftime("%d/%m/%Y"),
                "status": alerta.status,
                "valor": alerta.valor_envolvido,
                "documentos": alerta.documentos_relacionados[:5],
                "entidades": alerta.entidades_envolvidas[:5],
            })

        return dict(evidencias)

    def gerar_relatorio_denuncia(self, alerta: Alerta, evidencias: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Gera relatório de denúncia completo para um alerta."""
        return {
            "tipo": "denuncia",
            "titulo": alerta.titulo,
            "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "resumo": alerta.descricao,
            "detalhes": {
                "tipo_anomalia": alerta.tipo.value,
                "severidade": alerta.severidade,
                "confianca": f"{alerta.score_confianca:.0%}",
                "data_deteccao": alerta.data_deteccao.strftime("%d/%m/%Y"),
                "status": alerta.status,
                "valor_envolvido": alerta.valor_envolvido,
            },
            "evidencias": evidencias,
            "entidades_envolvidas": alerta.entidades_envolvidas,
            "documentos_relacionados": alerta.documentos_relacionados,
        }

    def gerar_relatorio_geral(self, dados_dashboard: Dict[str, Any]) -> Relatorio:
        """Gera relatório geral em formato estruturado."""
        relatorio_id = str(uuid.uuid4())

        return Relatorio(
            id=relatorio_id,
            titulo="Relatório Geral de Análise de Documentos Públicos",
            tipo="analise",
            dados=dados_dashboard,
            tabelas=dados_dashboard.get("tabelas", {}),
            alertas_incluidos=[a["id"] for a in dados_dashboard.get("alertas", {}).get("lista_alertas", [])],
            metadados={
                "versao": "1.0",
                "motor": "IA Analisadora - Cérebro da Transparência",
                "data_analise": datetime.now().isoformat(),
            },
        )

    def exportar_json(self, dados: Dict[str, Any], nome: str = "relatorio") -> str:
        """Exporta dados para JSON."""
        caminho = os.path.join(self.output_dir, f"{nome}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2, default=str)
        return caminho

    def exportar_pdf(self, dados_dashboard: Dict[str, Any]) -> Optional[str]:
        """
        Gera relatório PDF a partir do HTML usando WeasyPrint.
        Retorna o caminho do PDF ou None se WeasyPrint não estiver disponível.
        """
        try:
            from weasyprint import HTML
            html_content = self._gerar_html_template(dados_dashboard)
            caminho = os.path.join(
                self.output_dir,
                f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            HTML(string=html_content).write_pdf(caminho)
            return caminho
        except ImportError:
            logger.warning("weasyprint não instalado. PDF não gerado. Use: pip install weasyprint")
            return None
        except Exception as e:
            logger.error(f"Falha ao gerar PDF: {e}")
            return None

    def gerar_graficos_plotly(self, dados_dashboard: Dict[str, Any]) -> str:
        """
        Gera gráficos interativos com Plotly e retorna HTML embutido.
        Inclui gráficos de alertas por tipo, severidade e distribuição de valores.
        """
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
        except ImportError:
            return "<p>Gráficos não disponíveis (plotly não instalado).</p>"

        graficos = dados_dashboard.get("graficos", {})
        resumo = dados_dashboard.get("resumo", {})

        # Subplots: 2 colunas
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("Alertas por Tipo", "Alertas por Severidade",
                            "Distribuição de Valores", "Resumo"),
            specs=[
                [{"type": "bar"}, {"type": "pie"}],
                [{"type": "bar"}, {"type": "indicator"}],
            ],
        )

        # Gráfico 1: Alertas por tipo
        alertas_tipo = graficos.get("alertas_por_tipo", {})
        if alertas_tipo:
            fig.add_trace(
                go.Bar(x=list(alertas_tipo.keys()), y=list(alertas_tipo.values()),
                       name="Alertas", marker_color="#ff4444"),
                row=1, col=1
            )

        # Gráfico 2: Alertas por severidade (pizza)
        alertas_sev = graficos.get("alertas_por_severidade", {})
        if alertas_sev:
            cores = {"critica": "#ff0000", "alta": "#ff6600", "media": "#ffaa00", "baixa": "#00d4ff"}
            fig.add_trace(
                go.Pie(labels=list(alertas_sev.keys()), values=list(alertas_sev.values()),
                       name="Severidade",
                       marker=dict(colors=[cores.get(k, "#8899aa") for k in alertas_sev.keys()])),
                row=1, col=2
            )

        # Gráfico 3: Distribuição de valores
        dist = graficos.get("distribuicao_valores", {})
        if dist:
            fig.add_trace(
                go.Bar(x=["Mínimo", "Média", "Mediana", "Máximo", "Total"],
                       y=[dist.get("min", 0), dist.get("media", 0), dist.get("mediana", 0),
                          dist.get("max", 0), dist.get("total", 0)],
                       name="Valores", marker_color="#00ff88"),
                row=2, col=1
            )

        # Gráfico 4: Indicador de resumo
        fig.add_trace(
            go.Indicator(
                mode="number",
                value=resumo.get("total_alertas", 0),
                title={"text": "Total de Alertas"},
                number={"font": {"color": "#ff4444", "size": 40}},
            ),
            row=2, col=2
        )

        fig.update_layout(
            height=600,
            showlegend=False,
            paper_bgcolor="#0f1923",
            plot_bgcolor="#1a2a3a",
            font=dict(color="#e0e0e0", family="Segoe UI"),
        )

        return fig.to_html(full_html=False, include_plotlyjs="cdn")

    def exportar_html(self, dados_dashboard: Dict[str, Any]) -> str:
        """Gera relatório HTML com visualizações e gráficos interativos."""
        # Gera gráficos Plotly para embutir no HTML
        graficos_html = self.gerar_graficos_plotly(dados_dashboard)
        html = self._gerar_html_template(dados_dashboard, graficos_html)
        caminho = os.path.join(self.output_dir, f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(html)
        return caminho

    def _gerar_html_template(self, dados: Dict[str, Any], graficos_html: str = "") -> str:
        """Gera template HTML para o relatório."""
        resumo = dados.get("resumo", {})
        alertas = dados.get("alertas", {})
        rankings = dados.get("rankings", {})
        graficos = dados.get("graficos", {})

        # Cards de resumo
        cards = f"""
        <div class="cards-container">
            <div class="card critical"><h3>Alertas Críticos</h3><p>{resumo.get('alertas_criticos', 0)}</p></div>
            <div class="card high"><h3>Alertas Altos</h3><p>{resumo.get('alertas_altos', 0)}</p></div>
            <div class="card info"><h3>Documentos</h3><p>{resumo.get('total_documentos', 0)}</p></div>
            <div class="card total"><h3>Valor Envolvido</h3><p>R$ {resumo.get('valor_total_envolvido', 0):,.2f}</p></div>
        </div>
        """

        # Tabela de alertas
        tabela_alertas = """
        <table>
            <tr><th>Tipo</th><th>Título</th><th>Severidade</th><th>Confiança</th></tr>
        """
        for a in alertas.get("lista_alertas", [])[:20]:
            tabela_alertas += f"""
            <tr class="{a['severidade']}">
                <td>{a['tipo']}</td>
                <td>{a['titulo']}</td>
                <td>{a['severidade'].upper()}</td>
                <td>{a['score']:.0%}</td>
            </tr>
            """
        tabela_alertas += "</table>"

        # Ranking de fornecedores
        tabela_fornecedores = """
        <table>
            <tr><th>Fornecedor</th><th>CNPJ</th><th>Contratos</th><th>Score</th></tr>
        """
        for f in rankings.get("fornecedores", [])[:20]:
            tabela_fornecedores += f"""
            <tr>
                <td>{f['nome']}</td>
                <td>{f.get('cnpj', '-')}</td>
                <td>{f['contratos']}</td>
                <td>{f.get('score_suspeita', 0):.2f}</td>
            </tr>
            """
        tabela_fornecedores += "</table>"

        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatório - IA Analisadora</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', system-ui, sans-serif; }}
        body {{ background: #0B1120; color: #E2E8F0; padding: 30px; line-height: 1.6; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ color: #38BDF8; margin-bottom: 30px; border-bottom: 1px solid rgba(56, 189, 248, 0.2); padding-bottom: 15px; font-weight: 700; font-size: 2.2rem; }}
        h2 {{ color: #F8FAFC; margin: 40px 0 20px; font-weight: 600; font-size: 1.5rem; }}
        .cards-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px; margin: 30px 0; }}
        .card {{ padding: 30px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.4); backdrop-filter: blur(10px); transition: transform 0.2s; }}
        .card:hover {{ transform: translateY(-5px); }}
        .card.critical {{ background: linear-gradient(145deg, rgba(153, 27, 27, 0.4), rgba(127, 29, 29, 0.8)); border: 1px solid rgba(248, 113, 113, 0.3); }}
        .card.high {{ background: linear-gradient(145deg, rgba(154, 52, 18, 0.4), rgba(124, 45, 18, 0.8)); border: 1px solid rgba(251, 146, 60, 0.3); }}
        .card.info {{ background: linear-gradient(145deg, rgba(30, 64, 175, 0.4), rgba(30, 58, 138, 0.8)); border: 1px solid rgba(96, 165, 250, 0.3); }}
        .card.total {{ background: linear-gradient(145deg, rgba(21, 128, 61, 0.4), rgba(20, 83, 45, 0.8)); border: 1px solid rgba(74, 222, 128, 0.3); }}
        .card h3 {{ font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 15px; color: #CBD5E1; font-weight: 600; }}
        .card p {{ font-size: 2.5rem; font-weight: 700; color: #FFFFFF; }}
        table {{ width: 100%; border-collapse: separate; border-spacing: 0; margin: 20px 0; background: rgba(30, 41, 59, 0.5); border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }}
        th, td {{ padding: 16px 20px; text-align: left; }}
        th {{ background: rgba(15, 23, 42, 0.8); color: #94A3B8; font-weight: 600; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 1px; border-bottom: 2px solid rgba(255,255,255,0.05); }}
        td {{ border-bottom: 1px solid rgba(255,255,255,0.05); color: #F1F5F9; }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover td {{ background: rgba(51, 65, 85, 0.5); }}
        tr.critical td:first-child {{ box-shadow: inset 4px 0 0 #EF4444; }}
        tr.high td:first-child {{ box-shadow: inset 4px 0 0 #F97316; }}
        tr.media td:first-child {{ box-shadow: inset 4px 0 0 #EAB308; }}
        .section {{ background: rgba(30, 41, 59, 0.3); border-radius: 16px; padding: 30px; margin: 30px 0; border: 1px solid rgba(255,255,255,0.05); }}
        .footer {{ margin-top: 60px; text-align: center; color: #64748B; font-size: 0.85rem; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.05); }}
        @media print {{ body {{ background: white; color: black; }} .section {{ background: #F8FAFC; border: 1px solid #E2E8F0; }} th {{ background: #F1F5F9; color: #334155; }} td {{ color: #0F172A; }} }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Relatório de Análise - IA Analisadora</h1>
        <p>Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
        {cards}

        <div class="section">
            <h2>📊 Alertas Detectados</h2>
            {tabela_alertas}
        </div>

        <div class="section">
            <h2>🏢 Ranking de Fornecedores</h2>
            {tabela_fornecedores}
        </div>

        <div class="section">
            <h2>📈 Gráficos Interativos</h2>
            {graficos_html}
        </div>

        <div class="section">
            <h2>📊 Distribuição de Valores</h2>
            <p>Média: R$ {graficos.get('distribuicao_valores', dict()).get('media', 0):,.2f}</p>
            <p>Mediana: R$ {graficos.get('distribuicao_valores', dict()).get('mediana', 0):,.2f}</p>
            <p>Total: R$ {graficos.get('distribuicao_valores', dict()).get('total', 0):,.2f}</p>
            <p>Maior valor: R$ {graficos.get('distribuicao_valores', dict()).get('max', 0):,.2f}</p>
        </div>

        <div class="footer">
            <p>IA Analisadora - "O Cérebro da Transparência" v1.0</p>
            <p>Documentos Públicos • OCR • NLP • Graph Database • Detecção de Anomalias</p>
        </div>
    </div>
</body>
</html>"""
        return html

    def _descricao_tipo_alerta(self, tipo: str) -> str:
        """Retorna descrição do tipo de alerta."""
        descricoes = {
            "superfaturamento": "Valores pagos muito acima da média de mercado",
            "nepotismo": "Parentes de agentes públicos contratados",
            "cartel": "Empresas com padrão suspeito em licitações",
            "fracionamento": "Compras fracionadas para evitar licitação",
            "empresa_fantasma": "Empresas com características suspeitas",
            "conflito_interesse": "Agente público sócio de empresa contratada",
            "empresa_recem_criada": "Empresas novas com contratos públicos",
            "endereco_repetido": "Múltiplas empresas suspeitas no mesmo endereço",
            "socio_repetido": "Mesma pessoa como sócia de múltiplas empresas",
            "valor_acima_media": "Valores individuais acima da média",
            "suspeita_fraude": "Múltiplos indicadores de irregularidade",
            "pagamento_sem_licitacao": "Pagamentos sem processo licitatório",
            "prazo_curto": "Contratos com prazos suspeitosamente curtos",
        }
        return descricoes.get(tipo, "Anomalia detectada automaticamente")
