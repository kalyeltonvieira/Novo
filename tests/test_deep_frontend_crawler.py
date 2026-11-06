"""
Testes Unitários do Deep Frontend Crawler
==========================================
"""

import pytest
from core.deep_frontend_crawler import DeepFrontendCrawler


def test_extrair_shadow_dom():
    crawler = DeepFrontendCrawler()
    html = '<div id="app"><template shadowroot="open"><p>Dados Protegidos</p></template></div>'
    res = crawler.extrair_shadow_dom(html)
    assert res["possui_shadow_dom"] is True
    assert len(res["elementos_extraidos"]) == 1


def test_inspecionar_iframes():
    crawler = DeepFrontendCrawler()
    iframes = ["https://site.gov.br/banner.html", "https://site.gov.br/tabela_licitacoes.php"]
    res = crawler.inspecionar_iframes(iframes)
    assert res["total_iframes"] == 2
    assert len(res["iframes_criticos"]) == 1
