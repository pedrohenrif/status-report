"""Interface grafica (tkinter) do Gerador de Status Report - GHR."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from datetime import date, datetime
from tkinter import font, scrolledtext, ttk


_COR_AZUL = "#1a3c6e"
_COR_AZUL_HOVER = "#15305a"
_COR_BRANCO = "#ffffff"
_COR_FUNDO = "#f4f6f9"
_COR_BORDA = "#d1d9e0"
_COR_VERDE = "#1a7a4a"
_COR_VERMELHO = "#c0392b"
_COR_LARANJA = "#d35400"
_COR_CINZA = "#555555"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Gerador de Status Report — GHR")
        self.geometry("680x560")
        self.resizable(False, False)
        self.configure(bg=_COR_FUNDO)
        self._fila_log: queue.Queue[tuple[str, str]] = queue.Queue()
        self._construir_ui()
        self._verificar_fila_log()

    # ------------------------------------------------------------------
    # Construcao da UI
    # ------------------------------------------------------------------

    def _construir_ui(self) -> None:
        self._construir_cabecalho()
        self._construir_formulario()
        self._construir_botao()
        self._construir_area_log()

    def _construir_cabecalho(self) -> None:
        frame = tk.Frame(self, bg=_COR_AZUL)
        frame.pack(fill="x")
        tk.Label(
            frame,
            text="Gerador de Status Report",
            bg=_COR_AZUL,
            fg=_COR_BRANCO,
            font=("Helvetica", 17, "bold"),
            pady=18,
        ).pack()
        tk.Label(
            frame,
            text="GHR Tech — Automacao de Relatorios",
            bg=_COR_AZUL,
            fg="#a8c0e0",
            font=("Helvetica", 9),
            pady=0,
        ).pack()
        tk.Frame(frame, bg=_COR_AZUL, height=12).pack()

    def _construir_formulario(self) -> None:
        frame = tk.Frame(self, bg=_COR_FUNDO, padx=30, pady=20)
        frame.pack(fill="x")

        # Coordenadora
        tk.Label(
            frame, text="Coordenadora", bg=_COR_FUNDO,
            font=("Helvetica", 10, "bold"), fg=_COR_CINZA, anchor="w",
        ).grid(row=0, column=0, sticky="w")
        self._var_coordenadora = tk.StringVar()
        entry_coord = tk.Entry(
            frame, textvariable=self._var_coordenadora,
            width=38, font=("Helvetica", 11),
            relief="flat", bd=0, bg=_COR_BRANCO,
            highlightthickness=1, highlightbackground=_COR_BORDA,
            highlightcolor=_COR_AZUL,
        )
        entry_coord.grid(row=1, column=0, pady=(4, 14), ipady=7, sticky="w")
        entry_coord.focus()

        # Data
        tk.Label(
            frame, text="Data (DD/MM/AAAA)", bg=_COR_FUNDO,
            font=("Helvetica", 10, "bold"), fg=_COR_CINZA, anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(20, 0))
        self._var_data = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))
        entry_data = tk.Entry(
            frame, textvariable=self._var_data,
            width=16, font=("Helvetica", 11),
            relief="flat", bd=0, bg=_COR_BRANCO,
            highlightthickness=1, highlightbackground=_COR_BORDA,
            highlightcolor=_COR_AZUL,
        )
        entry_data.grid(row=1, column=1, pady=(4, 14), ipady=7, padx=(20, 0), sticky="w")

        # Botao "Hoje"
        tk.Button(
            frame, text="Hoje",
            command=lambda: self._var_data.set(date.today().strftime("%d/%m/%Y")),
            bg=_COR_BORDA, fg=_COR_CINZA, relief="flat",
            font=("Helvetica", 9), cursor="hand2", padx=8,
        ).grid(row=1, column=2, padx=(6, 0), pady=(4, 14), sticky="w")

    def _construir_botao(self) -> None:
        frame = tk.Frame(self, bg=_COR_FUNDO)
        frame.pack(fill="x", padx=30)
        self._btn = tk.Button(
            frame,
            text="Gerar Status Reports",
            command=self._ao_clicar_gerar,
            bg=_COR_AZUL, fg=_COR_BRANCO,
            font=("Helvetica", 12, "bold"),
            relief="flat", cursor="hand2",
            padx=28, pady=10,
        )
        self._btn.pack(anchor="w")
        self._btn.bind("<Enter>", lambda _: self._btn.config(bg=_COR_AZUL_HOVER))
        self._btn.bind("<Leave>", lambda _: self._btn.config(bg=_COR_AZUL))

    def _construir_area_log(self) -> None:
        frame = tk.Frame(self, bg=_COR_FUNDO, padx=30, pady=10)
        frame.pack(fill="both", expand=True)
        tk.Label(
            frame, text="Log de execucao", bg=_COR_FUNDO,
            font=("Helvetica", 10, "bold"), fg=_COR_CINZA, anchor="w",
        ).pack(fill="x", pady=(0, 4))
        self._log_area = scrolledtext.ScrolledText(
            frame, height=14, font=("Courier", 9),
            state="disabled", bg="#1e2533", fg="#d0d7e3",
            relief="flat", borderwidth=0, padx=10, pady=8,
        )
        self._log_area.pack(fill="both", expand=True)
        self._log_area.tag_config("ok", foreground="#4ec97e")
        self._log_area.tag_config("erro", foreground="#ff6b6b")
        self._log_area.tag_config("aviso", foreground="#ffd166")
        self._log_area.tag_config("info", foreground="#d0d7e3")
        self._log_area.tag_config("separador", foreground="#444c60")

    # ------------------------------------------------------------------
    # Acoes
    # ------------------------------------------------------------------

    def _ao_clicar_gerar(self) -> None:
        coordenadora = self._var_coordenadora.get().strip()
        data_str = self._var_data.get().strip()

        self._limpar_log()

        if not coordenadora:
            self._log("Informe o nome da coordenadora.", "aviso")
            return

        try:
            data = datetime.strptime(data_str, "%d/%m/%Y").date()
        except ValueError:
            self._log(f"Data invalida '{data_str}'. Use o formato DD/MM/AAAA.", "aviso")
            return

        self._btn.config(state="disabled", text="Gerando...")
        thread = threading.Thread(
            target=self._executar_em_thread, args=(coordenadora, data), daemon=True
        )
        thread.start()

    def _executar_em_thread(self, coordenadora: str, data: date) -> None:
        try:
            from status_report.aplicacao.pipeline_coordenadora import (
                executar_pipeline_coordenadora,
            )
            from status_report.configuracao import carregar_configuracoes
            from status_report.infraestrutura.autenticacao_google import (
                construir_servicos_google,
            )

            self._log(f"Iniciando — {coordenadora} | {data.strftime('%d/%m/%Y')}")
            self._log("─" * 52, "separador")

            config = carregar_configuracoes()
            servicos = construir_servicos_google(config)

            resultados = executar_pipeline_coordenadora(
                config=config,
                servicos=servicos,
                nome_coordenadora=coordenadora,
                data_referencia=data,
                log_fn=self._log,
            )

            self._log("─" * 52, "separador")
            if resultados:
                sucessos = sum(1 for r in resultados if r.sucesso)
                tag = "ok" if sucessos == len(resultados) else "aviso"
                self._log(f"Concluido: {sucessos}/{len(resultados)} com sucesso.", tag)
            elif resultados == []:
                pass  # mensagens ja exibidas no pipeline

        except Exception as e:
            self._log(f"Erro inesperado: {e}", "erro")
        finally:
            self.after(0, lambda: self._btn.config(state="normal", text="Gerar Status Reports"))

    # ------------------------------------------------------------------
    # Log (thread-safe via fila)
    # ------------------------------------------------------------------

    def _log(self, msg: str, tag: str = "info") -> None:
        self._fila_log.put((msg, tag))

    def _limpar_log(self) -> None:
        self._log_area.configure(state="normal")
        self._log_area.delete("1.0", "end")
        self._log_area.configure(state="disabled")

    def _verificar_fila_log(self) -> None:
        try:
            while True:
                msg, tag = self._fila_log.get_nowait()
                self._log_area.configure(state="normal")
                self._log_area.insert("end", msg + "\n", tag)
                self._log_area.see("end")
                self._log_area.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._verificar_fila_log)


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
