"""Interface grafica (tkinter) do Gerador de Status Report - GHR."""
from __future__ import annotations

import queue
import re
import threading
import tkinter as tk
from dataclasses import replace
from datetime import date, datetime
from tkinter import font as tkfont
from tkinter import ttk

from status_report.recursos import caminho_logo

_RE_CODIGO_NEGOCIO = re.compile(r"(\d{3,4}-\d{2})")

# --- Paleta GHR --------------------------------------------------------------
COR_PRIMARIA = "#12559C"       # azul GHR
COR_PRIMARIA_ESC = "#0C3B6E"   # azul escuro (cabecalho)
COR_PRIMARIA_HOVER = "#0E4A87"
COR_ACENTO = "#3D8ED9"         # azul claro (detalhes)
COR_SUCESSO = "#1E8E5A"
COR_SUCESSO_HOVER = "#187048"
COR_FUNDO = "#EEF2F7"          # fundo da janela
COR_CARD = "#FFFFFF"
COR_CAMPO = "#F1F4F9"
COR_BORDA = "#DCE3EC"
COR_TEXTO = "#22303F"
COR_TEXTO_SUAVE = "#6B7A8D"
COR_DESABILITADO = "#B4BFCB"

# Feed de acompanhamento (tema claro)
FEED_OK = "#178A55"
FEED_ERRO = "#C23B34"
FEED_AVISO = "#B9771A"
FEED_INFO = "#5A6A7B"

FONTE = "Segoe UI"

_ICONES = {"ok": "✓", "erro": "✕", "aviso": "⚠", "info": "•"}


# --- Desenho de cantos arredondados ------------------------------------------

def _desenhar_arredondado(canvas: tk.Canvas, x1, y1, x2, y2, raio, **kw):
    pontos = [
        x1 + raio, y1, x2 - raio, y1, x2, y1, x2, y1 + raio,
        x2, y2 - raio, x2, y2, x2 - raio, y2, x1 + raio, y2,
        x1, y2, x1, y2 - raio, x1, y1 + raio, x1, y1,
    ]
    return canvas.create_polygon(pontos, smooth=True, **kw)


class CartaoArredondado(tk.Canvas):
    """Container com cantos arredondados. Conteudo vai em ``.inner``."""

    def __init__(self, master, *, raio=16, cor=COR_CARD, cor_fundo=COR_FUNDO,
                 borda=COR_BORDA, expandir=False, padding=18):
        super().__init__(master, bg=cor_fundo, highlightthickness=0, bd=0, height=60)
        self._raio = raio
        self._cor = cor
        self._borda = borda
        self._expandir = expandir
        self._pad = padding
        self._rect = None
        self.inner = tk.Frame(self, bg=cor)
        self._win = self.create_window(padding, padding, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._ao_inner)
        self.bind("<Configure>", self._ao_canvas)

    def _ao_inner(self, _e=None):
        if not self._expandir:
            self.configure(height=self.inner.winfo_reqheight() + 2 * self._pad)

    def _ao_canvas(self, e):
        self.itemconfigure(self._win, width=max(1, e.width - 2 * self._pad))
        if self._expandir:
            self.itemconfigure(self._win, height=max(1, e.height - 2 * self._pad))
        if self._rect:
            self.delete(self._rect)
        self._rect = _desenhar_arredondado(
            self, 1, 1, e.width - 1, e.height - 1, self._raio,
            fill=self._cor, outline=self._borda, width=1,
        )
        self.tag_lower(self._rect)


class BotaoArredondado(tk.Canvas):
    def __init__(self, master, texto, comando, *, cor, cor_hover,
                 cor_texto=COR_CARD, raio=12, cor_fundo=COR_FUNDO,
                 pad_x=22, pad_y=11, tamanho=11, negrito=True):
        super().__init__(master, bg=cor_fundo, highlightthickness=0, bd=0)
        self._comando = comando
        self._cor = cor
        self._cor_hover = cor_hover
        self._cor_texto = cor_texto
        self._raio = raio
        self._pad_x = pad_x
        self._pad_y = pad_y
        self._habilitado = True
        self._texto = texto
        self._fonte = tkfont.Font(family=FONTE, size=tamanho,
                                  weight="bold" if negrito else "normal")
        self._rect = None
        self._lbl = None
        self.bind("<Button-1>", self._ao_clicar)
        self.bind("<Enter>", lambda _e: self._pintar(self._cor_hover))
        self.bind("<Leave>", lambda _e: self._pintar(self._cor))
        self._relayout()

    def _relayout(self):
        larg = self._fonte.measure(self._texto) + 2 * self._pad_x
        alt = self._fonte.metrics("linespace") + 2 * self._pad_y
        self.configure(width=larg, height=alt, cursor="hand2" if self._habilitado else "arrow")
        self.delete("all")
        cor = self._cor if self._habilitado else COR_DESABILITADO
        self._rect = _desenhar_arredondado(self, 1, 1, larg - 1, alt - 1, self._raio,
                                           fill=cor, outline=cor)
        self._lbl = self.create_text(larg / 2, alt / 2, text=self._texto,
                                     fill=self._cor_texto, font=self._fonte)

    def _pintar(self, cor):
        if self._habilitado and self._rect:
            self.itemconfigure(self._rect, fill=cor, outline=cor)

    def _ao_clicar(self, _e):
        if self._habilitado and self._comando:
            self._comando()

    def definir_texto(self, texto):
        self._texto = texto
        self._relayout()

    def definir_habilitado(self, habilitado):
        self._habilitado = habilitado
        self._relayout()


class CampoArredondado(tk.Canvas):
    def __init__(self, master, variavel, *, largura_px=300, cor_fundo=COR_CARD, raio=10):
        super().__init__(master, bg=cor_fundo, highlightthickness=0, bd=0,
                         width=largura_px, height=40)
        self._raio = raio
        self._cor_borda = COR_BORDA
        self._rect = None
        self.entry = tk.Entry(self, textvariable=variavel, font=(FONTE, 11),
                              relief="flat", bd=0, bg=COR_CAMPO, fg=COR_TEXTO,
                              highlightthickness=0, insertbackground=COR_TEXTO)
        self._win = self.create_window(14, 20, window=self.entry, anchor="w")
        self.entry.bind("<FocusIn>", lambda _e: self._definir_borda(COR_ACENTO))
        self.entry.bind("<FocusOut>", lambda _e: self._definir_borda(COR_BORDA))
        self.bind("<Configure>", self._redesenhar)

    def _redesenhar(self, _e=None):
        w = self.winfo_width()
        h = self.winfo_height()
        self.itemconfigure(self._win, width=w - 26)
        if self._rect:
            self.delete(self._rect)
        self._rect = _desenhar_arredondado(self, 1, 1, w - 1, h - 1, self._raio,
                                           fill=COR_CAMPO, outline=self._cor_borda, width=1)
        self.tag_lower(self._rect)

    def _definir_borda(self, cor):
        self._cor_borda = cor
        self._redesenhar()

    def focus(self):
        self.entry.focus()


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Gerador de Status Report — GHR")
        self.geometry("800x700")
        self.minsize(740, 640)
        self.configure(bg=COR_FUNDO)

        self._fila_log: queue.Queue[tuple[str, str]] = queue.Queue()
        self._clientes: list = []
        self._projetos_por_cliente: list[list] = []
        self._combos: list = []
        self._mapa_rotulo_proj: list[dict] = []
        self._config = None
        self._servicos = None
        self._logo_img: tk.PhotoImage | None = None
        self._ocupado = False

        self._construir_ui()
        self._registrar_invalidacao()
        self._verificar_fila_log()

    # ------------------------------------------------------------------
    # Construcao da UI
    # ------------------------------------------------------------------

    def _configurar_estilo_ttk(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "GHR.TCombobox",
            fieldbackground=COR_CARD,
            background=COR_CARD,
            foreground=COR_TEXTO,
            arrowcolor=COR_PRIMARIA,
            bordercolor=COR_BORDA,
            lightcolor=COR_BORDA,
            darkcolor=COR_BORDA,
            relief="flat",
            padding=7,
            arrowsize=15,
        )
        style.map(
            "GHR.TCombobox",
            fieldbackground=[("readonly", COR_CARD), ("focus", COR_CARD)],
            selectbackground=[("readonly", COR_CARD)],
            selectforeground=[("readonly", COR_TEXTO)],
            bordercolor=[("focus", COR_ACENTO), ("active", COR_ACENTO)],
            arrowcolor=[("active", COR_PRIMARIA_HOVER)],
        )
        self.option_add("*TCombobox*Listbox.background", COR_CARD)
        self.option_add("*TCombobox*Listbox.foreground", COR_TEXTO)
        self.option_add("*TCombobox*Listbox.selectBackground", COR_ACENTO)
        self.option_add("*TCombobox*Listbox.selectForeground", COR_CARD)
        self.option_add("*TCombobox*Listbox.font", (FONTE, 9))
        self.option_add("*TCombobox*Listbox.borderWidth", 0)

    def _construir_ui(self) -> None:
        self._configurar_estilo_ttk()
        self._construir_cabecalho()
        corpo = tk.Frame(self, bg=COR_FUNDO)
        corpo.pack(fill="both", expand=True, padx=24, pady=(18, 22))
        self._construir_formulario(corpo)
        self._construir_clientes(corpo)
        self._construir_acompanhamento(corpo)

    def _construir_cabecalho(self) -> None:
        barra = tk.Frame(self, bg=COR_PRIMARIA_ESC)
        barra.pack(fill="x")
        interno = tk.Frame(barra, bg=COR_PRIMARIA_ESC)
        interno.pack(fill="x", padx=24, pady=16)

        logo = self._carregar_logo()
        if logo is not None:
            self._logo_img = logo
            tk.Label(interno, image=logo, bg=COR_PRIMARIA_ESC).pack(side="left", padx=(0, 16))

        textos = tk.Frame(interno, bg=COR_PRIMARIA_ESC)
        textos.pack(side="left", anchor="w")
        tk.Label(textos, text="Gerador de Status Report", bg=COR_PRIMARIA_ESC,
                 fg=COR_CARD, font=(FONTE, 18, "bold")).pack(anchor="w")
        tk.Label(textos, text="GHR Tech · Automação de Relatórios", bg=COR_PRIMARIA_ESC,
                 fg=COR_ACENTO, font=(FONTE, 10)).pack(anchor="w")

        tk.Frame(self, bg=COR_ACENTO, height=3).pack(fill="x")

    def _construir_formulario(self, pai: tk.Frame) -> None:
        card = CartaoArredondado(pai)
        card.pack(fill="x")
        corpo = card.inner

        grade = tk.Frame(corpo, bg=COR_CARD)
        grade.pack(fill="x", padx=6, pady=(4, 2))

        tk.Label(grade, text="COORDENADORA", bg=COR_CARD, font=(FONTE, 8, "bold"),
                 fg=COR_TEXTO_SUAVE).grid(row=0, column=0, sticky="w")
        self._var_coordenadora = tk.StringVar()
        campo_coord = CampoArredondado(grade, self._var_coordenadora, largura_px=320)
        campo_coord.grid(row=1, column=0, pady=(4, 0), sticky="w")
        campo_coord.focus()

        tk.Label(grade, text="DATA (DD/MM/AAAA)", bg=COR_CARD, font=(FONTE, 8, "bold"),
                 fg=COR_TEXTO_SUAVE).grid(row=0, column=1, sticky="w", padx=(18, 0))
        self._var_data = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))
        campo_data = CampoArredondado(grade, self._var_data, largura_px=150)
        campo_data.grid(row=1, column=1, pady=(4, 0), padx=(18, 0), sticky="w")

        btn_hoje = BotaoArredondado(
            grade, "Hoje",
            lambda: self._var_data.set(date.today().strftime("%d/%m/%Y")),
            cor=COR_CAMPO, cor_hover=COR_BORDA, cor_texto=COR_TEXTO,
            cor_fundo=COR_CARD, raio=10, pad_x=14, pad_y=9, tamanho=9, negrito=False,
        )
        btn_hoje.grid(row=1, column=2, padx=(8, 0), pady=(4, 0), sticky="w")

        acoes = tk.Frame(corpo, bg=COR_CARD)
        acoes.pack(fill="x", padx=6, pady=(16, 4))
        self._btn_buscar = BotaoArredondado(
            acoes, "Buscar clientes", self._ao_buscar,
            cor=COR_PRIMARIA, cor_hover=COR_PRIMARIA_HOVER, cor_fundo=COR_CARD,
        )
        self._btn_buscar.pack(side="left")
        self._btn_gerar = BotaoArredondado(
            acoes, "Gerar Status Reports", self._ao_gerar,
            cor=COR_SUCESSO, cor_hover=COR_SUCESSO_HOVER, cor_fundo=COR_CARD,
        )
        self._btn_gerar.pack(side="left", padx=(10, 0))
        self._btn_gerar.definir_habilitado(False)

    def _construir_clientes(self, pai: tk.Frame) -> None:
        card = CartaoArredondado(pai)
        card.pack(fill="x", pady=(14, 0))
        corpo = card.inner

        topo = tk.Frame(corpo, bg=COR_CARD)
        topo.pack(fill="x", padx=6)
        tk.Label(topo, text="Clientes do dia", bg=COR_CARD, font=(FONTE, 11, "bold"),
                 fg=COR_TEXTO).pack(side="left")
        self._lbl_contador = tk.Label(topo, text="", bg=COR_ACENTO, fg=COR_CARD,
                                      font=(FONTE, 9, "bold"), padx=9, pady=1)

        self._clientes_container = tk.Frame(corpo, bg=COR_CARD)
        self._clientes_container.pack(fill="x", padx=6, pady=(10, 2))
        self._render_placeholder_clientes()

    def _construir_acompanhamento(self, pai: tk.Frame) -> None:
        card = CartaoArredondado(pai, expandir=True)
        card.pack(fill="both", expand=True, pady=(14, 0))
        corpo = card.inner

        topo = tk.Frame(corpo, bg=COR_CARD)
        topo.pack(fill="x", padx=6)
        tk.Label(topo, text="Acompanhamento", bg=COR_CARD, font=(FONTE, 11, "bold"),
                 fg=COR_TEXTO).pack(side="left")
        tk.Label(topo, text="Limpar", bg=COR_CARD, fg=COR_TEXTO_SUAVE,
                 font=(FONTE, 9, "underline"), cursor="hand2").pack(side="right")
        topo.winfo_children()[-1].bind("<Button-1>", lambda _e: self._limpar_log())

        moldura = tk.Frame(corpo, bg=COR_CARD)
        moldura.pack(fill="both", expand=True, padx=6, pady=(10, 4))
        self._feed = tk.Text(
            moldura, font=(FONTE, 10), state="disabled", bg=COR_CARD, fg=COR_TEXTO,
            relief="flat", borderwidth=0, wrap="word", cursor="arrow",
            spacing1=4, spacing3=4, padx=4, pady=2, highlightthickness=0,
        )
        scroll = tk.Scrollbar(moldura, command=self._feed.yview, width=12,
                              relief="flat", bd=0, troughcolor=COR_CARD)
        self._feed.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self._feed.pack(side="left", fill="both", expand=True)

        for chave, cor in (("ok", FEED_OK), ("erro", FEED_ERRO),
                           ("aviso", FEED_AVISO), ("info", COR_TEXTO)):
            self._feed.tag_config(chave, foreground=cor, lmargin1=2, lmargin2=26)
            self._feed.tag_config(chave + "_i", foreground=cor)
        self._feed.tag_config("sub", foreground=FEED_INFO, lmargin1=26, lmargin2=40)

    # ------------------------------------------------------------------
    # Painel de clientes
    # ------------------------------------------------------------------

    def _limpar_container_clientes(self) -> None:
        for w in self._clientes_container.winfo_children():
            w.destroy()

    def _render_placeholder_clientes(self, texto: str | None = None) -> None:
        self._limpar_container_clientes()
        self._combos = []
        self._mapa_rotulo_proj = []
        self._lbl_contador.pack_forget()
        tk.Label(
            self._clientes_container,
            text=texto or "Informe a coordenadora e a data, depois clique em “Buscar clientes”.",
            bg=COR_CARD, fg=COR_TEXTO_SUAVE, font=(FONTE, 10, "italic"),
            anchor="w", justify="left", wraplength=700,
        ).pack(fill="x", pady=6)

    def _render_clientes(self, clientes: list, projetos_por_cliente: list) -> None:
        self._limpar_container_clientes()
        self._combos = []
        self._mapa_rotulo_proj = []
        self._lbl_contador.config(text=f"{len(clientes)}")
        self._lbl_contador.pack(side="left", padx=(10, 0))

        for cliente, projetos in zip(clientes, projetos_por_cliente):
            self._render_linha_cliente(cliente, projetos)

    def _render_linha_cliente(self, cliente, projetos: list) -> None:
        card = CartaoArredondado(self._clientes_container, cor=COR_CAMPO,
                                 raio=12, padding=10)
        card.pack(fill="x", pady=3)
        row = card.inner

        tk.Label(row, text="●", bg=COR_CAMPO, fg=COR_ACENTO,
                 font=(FONTE, 10)).pack(side="left", padx=(2, 8))

        texto = tk.Frame(row, bg=COR_CAMPO)
        texto.pack(side="left", fill="x", expand=True)
        tk.Label(texto, text=cliente.nome_curto, bg=COR_CAMPO, fg=COR_TEXTO,
                 font=(FONTE, 10, "bold"), anchor="w").pack(fill="x")
        tk.Label(texto, text=cliente.cliente_id_completo, bg=COR_CAMPO,
                 fg=COR_TEXTO_SUAVE, font=(FONTE, 9), anchor="w").pack(fill="x")

        seletor = tk.Frame(row, bg=COR_CAMPO)
        seletor.pack(side="right", padx=(8, 2))
        tk.Label(seletor, text="PROJETO", bg=COR_CAMPO, fg=COR_TEXTO_SUAVE,
                 font=(FONTE, 8, "bold")).pack(anchor="w")

        if projetos:
            mapa = {p.rotulo(): p for p in projetos}
            combo = ttk.Combobox(seletor, values=list(mapa.keys()),
                                 state="readonly", width=44, font=(FONTE, 9),
                                 style="GHR.TCombobox")
            combo.pack(ipady=1)
            self._preselecionar_projeto(combo, cliente, projetos)
            self._combos.append(combo)
            self._mapa_rotulo_proj.append(mapa)
        else:
            aviso = ("sem nr_seq_cliente cadastrado"
                     if not cliente.nr_seq_cliente else "nenhum projeto ativo no ERP")
            tk.Label(seletor, text=aviso, bg=COR_CAMPO, fg=COR_TEXTO_SUAVE,
                     font=(FONTE, 9, "italic")).pack(anchor="w")
            self._combos.append(None)
            self._mapa_rotulo_proj.append({})

    def _preselecionar_projeto(self, combo, cliente, projetos: list) -> None:
        codigo = self._codigo_negocio(cliente.cliente_id_completo)
        if codigo:
            for p in projetos:
                if self._codigo_negocio(p.titulo) == codigo:
                    combo.set(p.rotulo())
                    return

    @staticmethod
    def _codigo_negocio(texto: str) -> str:
        achado = _RE_CODIGO_NEGOCIO.search(texto or "")
        return achado.group(1) if achado else ""

    # ------------------------------------------------------------------
    # Acoes
    # ------------------------------------------------------------------

    def _registrar_invalidacao(self) -> None:
        self._var_coordenadora.trace_add("write", self._invalidar_selecao)
        self._var_data.trace_add("write", self._invalidar_selecao)

    def _invalidar_selecao(self, *_args) -> None:
        if self._ocupado:
            return
        if self._clientes:
            self._clientes = []
            self._render_placeholder_clientes(
                "Dados alterados — clique em “Buscar clientes” novamente."
            )
        self._btn_gerar.definir_habilitado(False)

    def _validar_entradas(self) -> date | None:
        if not self._var_coordenadora.get().strip():
            self._log("Informe o nome da coordenadora.", "aviso")
            return None
        try:
            return datetime.strptime(self._var_data.get().strip(), "%d/%m/%Y").date()
        except ValueError:
            self._log(f"Data inválida '{self._var_data.get().strip()}'. Use DD/MM/AAAA.", "aviso")
            return None

    def _ao_buscar(self) -> None:
        self._limpar_log()
        data = self._validar_entradas()
        if data is None:
            return
        coordenadora = self._var_coordenadora.get().strip()

        self._ocupado = True
        self._clientes = []
        self._placeholder_vazio = "Nenhum cliente encontrado para esta coordenadora/data."
        self._render_placeholder_clientes("Verificando o banco e procurando os clientes...")
        self._btn_gerar.definir_habilitado(False)
        self._btn_buscar.definir_habilitado(False)
        self._btn_buscar.definir_texto("Procurando...")

        threading.Thread(target=self._buscar_em_thread,
                         args=(coordenadora, data), daemon=True).start()

    def _buscar_em_thread(self, coordenadora: str, data: date) -> None:
        clientes: list = []
        projetos_por_cliente: list = []
        try:
            from status_report.aplicacao.pipeline_coordenadora import (
                buscar_clientes_para_status_report,
            )
            from status_report.configuracao import carregar_configuracoes
            from status_report.infraestrutura.autenticacao_google import (
                construir_servicos_google,
            )

            self._config = carregar_configuracoes()

            # 1) O banco e a primeira coisa a verificar.
            if not self._verificar_banco():
                return

            mapa_clientes = self._carregar_mapa_clientes()

            self._log(f"Procurando os status reports de {coordenadora} em "
                      f"{data.strftime('%d/%m/%Y')}...")
            self._servicos = construir_servicos_google(self._config)
            clientes = buscar_clientes_para_status_report(
                config=self._config, servicos=self._servicos,
                nome_coordenadora=coordenadora, data_referencia=data, log_fn=self._log,
            )
            clientes = self._resolver_nr_seq_cliente(clientes, mapa_clientes)
            projetos_por_cliente = self._buscar_projetos(clientes)
        except Exception as e:
            self._log(f"Algo deu errado: {e}", "erro")
        finally:
            self.after(0, lambda: self._apos_busca(clientes, projetos_por_cliente))

    def _verificar_banco(self) -> bool:
        """Testa a conexao com o Oracle antes de qualquer outra coisa."""
        self._log("Verificando conexão com o banco de dados...", "info")
        if self._config is None or not self._config.oracle_configurado():
            self._log("Banco de dados não configurado (verifique ORACLE_* no .env).", "erro")
            self._placeholder_vazio = "Banco de dados não configurado (ORACLE_* no .env)."
            return False
        from status_report.infraestrutura.repositorio_oracle import testar_conexao
        try:
            testar_conexao(self._config)
        except Exception:
            self._log("Não foi possível conectar ao banco de dados.", "erro")
            self._log("Verifique se a conexão com a VPN está ativa e tente novamente.", "aviso")
            self._placeholder_vazio = "Sem conexão com o banco de dados. Verifique a VPN."
            return False
        self._log("Banco de dados conectado.", "ok")
        return True

    def _carregar_mapa_clientes(self) -> dict:
        from status_report.infraestrutura.repositorio_oracle import (
            carregar_mapa_codigo_para_nr_seq,
        )
        try:
            return carregar_mapa_codigo_para_nr_seq(self._config)
        except Exception as e:
            self._log(f"Falha ao carregar clientes do ERP: {e}", "aviso")
            return {}

    def _resolver_nr_seq_cliente(self, clientes: list, mapa: dict) -> list:
        """Descobre o nr_seq_cliente no ERP pelo codigo do cliente (ou usa a coluna G)."""
        resolvidos: list = []
        for cliente in clientes:
            nr_seq = cliente.nr_seq_cliente
            if not nr_seq:
                codigo = self._codigo_inicial(cliente.codigo_cliente) or \
                    self._codigo_inicial(cliente.cliente_id_completo)
                if codigo is not None and codigo in mapa:
                    nr_seq = str(mapa[codigo])
            if nr_seq and nr_seq != cliente.nr_seq_cliente:
                cliente = replace(cliente, nr_seq_cliente=nr_seq)
            resolvidos.append(cliente)
        return resolvidos

    @staticmethod
    def _codigo_inicial(texto: str) -> int | None:
        achado = re.match(r"\s*(\d+)", texto or "")
        return int(achado.group(1)) if achado else None

    def _buscar_projetos(self, clientes: list) -> list:
        """Para cada cliente, lista os projetos ativos no Oracle."""
        if not clientes:
            return []
        if self._config is None or not self._config.oracle_configurado():
            self._log("Oracle não configurado — seleção de projeto indisponível.", "aviso")
            return [[] for _ in clientes]

        from status_report.infraestrutura.repositorio_oracle import (
            listar_projetos_ativos_do_cliente,
        )

        self._log("Buscando projetos no ERP...", "info")
        projetos_por_cliente: list = []
        for cliente in clientes:
            if not cliente.nr_seq_cliente:
                self._log(f"  {cliente.nome_curto}: sem nr_seq_cliente na aba Clientes (coluna G).",
                          "aviso")
                projetos_por_cliente.append([])
                continue
            try:
                projetos = listar_projetos_ativos_do_cliente(
                    self._config, cliente.nr_seq_cliente
                )
                self._log(f"  {cliente.nome_curto}: {len(projetos)} projeto(s) ativo(s).")
                projetos_por_cliente.append(projetos)
            except Exception as e:
                self._log(f"  {cliente.nome_curto}: falha ao buscar projetos ({e}).", "aviso")
                projetos_por_cliente.append([])
        return projetos_por_cliente

    def _apos_busca(self, clientes: list, projetos_por_cliente: list) -> None:
        self._ocupado = False
        self._clientes = clientes
        self._projetos_por_cliente = projetos_por_cliente
        self._btn_buscar.definir_habilitado(True)
        self._btn_buscar.definir_texto("Buscar clientes")
        if clientes:
            self._render_clientes(clientes, projetos_por_cliente)
            self._btn_gerar.definir_habilitado(True)
            self._log("Escolha o projeto de cada cliente e clique em “Gerar Status Reports”.",
                      "info")
        else:
            self._render_placeholder_clientes(
                getattr(self, "_placeholder_vazio",
                        "Nenhum cliente encontrado para esta coordenadora/data.")
            )
            self._btn_gerar.definir_habilitado(False)

    def _ao_gerar(self) -> None:
        if not self._clientes or self._config is None or self._servicos is None:
            self._log("Busque os clientes antes de gerar.", "aviso")
            return
        data = self._validar_entradas()
        if data is None:
            return

        clientes = self._clientes_com_projeto_escolhido()

        self._ocupado = True
        self._btn_gerar.definir_habilitado(False)
        self._btn_gerar.definir_texto("Gerando...")
        self._btn_buscar.definir_habilitado(False)

        threading.Thread(target=self._gerar_em_thread,
                         args=(clientes, data), daemon=True).start()

    def _clientes_com_projeto_escolhido(self) -> list:
        """Aplica em cada ClienteFila o projeto selecionado no combo (se houver)."""
        clientes: list = []
        for i, cliente in enumerate(self._clientes):
            combo = self._combos[i] if i < len(self._combos) else None
            projeto = None
            if combo is not None:
                projeto = self._mapa_rotulo_proj[i].get(combo.get())
            if projeto is not None:
                cliente = replace(
                    cliente,
                    nr_seq_proj=str(projeto.nr_seq_proj),
                    nome_projeto=projeto.titulo,
                    cliente_id_completo=projeto.titulo,
                )
            clientes.append(cliente)
        return clientes

    def _gerar_em_thread(self, clientes: list, data: date) -> None:
        resultados: list = []
        try:
            from status_report.aplicacao.pipeline_coordenadora import processar_clientes

            self._log(f"Gerando {len(clientes)} status report(s)...", "info")
            for cliente in clientes:
                if cliente.nome_projeto:
                    self._log(f"  {cliente.nome_curto} → {cliente.nome_projeto}")
            resultados = processar_clientes(
                config=self._config, servicos=self._servicos,
                clientes=clientes, data_referencia=data, log_fn=self._log,
            )
        except Exception as e:
            self._log(f"Algo deu errado: {e}", "erro")
        finally:
            self.after(0, lambda: self._apos_geracao(resultados))

    def _apos_geracao(self, resultados: list) -> None:
        self._ocupado = False
        if resultados:
            sucessos = sum(1 for r in resultados if r.sucesso)
            tag = "ok" if sucessos == len(resultados) else "aviso"
            self._log(f"Pronto! {sucessos} de {len(resultados)} gerado(s) com sucesso.", tag)
            for resultado in resultados:
                for caminho in resultado.caminhos_locais:
                    rotulo = "PDF" if caminho.lower().endswith(".pdf") else "PowerPoint"
                    self._log(f"{rotulo} salvo em: {caminho}", "ok")
        self._btn_gerar.definir_texto("Gerar Status Reports")
        self._btn_buscar.definir_habilitado(True)
        self._btn_gerar.definir_habilitado(bool(self._clientes))

    # ------------------------------------------------------------------
    # Logo
    # ------------------------------------------------------------------

    def _carregar_logo(self, altura_alvo: int = 60) -> tk.PhotoImage | None:
        caminho = caminho_logo()
        if caminho is None:
            return None
        try:
            img = tk.PhotoImage(file=str(caminho))
        except Exception:
            return None
        fator = max(1, round(img.height() / altura_alvo))
        return img.subsample(fator, fator) if fator > 1 else img

    # ------------------------------------------------------------------
    # Acompanhamento (thread-safe via fila)
    # ------------------------------------------------------------------

    def _log(self, msg: str, tag: str = "info") -> None:
        self._fila_log.put((msg, tag))

    def _limpar_log(self) -> None:
        self._feed.configure(state="normal")
        self._feed.delete("1.0", "end")
        self._feed.configure(state="disabled")

    def _inserir_feed(self, msg: str, tag: str) -> None:
        self._feed.configure(state="normal")
        for linha in msg.split("\n"):
            texto = linha.strip()
            if not texto:
                self._feed.insert("end", "\n")
                continue
            if texto.startswith("•"):
                self._feed.insert("end", "   " + texto.lstrip("• ").strip() + "\n", ("sub",))
            else:
                icone = _ICONES.get(tag, "•")
                self._feed.insert("end", icone + "  ", (tag + "_i",))
                self._feed.insert("end", texto + "\n", (tag,))
        self._feed.see("end")
        self._feed.configure(state="disabled")

    def _verificar_fila_log(self) -> None:
        try:
            while True:
                msg, tag = self._fila_log.get_nowait()
                self._inserir_feed(msg, tag)
        except queue.Empty:
            pass
        self.after(100, self._verificar_fila_log)


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
