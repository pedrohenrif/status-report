"""Utilitarios para limpar e preparar slides de Projeto Funcional (6/7/8)."""
from __future__ import annotations

_MARCADORES_TITULO = (
    "projeto funcional",
    "{{qtd_concluidos}}",
    "{{qtd_pendentes}}",
    "{{qtd_em_andamento}}",
    "concluído",
    "concluido",
    "pendente",
    "andamento",
)


def texto_do_elemento(elemento: dict) -> str:
    """Extrai texto de um pageElement do tipo shape."""
    shape = elemento.get("shape")
    if not shape:
        return ""
    partes: list[str] = []
    for bloco in shape.get("text", {}).get("textElements", []):
        trecho = bloco.get("textRun", {}).get("content", "")
        if trecho:
            partes.append(trecho)
    return "".join(partes)


def eh_titulo_projeto_funcional(elemento: dict) -> bool:
    """Mantem caixas de texto do titulo dos slides 6/7/8."""
    if "shape" not in elemento:
        return False
    texto = texto_do_elemento(elemento).strip()
    if not texto:
        return False
    lower = texto.lower()
    return any(marcador in lower for marcador in _MARCADORES_TITULO)


def ids_elementos_removiveis(page_elements: list[dict]) -> list[str]:
    """Retorna IDs de tudo que nao e titulo (imagens, tabelas antigas, formas)."""
    return [
        elemento["objectId"]
        for elemento in page_elements
        if not eh_titulo_projeto_funcional(elemento)
    ]


def requests_remover_elementos(object_ids: list[str]) -> list[dict]:
    return [{"deleteObject": {"objectId": object_id}} for object_id in object_ids]


_POL = 914400
# Margens laterais simetricas: tabela ~9" em slide de 10", centralizada.
_MARGEM_LATERAL_POLEGADAS = 0.50
_MARGEM_APOS_TITULO_POLEGADAS = 0.12
_MARGEM_INFERIOR_POLEGADAS = 0.38
_Y_PADRAO_POLEGADAS = 1.95


def calcular_layout_tabela(
    largura_slide_polegadas: float,
    altura_slide_polegadas: float,
    page_elements: list[dict],
) -> dict[str, float]:
    """Calcula posicao e largura da tabela com base no slide e no titulo."""
    largura_tabela = largura_slide_polegadas - 2 * _MARGEM_LATERAL_POLEGADAS
    x_tabela = (largura_slide_polegadas - largura_tabela) / 2
    titulos = [elemento for elemento in page_elements if eh_titulo_projeto_funcional(elemento)]
    if titulos:
        y_tabela = (
            max(_fundo_inferior_polegadas(elemento) for elemento in titulos)
            + _MARGEM_APOS_TITULO_POLEGADAS
        )
    else:
        y_tabela = _Y_PADRAO_POLEGADAS

    return {
        "x_polegadas": x_tabela,
        "y_polegadas": max(y_tabela, 1.5),
        "largura_polegadas": largura_tabela,
        "altura_slide_polegadas": altura_slide_polegadas,
        "margem_inferior_polegadas": _MARGEM_INFERIOR_POLEGADAS,
    }


def _fundo_inferior_polegadas(elemento: dict) -> float:
    transform = elemento.get("transform", {})
    tamanho = elemento.get("size", {})
    translate_y = transform.get("translateY", 0)
    altura = tamanho.get("height", {}).get("magnitude", 0)
    escala_y = transform.get("scaleY", 1) or 1
    return (translate_y + altura * escala_y) / _POL

