"""Testa SO a renderizacao das tabelas de Projeto Funcional em um slide.

Copia o template, le a planilha COPEL (Projeto Funcional), monta as 3 tabelas
(concluidos/pendentes/em andamento) nos slides 6/7/8 e imprime o link da copia.

Nao depende do calendario nem do indice: usa o link da planilha direto. Serve
para iterar rapido no visual das tabelas.
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from status_report.aplicacao.projeto_funcional import agrupar_por_status
from status_report.aplicacao.render_projeto_funcional import (
    renderizar_tabelas_projeto_funcional,
)
from status_report.configuracao import carregar_configuracoes
from status_report.infraestrutura.autenticacao_google import (
    construir_servicos_google,
)
from status_report.infraestrutura.repositorio_apresentacao import (
    aplicar_substituicoes,
)
from status_report.infraestrutura.repositorio_drive import (
    copiar_apresentacao,
    criar_ou_obter_subpasta,
    obter_link_arquivo,
)
from status_report.infraestrutura.repositorio_projeto_funcional import (
    extrair_id_planilha,
    ler_itens_projeto_funcional,
)

LINK_PROJETO = "https://docs.google.com/spreadsheets/d/1eR-aFsMqWkmyCgbKcYVLLVeZ9A5J94IQ/edit?gid=1571195596#gid=1571195596"


def main() -> None:
    config = carregar_configuracoes()
    servicos = construir_servicos_google(config)
    hoje = date.today()

    print("Lendo planilha de Projeto Funcional...")
    _, itens = ler_itens_projeto_funcional(
        servicos.sheets, servicos.drive, extrair_id_planilha(LINK_PROJETO)
    )
    grupos = agrupar_por_status(itens)
    print(
        f"  Concluidos={grupos.total_concluidos} "
        f"Em andamento={grupos.total_em_andamento} "
        f"Pendentes={grupos.total_pendentes}"
    )

    print("Copiando template...")
    id_subpasta = criar_ou_obter_subpasta(
        drive=servicos.drive,
        id_pasta_pai=config.id_pasta_saida,
        nome="TESTE_TABELAS",
    )
    id_copia = copiar_apresentacao(
        drive=servicos.drive,
        id_modelo=config.id_apresentacao_modelo,
        nome_da_copia=f"TESTE_TABELAS - {hoje.isoformat()}",
        id_pasta_destino=id_subpasta,
    )

    print("Montando tabelas nos slides 6/7/8...")
    substituicoes_qtd = renderizar_tabelas_projeto_funcional(
        slides=servicos.slides,
        presentation_id=id_copia,
        grupos=grupos,
    )
    aplicar_substituicoes(
        slides=servicos.slides,
        id_apresentacao=id_copia,
        substituicoes=substituicoes_qtd,
    )

    link = obter_link_arquivo(drive=servicos.drive, id_arquivo=id_copia)
    print("\nPronto! Abra a copia para conferir as tabelas:")
    print(f"  {link}")


if __name__ == "__main__":
    main()
