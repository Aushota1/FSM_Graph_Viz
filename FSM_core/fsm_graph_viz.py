# -*- coding: utf-8 -*-
"""
fsm_gui_app.py

GUI-приложение для визуализации FSM-графов, построенных из SystemVerilog-кода.

Использует:
  - cst_service.CSTService
  - fsm_graph_builder.build_fsm_graphs_from_cst

Фичи:
  - Открытие .sv-файлов (File -> Open...)
  - Вкладка с редактором SystemVerilog-кода и кнопкой "Parse from editor"
  - Список найденных FSM слева
  - Отрисовка FSM-графа на Canvas (состояния по окружности, стрелки, условия переходов)
  - Детальная панель (scope, enum_name, state_var, next_state_var, reset_state, статистика)
  - Таблица переходов
  - Зум Canvas (Scale)
  - Export as HTML — сохранение красивого HTML+SVG для текущего FSM

Требования:
  - Python стандартной комплектации (tkinter есть в стандартной библиотеке)
  - Файлы:
      cst_service.py
      fsm_graph_builder.py
    должны лежать рядом.

Запуск:
    python fsm_gui_app.py
"""

import math
import os
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from AST_CST.cst_service import CSTService
from .fsm_graph_builder import build_fsm_graphs_from_cst


# ============================================================
# Утилиты
# ============================================================

def _escape_html(s: str) -> str:
    """Простое экранирование для HTML."""
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )


def _normalize_cond(cond: Optional[str]) -> str:
    """Подчистить строку условия."""
    if cond is None:
        return ""
    return " ".join(cond.strip().split())


# ============================================================
# HTML + SVG экспорт (без внешних библиотек)
# ============================================================

def fsm_graph_to_svg(graph: Dict[str, Any],
                     width: int = 800,
                     height: int = 600) -> str:
    """
    Преобразовать FSM-граф в SVG-строку.
    Состояния по окружности, стрелки с надписями.
    """
    states: List[str] = list(graph.get("states", []))
    transitions: List[Dict[str, Any]] = list(graph.get("transitions", []))
    reset_state = graph.get("reset_state")

    if not states:
        return f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg"></svg>'

    cx = width / 2
    cy = height / 2 + 40
    radius = min(width, height) * 0.30

    node_positions: Dict[str, tuple] = {}
    n = len(states)
    for i, s in enumerate(states):
        angle = 2 * math.pi * i / n - math.pi / 2
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        node_positions[s] = (x, y)

    node_r = 28

    svg_lines: List[str] = []
    svg_lines.append(f'<svg width="{width}" height="{height}" '
                     f'viewBox="0 0 {width} {height}" '
                     f'xmlns="http://www.w3.org/2000/svg">')

    svg_lines.append("<defs>")
    svg_lines.append(
        '<marker id="arrow" markerWidth="10" markerHeight="7" '
        'refX="10" refY="3.5" orient="auto">'
        '<polygon points="0 0, 10 3.5, 0 7" fill="#333" />'
        "</marker>"
    )
    svg_lines.append("</defs>")

    svg_lines.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" '
        f'fill="#ffffff" stroke="none" />'
    )

    # Рёбра
    for t in transitions:
        frm = t.get("from")
        to = t.get("to")
        cond = _normalize_cond(t.get("cond"))
        if frm not in node_positions or to not in node_positions:
            continue

        x1, y1 = node_positions[frm]
        x2, y2 = node_positions[to]

        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy) or 1.0
        ux, uy = dx / dist, dy / dist

        start_x = x1 + ux * node_r
        start_y = y1 + uy * node_r
        end_x = x2 - ux * node_r
        end_y = y2 - uy * node_r

        svg_lines.append(
            f'<line x1="{start_x:.1f}" y1="{start_y:.1f}" '
            f'x2="{end_x:.1f}" y2="{end_y:.1f}" '
            f'stroke="#333" stroke-width="2" marker-end="url(#arrow)" />'
        )

        if cond and cond != "1":
            mx = (start_x + end_x) / 2
            my = (start_y + end_y) / 2

            off = 14
            nx = -uy
            ny = ux
            label_x = mx + nx * off
            label_y = my + ny * off

            label = _escape_html(cond)
            svg_lines.append(
                f'<text x="{label_x:.1f}" y="{label_y:.1f}" '
                f'font-size="12" text-anchor="middle" '
                f'fill="#000000" '
                f'font-family="Helvetica, Arial, sans-serif">'
                f'{label}</text>'
            )

    # Узлы
    for s in states:
        x, y = node_positions[s]
        label = _escape_html(s)

        if reset_state and s == reset_state:
            svg_lines.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{node_r+4:.1f}" '
                f'fill="#e8ffe8" stroke="#006600" stroke-width="2.5" />'
            )
            svg_lines.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{node_r-2:.1f}" '
                f'fill="none" stroke="#006600" stroke-width="1.8" />'
            )
        else:
            svg_lines.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{node_r:.1f}" '
                f'fill="#eef2ff" stroke="#333366" stroke-width="2" />'
            )

        svg_lines.append(
            f'<text x="{x:.1f}" y="{y+4:.1f}" '
            f'font-size="12" text-anchor="middle" '
            f'fill="#000000" '
            f'font-family="Helvetica, Arial, sans-serif">'
            f'{label}</text>'
        )

    svg_lines.append("</svg>")
    return "\n".join(svg_lines)


def fsm_graph_to_html(graph: Dict[str, Any],
                      title: Optional[str] = None,
                      width: int = 800,
                      height: int = 600) -> str:
    """Обернуть SVG FSM-графа в HTML-документ."""
    scope = graph.get("scope", "fsm")
    enum_name = graph.get("enum_name", "")
    state_var = graph.get("state_var", "state")
    next_state_var = graph.get("next_state_var")
    reset_state = graph.get("reset_state")
    meta = graph.get("metadata", {}) or {}
    num_states = meta.get("num_states", len(graph.get("states", [])))
    num_trans = meta.get("num_transitions", len(graph.get("transitions", [])))

    if title is None:
        title = f"FSM Graph - {scope}"

    svg = fsm_graph_to_svg(graph, width=width, height=height)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{_escape_html(title)}</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f5f7fb;
    }}
    .container {{
      max-width: {width + 40}px;
      margin: 20px auto;
      background: #ffffff;
      box-shadow: 0 4px 12px rgba(0,0,0,0.08);
      border-radius: 12px;
      padding: 20px 20px 30px 20px;
    }}
    .header {{
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-bottom: 10px;
    }}
    .title {{
      font-size: 20px;
      font-weight: 600;
      color: #222;
    }}
    .subtitle {{
      font-size: 13px;
      color: #666;
    }}
    .badges {{
      margin-top: 6px;
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .badge {{
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 999px;
      background: #eef2ff;
      color: #333366;
    }}
    .badge-reset {{
      background: #e8ffe8;
      color: #006600;
    }}
    .svg-wrapper {{
      margin-top: 10px;
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid #dde3f0;
      background: #ffffff;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="title">{_escape_html(scope)}</div>
      <div class="subtitle">
        FSM по enum-типу {_escape_html(enum_name) if enum_name else "(анонимный enum)"}.
      </div>
      <div class="badges">
        <span class="badge">state: {_escape_html(state_var)}</span>"""
    if next_state_var:
        html += f'\n        <span class="badge">next: {_escape_html(next_state_var)}</span>'
    if reset_state:
        html += f'\n        <span class="badge badge-reset">reset: {_escape_html(reset_state)}</span>'
    html += f"""
        <span class="badge">states: {num_states}</span>
        <span class="badge">transitions: {num_trans}</span>
      </div>
    </div>
    <div class="svg-wrapper">
      {svg}
    </div>
  </div>
</body>
</html>
"""
    return html


# ============================================================
# GUI Application
# ============================================================

class FSMGuiApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FSM Visualizer")
        self.geometry("1200x800")

        self._create_menu()

        # Основный контейнер
        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True)

        # Левый сплиттер: список FSM + вкладки
        left_pane = ttk.Panedwindow(main, orient=tk.HORIZONTAL)
        left_pane.pack(fill=tk.BOTH, expand=True)

        # Слева: список FSM
        left_frame = ttk.Frame(left_pane)
        left_frame.pack(fill=tk.BOTH, expand=False)
        left_pane.add(left_frame, weight=1)

        # Справа: вкладки (Canvas + Editor + Details)
        right_notebook = ttk.Notebook(left_pane)
        left_pane.add(right_notebook, weight=4)

        # --- ЛЕВАЯ ПАНЕЛЬ: список FSM ---
        self.fsm_listbox = tk.Listbox(left_frame, height=20)
        self.fsm_listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.fsm_listbox.bind("<<ListboxSelect>>", self.on_fsm_select)

        lbl = ttk.Label(left_frame, text="FSM list")
        lbl.pack(side=tk.TOP, anchor="w", padx=4)

        # --- ПЕРВАЯ ВКЛАДКА: ГРАФ ---
        graph_tab = ttk.Frame(right_notebook)
        right_notebook.add(graph_tab, text="Graph")

        # Верхняя панель в graph_tab: зум + кнопки
        top_controls = ttk.Frame(graph_tab)
        top_controls.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top_controls, text="Zoom:").pack(side=tk.LEFT, padx=(4, 2))
        self.zoom_var = tk.DoubleVar(value=1.0)
        zoom_scale = ttk.Scale(
            top_controls,
            from_=0.5,
            to=2.0,
            orient=tk.HORIZONTAL,
            variable=self.zoom_var,
            command=lambda v: self.redraw_current_graph()
        )
        zoom_scale.pack(side=tk.LEFT, padx=4, pady=4)

        ttk.Button(
            top_controls,
            text="Export as HTML",
            command=self.export_current_graph_as_html
        ).pack(side=tk.RIGHT, padx=4)

        # Canvas
        self.canvas = tk.Canvas(graph_tab, bg="#f9fafc")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.canvas.bind("<Configure>", lambda e: self.redraw_current_graph())

        # --- ВТОРАЯ ВКЛАДКА: EDITOR ---
        editor_tab = ttk.Frame(right_notebook)
        right_notebook.add(editor_tab, text="Code editor")

        editor_controls = ttk.Frame(editor_tab)
        editor_controls.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(
            editor_controls,
            text="Parse from editor",
            command=self.parse_from_editor
        ).pack(side=tk.LEFT, padx=4, pady=4)

        self.editor = tk.Text(editor_tab, wrap="none")
        self.editor.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._fill_example_code()

        # --- ТРЕТЬЯ ВКЛАДКА: DETAILS ---
        details_tab = ttk.Frame(right_notebook)
        right_notebook.add(details_tab, text="Details")

        self.details_text = tk.Text(details_tab, wrap="word", height=15)
        self.details_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Таблица переходов
        self.transitions_tree = ttk.Treeview(
            details_tab,
            columns=("from", "to", "cond"),
            show="headings",
            height=10
        )
        self.transitions_tree.heading("from", text="From")
        self.transitions_tree.heading("to", text="To")
        self.transitions_tree.heading("cond", text="Condition")

        self.transitions_tree.column("from", width=80, anchor="center")
        self.transitions_tree.column("to", width=80, anchor="center")
        self.transitions_tree.column("cond", width=150, anchor="w")

        self.transitions_tree.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Данные
        self.graphs: List[Dict[str, Any]] = []
        self.current_graph_index: Optional[int] = None
        self.current_filename: Optional[str] = None

        # Немного стиля
        self._configure_style()

    # --------------------------------------------------------
    # UI helpers
    # --------------------------------------------------------

    def _configure_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

    def _create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="File", menu=file_menu)

        file_menu.add_command(label="Open .sv...", command=self.menu_open_sv)
        file_menu.add_command(label="Parse from editor", command=self.parse_from_editor)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)

    def _fill_example_code(self):
        example = r"""//----------------------------------------------------------------------------

//============================================================
// Сложный пример SystemVerilog с несколькими FSM
// - complex_fsm_top: верхний модуль
// - ingress_fsm    : приём пакетов, парсинг заголовка, классификация
// - egress_fsm     : выборка из буфера, учёт кредитов, ретраи
// - credit_ctrl_fsm: управление кредитами/паузой
// - error_mgr_fsm  : агрегатор ошибок, локальный/глобальный сброс
// - watchdog_fsm   : сторожевой таймер по "сердцебиениям" FSM
//
// Каждый автомат имеет много состояний и нетривиальные условия
// переходов, но код остаётся синтезируемым и структурированным.
//============================================================

`timescale 1ns/1ps

//============================================================
// Пакет с типами состояний
//============================================================
package complex_fsm_types_pkg;

  // Состояния входного автомата (ingress)
  typedef enum logic [3:0] {
    IN_IDLE,
    IN_WAIT_SOP,
    IN_PARSE_HDR,
    IN_CLASSIFY,
    IN_CHECK_LEN,
    IN_PUSH_PAYLOAD,
    IN_DROP_PKT,
    IN_FLUSH_REST,
    IN_ERR_HOLD,
    IN_ERR_RECOVER
  } ingress_state_t;

  // Состояния выходного автомата (egress)
  typedef enum logic [3:0] {
    EG_IDLE,
    EG_ARB_REQ,
    EG_WAIT_CREDIT,
    EG_DEQUEUE,
    EG_SEND_HDR,
    EG_SEND_PAYLOAD,
    EG_WAIT_ACK,
    EG_RETRY,
    EG_DRAIN,
    EG_PAUSE,
    EG_ERROR
  } egress_state_t;

  // Состояния контроллера кредитов
  typedef enum logic [2:0] {
    CR_IDLE,
    CR_GRANT,
    CR_WAIT_CONSUME,
    CR_UNDERFLOW,
    CR_OVERFLOW,
    CR_FREEZE,
    CR_RECOVER
  } credit_state_t;

  // Состояния менеджера ошибок
  typedef enum logic [2:0] {
    ER_IDLE,
    ER_MONITOR,
    ER_LOCAL_FAULT,
    ER_GLOBAL_FAULT,
    ER_ISOLATE,
    ER_CLEAR,
    ER_RECOVER
  } error_state_t;

  // Состояния сторожевого таймера
  typedef enum logic [2:0] {
    WD_IDLE,
    WD_ARMED,
    WD_COUNT,
    WD_EXPIRED,
    WD_HOLD
  } watchdog_state_t;

endpackage : complex_fsm_types_pkg

import complex_fsm_types_pkg::*;

//============================================================
// Верхний модуль, связывающий все FSM
//============================================================
module complex_fsm_top #(
  parameter int DATA_WIDTH      = 32,
  parameter int MAX_PKT_WORDS   = 256,
  parameter int MAX_CREDITS     = 8,
  parameter int WD_MAX_CYCLES   = 1024
) (
  input  logic                  clk,
  input  logic                  rst_n,

  // Входной поток (абстрактный протокол)
  input  logic                  in_valid_i,
  input  logic [DATA_WIDTH-1:0] in_data_i,
  input  logic                  in_sop_i,
  input  logic                  in_eop_i,

  // Выходной поток
  output logic                  out_valid_o,
  output logic [DATA_WIDTH-1:0] out_data_o,
  output logic                  out_sop_o,
  output logic                  out_eop_o,
  input  logic                  out_ready_i,

  // Общие статусы
  output logic                  global_error_o,
  output logic                  local_flush_active_o
);

  //==========================================================
  // Внутренние сигналы между FSM
  //==========================================================

  // Ingress
  logic                ing_fifo_wr;
  logic [DATA_WIDTH-1:0] ing_fifo_wdata;
  logic                ing_drop_pkt;
  logic                ing_error;
  logic                ing_heartbeat;
  logic [1:0]          ing_class_id;
  logic [15:0]         ing_pkt_len;

  // Egress
  logic                eg_fifo_rd;
  logic [DATA_WIDTH-1:0] eg_fifo_rdata;
  logic                eg_fifo_empty;
  logic                eg_error;
  logic                eg_heartbeat;
  logic                eg_need_credit;
  logic                eg_credit_consume;
  logic                eg_retry_pulse;

  // Буфер между ingress и egress (упрощённый)
  logic [DATA_WIDTH-1:0] fifo_mem   [0:15];
  logic [3:0]            fifo_wr_ptr;
  logic [3:0]            fifo_rd_ptr;
  logic [4:0]            fifo_count;
  logic                  fifo_full;
  logic                  fifo_almost_full;

  // Кредиты
  logic                cr_credits_ok;
  logic                cr_pause_req;
  logic                cr_error;

  // Менеджер ошибок
  logic                err_local_flush;
  logic                err_global_flush;
  logic                err_soft_reset_req;
  logic                err_hard_reset_req;

  // Watchdog
  logic                wd_expired;

  //==========================================================
  // Упрощённый FIFO между ingress и egress
  // (без отдельного FSM, только счётчики/флаги)
//==========================================================
  assign fifo_full        = (fifo_count == 16);
  assign fifo_almost_full = (fifo_count >= 14);
  assign eg_fifo_empty    = (fifo_count == 0);

  // запись
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      fifo_wr_ptr <= '0;
      fifo_count  <= '0;
    end
    else begin
      // soft reset от error manager
      if (err_soft_reset_req) begin
        fifo_wr_ptr <= '0;
        fifo_count  <= '0;
      end
      else begin
        if (ing_fifo_wr && !fifo_full) begin
          fifo_mem[fifo_wr_ptr] <= ing_fifo_wdata;
          fifo_wr_ptr           <= fifo_wr_ptr + 1'b1;
          fifo_count            <= fifo_count + 1'b1;
        end
        // чтение в egress
        if (eg_fifo_rd && !eg_fifo_empty) begin
          fifo_rd_ptr <= fifo_rd_ptr + 1'b1;
          fifo_count  <= fifo_count - 1'b1;
        end
      end
    end
  end

  assign eg_fifo_rdata = fifo_mem[fifo_rd_ptr];

  //==========================================================
  // Ingress FSM
  //==========================================================
  ingress_fsm #(
    .DATA_WIDTH    (DATA_WIDTH),
    .MAX_PKT_WORDS (MAX_PKT_WORDS)
  ) u_ingress_fsm (
    .clk              (clk),
    .rst_n            (rst_n & ~err_hard_reset_req),

    .in_valid_i       (in_valid_i),
    .in_data_i        (in_data_i),
    .in_sop_i         (in_sop_i),
    .in_eop_i         (in_eop_i),

    .buf_full_i       (fifo_full),
    .buf_almost_full_i(fifo_almost_full),
    .local_flush_i    (err_local_flush),
    .global_pause_i   (cr_pause_req),

    .fifo_wr_o        (ing_fifo_wr),
    .fifo_wdata_o     (ing_fifo_wdata),
    .drop_pkt_o       (ing_drop_pkt),
    .class_id_o       (ing_class_id),
    .pkt_len_o        (ing_pkt_len),
    .heartbeat_o      (ing_heartbeat),
    .error_o          (ing_error)
  );

  //==========================================================
  // Egress FSM
  //==========================================================
  egress_fsm #(
    .DATA_WIDTH    (DATA_WIDTH),
    .MAX_PKT_WORDS (MAX_PKT_WORDS)
  ) u_egress_fsm (
    .clk              (clk),
    .rst_n            (rst_n & ~err_hard_reset_req),

    .fifo_empty_i     (eg_fifo_empty),
    .fifo_rdata_i     (eg_fifo_rdata),

    .credits_ok_i     (cr_credits_ok),
    .pause_i          (cr_pause_req),
    .local_flush_i    (err_local_flush),
    .global_flush_i   (err_global_flush),

    .out_ready_i      (out_ready_i),

    .fifo_rd_o        (eg_fifo_rd),
    .need_credit_o    (eg_need_credit),
    .credit_consume_o (eg_credit_consume),

    .out_valid_o      (out_valid_o),
    .out_data_o       (out_data_o),
    .out_sop_o        (out_sop_o),
    .out_eop_o        (out_eop_o),

    .retry_pulse_o    (eg_retry_pulse),
    .heartbeat_o      (eg_heartbeat),
    .error_o          (eg_error)
  );

  //==========================================================
  // Credit controller FSM
  //==========================================================
  credit_ctrl_fsm #(
    .MAX_CREDITS (MAX_CREDITS)
  ) u_credit_ctrl_fsm (
    .clk              (clk),
    .rst_n            (rst_n & ~err_hard_reset_req),

    .need_credit_i    (eg_need_credit),
    .credit_consume_i (eg_credit_consume),
    .retry_pulse_i    (eg_retry_pulse),

    .local_flush_i    (err_local_flush),
    .global_flush_i   (err_global_flush),

    .credits_ok_o     (cr_credits_ok),
    .pause_req_o      (cr_pause_req),
    .error_o          (cr_error)
  );

  //==========================================================
  // Error manager FSM
  //==========================================================
  error_mgr_fsm u_error_mgr_fsm (
    .clk               (clk),
    .rst_n             (rst_n),

    .ing_error_i       (ing_error),
    .eg_error_i        (eg_error),
    .cr_error_i        (cr_error),
    .wd_expired_i      (wd_expired),

    .local_flush_o     (err_local_flush),
    .global_flush_o    (err_global_flush),
    .soft_reset_req_o  (err_soft_reset_req),
    .hard_reset_req_o  (err_hard_reset_req),
    .global_error_o    (global_error_o)
  );

  assign local_flush_active_o = err_local_flush;

  //==========================================================
  // Watchdog FSM
  //==========================================================
  watchdog_fsm #(
    .MAX_CYCLES (WD_MAX_CYCLES)
  ) u_watchdog_fsm (
    .clk          (clk),
    .rst_n        (rst_n),

    .ing_heartbeat_i (ing_heartbeat),
    .eg_heartbeat_i  (eg_heartbeat),
    .enable_i        (1'b1),

    .expired_o       (wd_expired)
  );

endmodule : complex_fsm_top

//============================================================
// Ingress FSM: приём и парсинг пакетов
//============================================================
module ingress_fsm #(
  parameter int DATA_WIDTH    = 32,
  parameter int MAX_PKT_WORDS = 256
) (
  input  logic                  clk,
  input  logic                  rst_n,

  input  logic                  in_valid_i,
  input  logic [DATA_WIDTH-1:0] in_data_i,
  input  logic                  in_sop_i,
  input  logic                  in_eop_i,

  input  logic                  buf_full_i,
  input  logic                  buf_almost_full_i,
  input  logic                  local_flush_i,
  input  logic                  global_pause_i,

  output logic                  fifo_wr_o,
  output logic [DATA_WIDTH-1:0] fifo_wdata_o,
  output logic                  drop_pkt_o,
  output logic [1:0]            class_id_o,
  output logic [15:0]           pkt_len_o,
  output logic                  heartbeat_o,
  output logic                  error_o
);

  ingress_state_t state, next_state;

  logic [DATA_WIDTH-1:0] hdr_reg;
  logic [15:0]           len_counter;
  logic [7:0]            error_counter;
  logic                  hdr_is_valid;
  logic                  hdr_is_control;
  logic                  length_ok;

  //----------------------------------------------------------
  // Простая "логика заголовка"
  //----------------------------------------------------------
  assign hdr_is_valid   = (hdr_reg[31:28] != 4'h0);
  assign hdr_is_control = (hdr_reg[31:28] == 4'hF);

  // Класс — по двум старшим битам поля
  assign class_id_o = hdr_reg[27:26];

  assign length_ok  = (len_counter <= MAX_PKT_WORDS[15:0]);

  //----------------------------------------------------------
  // Выходы по состоянию
  //----------------------------------------------------------
  always_comb begin
    fifo_wr_o     = 1'b0;
    fifo_wdata_o  = in_data_i;
    drop_pkt_o    = 1'b0;
    error_o       = 1'b0;

    unique case (state)
      IN_PUSH_PAYLOAD: begin
        if (in_valid_i && !buf_full_i && !local_flush_i && !global_pause_i) begin
          fifo_wr_o    = 1'b1;
          fifo_wdata_o = in_data_i;
        end
      end

      IN_DROP_PKT,
      IN_ERR_HOLD: begin
        drop_pkt_o = 1'b1;
      end

      IN_ERR_HOLD,
      IN_ERR_RECOVER: begin
        error_o = 1'b1;
      end

      default: ;
    endcase
  end

  // Простейшее "сердцебиение" — инвертируем бит в некоторых состояниях
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      heartbeat_o <= 1'b0;
    end
    else if (state == IN_PARSE_HDR || state == IN_PUSH_PAYLOAD) begin
      heartbeat_o <= ~heartbeat_o;
    end
  end

  //----------------------------------------------------------
  // Переходы по состояниям
  //----------------------------------------------------------
  always_comb begin
    next_state = state;

    unique case (state)
      IN_IDLE: begin
        if (local_flush_i) begin
          next_state = IN_FLUSH_REST;
        end
        else if (in_valid_i && in_sop_i && !global_pause_i) begin
          if (buf_full_i) begin
            // нет места — сразу в дроп
            next_state = IN_DROP_PKT;
          end
          else begin
            next_state = IN_WAIT_SOP;
          end
        end
      end

      IN_WAIT_SOP: begin
        // формально мы уже видели sop, но ждём первый валидный цикл
        if (in_valid_i) begin
          next_state = IN_PARSE_HDR;
        end
        else if (!in_sop_i) begin
          // передумали
          next_state = IN_IDLE;
        end
      end

      IN_PARSE_HDR: begin
        if (local_flush_i) begin
          next_state = IN_FLUSH_REST;
        end
        else if (in_valid_i) begin
          if (!hdr_is_valid) begin
            next_state = IN_ERR_HOLD;
          end
          else begin
            next_state = IN_CLASSIFY;
          end
        end
      end

      IN_CLASSIFY: begin
        // если пакет "управляющий" и буфер почти заполнен — дропаем
        if (hdr_is_control && buf_almost_full_i) begin
          next_state = IN_DROP_PKT;
        end
        else begin
          next_state = IN_CHECK_LEN;
        end
      end

      IN_CHECK_LEN: begin
        // если длина уже превышена — ошибка
        if (!length_ok) begin
          next_state = IN_ERR_HOLD;
        end
        else begin
          next_state = IN_PUSH_PAYLOAD;
        end
      end

      IN_PUSH_PAYLOAD: begin
        if (local_flush_i) begin
          next_state = IN_FLUSH_REST;
        end
        else if (buf_full_i) begin
          // переполнение — ошибка
          next_state = IN_ERR_HOLD;
        end
        else if (in_valid_i && in_eop_i) begin
          // закончили пакет
          if (!length_ok) begin
            next_state = IN_ERR_HOLD;
          end
          else begin
            next_state = IN_IDLE;
          end
        end
      end

      IN_DROP_PKT: begin
        // просто ждём конца пакета
        if (in_valid_i && in_eop_i) begin
          next_state = IN_IDLE;
        end
      end

      IN_FLUSH_REST: begin
        // сбрасываем всё до конца пакета
        if (in_valid_i && in_eop_i) begin
          next_state = IN_IDLE;
        end
      end

      IN_ERR_HOLD: begin
        // Накопление ошибок: если их слишком много — останемся тут
        if (error_counter >= 8'h20 && !local_flush_i) begin
          next_state = IN_ERR_RECOVER;
        end
        else if (local_flush_i) begin
          next_state = IN_FLUSH_REST;
        end
      end

      IN_ERR_RECOVER: begin
        // простая модель восстановления: один цикл и в IDLE
        if (!local_flush_i) begin
          next_state = IN_IDLE;
        end
      end

      default: next_state = IN_ERR_HOLD;
    endcase
  end

  //----------------------------------------------------------
  // Регистровая часть
  //----------------------------------------------------------
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state         <= IN_IDLE;
      hdr_reg       <= '0;
      len_counter   <= '0;
      pkt_len_o     <= '0;
      error_counter <= '0;
    end
    else begin
      state <= next_state;

      // захват заголовка
      if (state == IN_WAIT_SOP && in_valid_i) begin
        hdr_reg <= in_data_i;
      end

      // счётчик длины
      if (state == IN_IDLE || state == IN_ERR_RECOVER || local_flush_i) begin
        len_counter <= '0;
        pkt_len_o   <= '0;
      end
      else if (state == IN_PUSH_PAYLOAD && in_valid_i) begin
        len_counter <= len_counter + 1'b1;
        if (in_eop_i) begin
          pkt_len_o <= len_counter + 1'b1;
        end
      end

      // счётчик ошибок
      if (state == IN_ERR_HOLD && next_state == IN_ERR_HOLD) begin
        error_counter <= error_counter + 1'b1;
      end
      else if (state == IN_ERR_RECOVER || local_flush_i) begin
        error_counter <= '0;
      end
    end
  end

endmodule : ingress_fsm

//============================================================
// Egress FSM: выдача из буфера, кредиты, ретраи
//============================================================
module egress_fsm #(
  parameter int DATA_WIDTH    = 32,
  parameter int MAX_PKT_WORDS = 256
) (
  input  logic                  clk,
  input  logic                  rst_n,

  input  logic                  fifo_empty_i,
  input  logic [DATA_WIDTH-1:0] fifo_rdata_i,

  input  logic                  credits_ok_i,
  input  logic                  pause_i,
  input  logic                  local_flush_i,
  input  logic                  global_flush_i,

  input  logic                  out_ready_i,

  output logic                  fifo_rd_o,
  output logic                  need_credit_o,
  output logic                  credit_consume_o,

  output logic                  out_valid_o,
  output logic [DATA_WIDTH-1:0] out_data_o,
  output logic                  out_sop_o,
  output logic                  out_eop_o,

  output logic                  retry_pulse_o,
  output logic                  heartbeat_o,
  output logic                  error_o
);

  egress_state_t state, next_state;

  logic [DATA_WIDTH-1:0] data_reg;
  logic [15:0]           word_counter;
  logic [1:0]            retry_counter;

  //----------------------------------------------------------
  // heartbeat
  //----------------------------------------------------------
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      heartbeat_o <= 1'b0;
    end
    else if (state == EG_SEND_PAYLOAD || state == EG_SEND_HDR) begin
      heartbeat_o <= ~heartbeat_o;
    end
  end

  //----------------------------------------------------------
  // Выходы по состоянию
  //----------------------------------------------------------
  always_comb begin
    fifo_rd_o        = 1'b0;
    need_credit_o    = 1'b0;
    credit_consume_o = 1'b0;
    out_valid_o      = 1'b0;
    out_data_o       = data_reg;
    out_sop_o        = 1'b0;
    out_eop_o        = 1'b0;
    retry_pulse_o    = 1'b0;
    error_o          = 1'b0;

    unique case (state)
      EG_ARB_REQ: begin
        need_credit_o = 1'b1;
      end

      EG_DEQUEUE: begin
        fifo_rd_o = !fifo_empty_i && !pause_i && !local_flush_i && !global_flush_i;
      end

      EG_SEND_HDR: begin
        out_valid_o = 1'b1;
        out_sop_o   = 1'b1;
        out_data_o  = data_reg;
      end

      EG_SEND_PAYLOAD: begin
        out_valid_o = 1'b1;
        out_data_o  = data_reg;
        if (word_counter == 16'd1) begin
          out_eop_o = 1'b1;
        end
      end

      EG_WAIT_ACK,
      EG_RETRY,
      EG_ERROR: begin
        error_o = (state == EG_ERROR);
      end

      EG_DRAIN: begin
        fifo_rd_o = !fifo_empty_i;
      end

      EG_PAUSE: begin
        // ничего не делаем, просто удерживаемся
      end

      default: ;
    endcase
  end

  //----------------------------------------------------------
  // Переходы
  //----------------------------------------------------------
  always_comb begin
    next_state = state;

    unique case (state)
      EG_IDLE: begin
        if (local_flush_i || global_flush_i) begin
          next_state = EG_DRAIN;
        end
        else if (!fifo_empty_i && !pause_i) begin
          next_state = EG_ARB_REQ;
        end
      end

      EG_ARB_REQ: begin
        if (local_flush_i || global_flush_i) begin
          next_state = EG_DRAIN;
        end
        else if (credits_ok_i) begin
          next_state = EG_DEQUEUE;
        end
        else if (pause_i) begin
          next_state = EG_PAUSE;
        end
      end

      EG_DEQUEUE: begin
        if (local_flush_i || global_flush_i) begin
          next_state = EG_DRAIN;
        end
        else if (!fifo_empty_i) begin
          next_state = EG_SEND_HDR;
        end
        else begin
          next_state = EG_IDLE;
        end
      end

      EG_SEND_HDR: begin
        if (!out_ready_i) begin
          next_state = EG_PAUSE;
        end
        else begin
          next_state = EG_SEND_PAYLOAD;
        end
      end

      EG_SEND_PAYLOAD: begin
        if (local_flush_i || global_flush_i) begin
          next_state = EG_DRAIN;
        end
        else if (!out_ready_i) begin
          next_state = EG_PAUSE;
        end
        else if (word_counter == 16'd1) begin
          next_state = EG_WAIT_ACK;
        end
      end

      EG_WAIT_ACK: begin
        // модель ACK/NACK: используем bit fifo_rdata_i[0] как "успех"
        if (credits_ok_i) begin
          // считаем, что ack получен
          next_state = EG_IDLE;
        end
        else if (retry_counter < 2) begin
          next_state = EG_RETRY;
        end
        else begin
          next_state = EG_ERROR;
        end
      end

      EG_RETRY: begin
        if (local_flush_i || global_flush_i) begin
          next_state = EG_DRAIN;
        end
        else if (!pause_i) begin
          next_state = EG_ARB_REQ;
        end
      end

      EG_DRAIN: begin
        if (fifo_empty_i) begin
          next_state = EG_IDLE;
        end
      end

      EG_PAUSE: begin
        if (local_flush_i || global_flush_i) begin
          next_state = EG_DRAIN;
        end
        else if (!pause_i && out_ready_i) begin
          // возвращаемся туда, где остановились
          if (word_counter == 0)        next_state = EG_IDLE;
          else if (word_counter == 16'hFFFF) next_state = EG_SEND_HDR;
          else                          next_state = EG_SEND_PAYLOAD;
        end
      end

      EG_ERROR: begin
        // ждём локального flush для очистки
        if (local_flush_i) begin
          next_state = EG_DRAIN;
        end
      end

      default: next_state = EG_ERROR;
    endcase
  end

  //----------------------------------------------------------
  // Регистровая часть
  //----------------------------------------------------------
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state         <= EG_IDLE;
      data_reg      <= '0;
      word_counter  <= '0;
      retry_counter <= '0;
    end
    else begin
      state <= next_state;

      // захват данных из FIFO
      if (fifo_rd_o && !fifo_empty_i) begin
        data_reg <= fifo_rdata_i;
        // в нашем протоколе первый слово — заголовок, затем payload
        word_counter <= MAX_PKT_WORDS[15:0];
      end
      else if (state == EG_SEND_PAYLOAD && out_ready_i && word_counter != 0) begin
        word_counter <= word_counter - 1'b1;
      end

      // учёт кредитов
      if (state == EG_SEND_HDR && out_ready_i && credits_ok_i) begin
        credit_consume_o <= 1'b1;
      end
      else begin
        credit_consume_o <= 1'b0;
      end

      // счётчик ретраев
      if (state == EG_WAIT_ACK && next_state == EG_RETRY) begin
        retry_counter <= retry_counter + 1'b1;
        retry_pulse_o <= 1'b1;
      end
      else if (state == EG_IDLE) begin
        retry_counter <= '0;
        retry_pulse_o <= 1'b0;
      end
      else begin
        retry_pulse_o <= 1'b0;
      end
    end
  end

endmodule : egress_fsm

//============================================================
// Credit controller FSM
//============================================================
module credit_ctrl_fsm #(
  parameter int MAX_CREDITS = 8
) (
  input  logic clk,
  input  logic rst_n,

  input  logic need_credit_i,
  input  logic credit_consume_i,
  input  logic retry_pulse_i,

  input  logic local_flush_i,
  input  logic global_flush_i,

  output logic credits_ok_o,
  output logic pause_req_o,
  output logic error_o
);

  credit_state_t state, next_state;

  logic [$clog2(MAX_CREDITS+1)-1:0] credit_count;

  //----------------------------------------------------------
  // Выходы
  //----------------------------------------------------------
  always_comb begin
    credits_ok_o = 1'b0;
    pause_req_o  = 1'b0;
    error_o      = 1'b0;

    unique case (state)
      CR_IDLE,
      CR_GRANT,
      CR_WAIT_CONSUME: begin
        credits_ok_o = (credit_count != 0);
      end

      CR_UNDERFLOW,
      CR_OVERFLOW,
      CR_FREEZE: begin
        error_o = 1'b1;
        pause_req_o = 1'b1;
      end

      CR_RECOVER: begin
        pause_req_o = 1'b1;
      end

      default: ;
    endcase
  end

  //----------------------------------------------------------
  // Переходы
  //----------------------------------------------------------
  always_comb begin
    next_state = state;

    unique case (state)
      CR_IDLE: begin
        if (global_flush_i) begin
          next_state = CR_FREEZE;
        end
        else if (local_flush_i) begin
          next_state = CR_RECOVER;
        end
        else if (need_credit_i && (credit_count == 0)) begin
          next_state = CR_UNDERFLOW;
        end
        else if (need_credit_i && (credit_count != 0)) begin
          next_state = CR_GRANT;
        end
      end

      CR_GRANT: begin
        if (credit_count == 0) begin
          next_state = CR_UNDERFLOW;
        end
        else begin
          next_state = CR_WAIT_CONSUME;
        end
      end

      CR_WAIT_CONSUME: begin
        if (credit_consume_i) begin
          if (credit_count == 0) begin
            next_state = CR_UNDERFLOW;
          end
          else begin
            next_state = CR_IDLE;
          end
        end
        else if (retry_pulse_i) begin
          // при ретрае считаем, что кредит возвращается
          next_state = CR_IDLE;
        end
      end

      CR_UNDERFLOW: begin
        if (local_flush_i || global_flush_i) begin
          next_state = CR_RECOVER;
        end
      end

      CR_OVERFLOW: begin
        if (local_flush_i || global_flush_i) begin
          next_state = CR_RECOVER;
        end
      end

      CR_FREEZE: begin
        if (!global_flush_i) begin
          next_state = CR_RECOVER;
        end
      end

      CR_RECOVER: begin
        // один цикл восстановления
        if (!local_flush_i && !global_flush_i) begin
          next_state = CR_IDLE;
        end
      end

      default: next_state = CR_FREEZE;
    endcase
  end

  //----------------------------------------------------------
  // Регистровая часть
  //----------------------------------------------------------
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state        <= CR_IDLE;
      credit_count <= MAX_CREDITS[$clog2(MAX_CREDITS+1)-1:0];
    end
    else begin
      state <= next_state;

      // модель: кредиты уменьшаются при потреблении и восстанавливаются при retry
      if (credit_consume_i && credit_count != 0) begin
        credit_count <= credit_count - 1'b1;
      end
      else if (retry_pulse_i && credit_count < MAX_CREDITS[$clog2(MAX_CREDITS+1)-1:0]) begin
        credit_count <= credit_count + 1'b1;
      end

      // при глобальном flush — жёстко обнуляем
      if (global_flush_i) begin
        credit_count <= '0;
      end
      else if (state == CR_RECOVER && next_state == CR_IDLE) begin
        credit_count <= MAX_CREDITS[$clog2(MAX_CREDITS+1)-1:0];
      end
    end
  end

endmodule : credit_ctrl_fsm

//============================================================
// Error manager FSM
//============================================================
module error_mgr_fsm (
  input  logic clk,
  input  logic rst_n,

  input  logic ing_error_i,
  input  logic eg_error_i,
  input  logic cr_error_i,
  input  logic wd_expired_i,

  output logic local_flush_o,
  output logic global_flush_o,
  output logic soft_reset_req_o,
  output logic hard_reset_req_o,
  output logic global_error_o
);

  error_state_t state, next_state;

  logic [7:0] fault_counter;

  //----------------------------------------------------------
  // Выходы
  //----------------------------------------------------------
  always_comb begin
    local_flush_o     = 1'b0;
    global_flush_o    = 1'b0;
    soft_reset_req_o  = 1'b0;
    hard_reset_req_o  = 1'b0;
    global_error_o    = 1'b0;

    unique case (state)
      ER_MONITOR: begin
        // ничего не делаем
      end

      ER_LOCAL_FAULT: begin
        local_flush_o = 1'b1;
      end

      ER_GLOBAL_FAULT: begin
        local_flush_o  = 1'b1;
        global_flush_o = 1'b1;
      end

      ER_ISOLATE: begin
        global_flush_o    = 1'b1;
        soft_reset_req_o  = 1'b1;
      end

      ER_CLEAR: begin
        soft_reset_req_o = 1'b1;
      end

      ER_RECOVER: begin
        global_error_o = 1'b0;
      end

      default: ;
    endcase

    if (state == ER_GLOBAL_FAULT || state == ER_ISOLATE) begin
      global_error_o = 1'b1;
    end
  end

  //----------------------------------------------------------
  // Переходы
  //----------------------------------------------------------
  always_comb begin
    next_state = state;

    unique case (state)
      ER_IDLE: begin
        if (ing_error_i || eg_error_i || cr_error_i || wd_expired_i) begin
          next_state = ER_MONITOR;
        end
      end

      ER_MONITOR: begin
        if (wd_expired_i || (ing_error_i && eg_error_i) || cr_error_i) begin
          next_state = ER_GLOBAL_FAULT;
        end
        else if (ing_error_i || eg_error_i) begin
          next_state = ER_LOCAL_FAULT;
        end
        else if (!ing_error_i && !eg_error_i && !cr_error_i && !wd_expired_i) begin
          next_state = ER_IDLE;
        end
      end

      ER_LOCAL_FAULT: begin
        if (wd_expired_i || cr_error_i) begin
          next_state = ER_GLOBAL_FAULT;
        end
        else begin
          next_state = ER_CLEAR;
        end
      end

      ER_GLOBAL_FAULT: begin
        if (fault_counter > 8'd10) begin
          next_state = ER_ISOLATE;
        end
      end

      ER_ISOLATE: begin
        hard_reset_req_o = 1'b1;
        if (fault_counter > 8'd20) begin
          next_state = ER_RECOVER;
        end
      end

      ER_CLEAR: begin
        if (!ing_error_i && !eg_error_i && !cr_error_i) begin
          next_state = ER_RECOVER;
        end
      end

      ER_RECOVER: begin
        if (!ing_error_i && !eg_error_i && !cr_error_i && !wd_expired_i) begin
          next_state = ER_IDLE;
        end
      end

      default: next_state = ER_IDLE;
    endcase
  end

  //----------------------------------------------------------
  // Регистровая часть
  //----------------------------------------------------------
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state         <= ER_IDLE;
      fault_counter <= '0;
    end
    else begin
      state <= next_state;

      if (state == ER_GLOBAL_FAULT || state == ER_ISOLATE) begin
        fault_counter <= fault_counter + 1'b1;
      end
      else if (state == ER_RECOVER || state == ER_IDLE) begin
        fault_counter <= '0;
      end
    end
  end

endmodule : error_mgr_fsm

//============================================================
// Watchdog FSM
//============================================================
module watchdog_fsm #(
  parameter int MAX_CYCLES = 1024
) (
  input  logic clk,
  input  logic rst_n,

  input  logic ing_heartbeat_i,
  input  logic eg_heartbeat_i,
  input  logic enable_i,

  output logic expired_o
);

  watchdog_state_t state, next_state;

  logic [$clog2(MAX_CYCLES+1)-1:0] counter;
  logic                             hb_xor;

  assign hb_xor   = ing_heartbeat_i ^ eg_heartbeat_i;
  assign expired_o = (state == WD_EXPIRED);

  //----------------------------------------------------------
  // Переходы
  //----------------------------------------------------------
  always_comb begin
    next_state = state;

    unique case (state)
      WD_IDLE: begin
        if (enable_i) begin
          next_state = WD_ARMED;
        end
      end

      WD_ARMED: begin
        if (!enable_i) begin
          next_state = WD_IDLE;
        end
        else if (hb_xor) begin
          next_state = WD_COUNT;
        end
      end

      WD_COUNT: begin
        if (!enable_i) begin
          next_state = WD_IDLE;
        end
        else if (hb_xor) begin
          // успешный "тик" сторожевика — перезапускаем
          next_state = WD_ARMED;
        end
        else if (counter >= MAX_CYCLES[$clog2(MAX_CYCLES+1)-1:0]) begin
          next_state = WD_EXPIRED;
        end
      end

      WD_EXPIRED: begin
        next_state = WD_HOLD;
      end

      WD_HOLD: begin
        // остаёмся здесь, пока не снимут enable
        if (!enable_i) begin
          next_state = WD_IDLE;
        end
      end

      default: next_state = WD_IDLE;
    endcase
  end

  //----------------------------------------------------------
  // Регистровая часть
  //----------------------------------------------------------
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state   <= WD_IDLE;
      counter <= '0;
    end
    else begin
      state <= next_state;

      case (next_state)
        WD_IDLE:   counter <= '0;
        WD_ARMED:  counter <= '0;
        WD_COUNT:  counter <= counter + 1'b1;
        WD_EXPIRED,
        WD_HOLD:   counter <= counter;
        default:   counter <= '0;
      endcase
    end
  end

endmodule : watchdog_fsm

"""
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", example)

    # --------------------------------------------------------
    # File / parsing handlers
    # --------------------------------------------------------

    def menu_open_sv(self):
        path = filedialog.askopenfilename(
            title="Open SystemVerilog file",
            filetypes=[("SystemVerilog files", "*.sv *.svh *.v"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            self.current_filename = path
            self.editor.delete("1.0", tk.END)
            self.editor.insert("1.0", text)
            self.parse_sv_text(text, filename_hint=os.path.basename(path))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file:\n{e}")

    def parse_from_editor(self):
        text = self.editor.get("1.0", tk.END)
        self.parse_sv_text(text, filename_hint=self.current_filename or "editor_code.sv")

    def parse_sv_text(self, sv_text: str, filename_hint: str = "source.sv"):
        try:
            cst = CSTService()
            tree = cst.build_cst_from_text(sv_text, filename_hint)
            graphs = build_fsm_graphs_from_cst(tree)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse FSM:\n{e}")
            return

        self.graphs = graphs
        self.current_graph_index = None
        self._update_fsm_listbox()

        if not graphs:
            messagebox.showinfo("FSM Visualizer", "FSM-графы не найдены.")
        else:
            # выбрать первый граф
            self.fsm_listbox.selection_clear(0, tk.END)
            self.fsm_listbox.selection_set(0)
            self.fsm_listbox.event_generate("<<ListboxSelect>>")

    def _update_fsm_listbox(self):
        self.fsm_listbox.delete(0, tk.END)
        for i, g in enumerate(self.graphs):
            scope = g.get("scope", "")
            enum_name = g.get("enum_name", "")
            state_var = g.get("state_var", "state")

            label = f"{i}: [{scope}] {enum_name or '<anon enum>'} / {state_var}"
            self.fsm_listbox.insert(tk.END, label)

    # --------------------------------------------------------
    # FSM selection and redraw
    # --------------------------------------------------------

    def on_fsm_select(self, event=None):
        sel = self.fsm_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < 0 or idx >= len(self.graphs):
            return
        self.current_graph_index = idx
        self.redraw_current_graph()
        self.update_details_panel()

    def get_current_graph(self) -> Optional[Dict[str, Any]]:
        if self.current_graph_index is None:
            return None
        if not (0 <= self.current_graph_index < len(self.graphs)):
            return None
        return self.graphs[self.current_graph_index]

    def redraw_current_graph(self):
        graph = self.get_current_graph()
        if graph is None:
            self.canvas.delete("all")
            return

        self.canvas.delete("all")

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 10 or height <= 10:
            return

        zoom = float(self.zoom_var.get() or 1.0)

        states: List[str] = list(graph.get("states", []))
        transitions: List[Dict[str, Any]] = list(graph.get("transitions", []))
        reset_state = graph.get("reset_state")

        if not states:
            return

        cx = width / 2
        cy = height / 2
        radius = min(width, height) * 0.35 * zoom

        node_positions: Dict[str, tuple] = {}
        n = len(states)
        for i, s in enumerate(states):
            angle = 2 * math.pi * i / n - math.pi / 2
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            node_positions[s] = (x, y)

        node_r = 24 * zoom

        # Рисуем рёбра
        for t in transitions:
            frm = t.get("from")
            to = t.get("to")
            cond = _normalize_cond(t.get("cond"))
            if frm not in node_positions or to not in node_positions:
                continue

            x1, y1 = node_positions[frm]
            x2, y2 = node_positions[to]

            dx = x2 - x1
            dy = y2 - y1
            dist = math.hypot(dx, dy) or 1.0
            ux, uy = dx / dist, dy / dist

            start_x = x1 + ux * node_r
            start_y = y1 + uy * node_r
            end_x = x2 - ux * node_r
            end_y = y2 - uy * node_r

            self.canvas.create_line(
                start_x,
                start_y,
                end_x,
                end_y,
                arrow=tk.LAST,
                width=2,
                fill="#333333"
            )

            if cond and cond != "1":
                mx = (start_x + end_x) / 2
                my = (start_y + end_y) / 2
                off = 10 * zoom
                nx = -uy
                ny = ux
                label_x = mx + nx * off
                label_y = my + ny * off

                self.canvas.create_text(
                    label_x,
                    label_y,
                    text=cond,
                    font=("Helvetica", max(int(9 * zoom), 7)),
                    fill="#000000"
                )

        # Рисуем узлы
        for s in states:
            x, y = node_positions[s]

            if reset_state and s == reset_state:
                self.canvas.create_oval(
                    x - (node_r + 4),
                    y - (node_r + 4),
                    x + (node_r + 4),
                    y + (node_r + 4),
                    fill="#e8ffe8",
                    outline="#006600",
                    width=2
                )
                self.canvas.create_oval(
                    x - (node_r - 2),
                    y - (node_r - 2),
                    x + (node_r - 2),
                    y + (node_r - 2),
                    outline="#006600",
                    width=2
                )
            else:
                self.canvas.create_oval(
                    x - node_r,
                    y - node_r,
                    x + node_r,
                    y + node_r,
                    fill="#eef2ff",
                    outline="#333366",
                    width=2
                )

            self.canvas.create_text(
                x,
                y,
                text=s,
                font=("Helvetica", max(int(10 * zoom), 8)),
                fill="#000000"
            )

    # --------------------------------------------------------
    # Details panel
    # --------------------------------------------------------

    def update_details_panel(self):
        graph = self.get_current_graph()
        self.details_text.delete("1.0", tk.END)
        for row in self.transitions_tree.get_children():
            self.transitions_tree.delete(row)

        if graph is None:
            return

        scope = graph.get("scope", "")
        enum_name = graph.get("enum_name", "")
        state_var = graph.get("state_var", "state")
        next_state_var = graph.get("next_state_var")
        reset_state = graph.get("reset_state")
        meta = graph.get("metadata", {}) or {}
        num_states = meta.get("num_states", len(graph.get("states", [])))
        num_trans = meta.get("num_transitions", len(graph.get("transitions", [])))

        lines = []
        lines.append(f"Scope (module/class/etc): {scope}")
        lines.append(f"Enum type: {enum_name or '(anonymous)'}")
        lines.append(f"State variable: {state_var}")
        lines.append(f"Next state variable: {next_state_var or '(none)'}")
        lines.append(f"Reset state: {reset_state or '(unknown)'}")
        lines.append("")
        lines.append(f"States ({num_states}):")
        for s in graph.get("states", []):
            lines.append(f"  - {s}")
        lines.append("")
        lines.append(f"Transitions ({num_trans}):")

        for t in graph.get("transitions", []):
            frm = t.get("from")
            to = t.get("to")
            cond = _normalize_cond(t.get("cond"))
            if not cond or cond == "1":
                lines.append(f"  {frm} -> {to}")
            else:
                lines.append(f"  {frm} --[{cond}]--> {to}")

        self.details_text.insert("1.0", "\n".join(lines))

        # Таблица переходов
        for t in graph.get("transitions", []):
            frm = t.get("from")
            to = t.get("to")
            cond = _normalize_cond(t.get("cond"))
            if not cond or cond == "1":
                cond = ""
            self.transitions_tree.insert("", tk.END, values=(frm, to, cond))

    # --------------------------------------------------------
    # Export
    # --------------------------------------------------------

    def export_current_graph_as_html(self):
        graph = self.get_current_graph()
        if graph is None:
            messagebox.showinfo("Export", "FSM не выбран.")
            return

        default_name = "fsm_graph.html"
        if self.current_filename:
            base = os.path.splitext(os.path.basename(self.current_filename))[0]
            default_name = f"{base}_fsm_{self.current_graph_index or 0}.html"

        path = filedialog.asksaveasfilename(
            title="Save FSM as HTML",
            defaultextension=".html",
            initialfile=default_name,
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            title = f"FSM Graph #{self.current_graph_index or 0} - {graph.get('scope','')}"
            html = fsm_graph_to_html(graph, title=title, width=900, height=650)
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            messagebox.showinfo("Export", f"HTML сохранён:\n{path}")
        except Exception as e:
            messagebox.showerror("Export error", f"Не удалось сохранить HTML:\n{e}")


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    app = FSMGuiApp()
    app.mainloop()
