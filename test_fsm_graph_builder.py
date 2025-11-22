# -*- coding: utf-8 -*-
"""
test_fsm_graph_builder.py

Набор автотестов для fsm_graph_builder.build_fsm_graphs_from_cst.

Запуск:
    python test_fsm_graph_builder.py

Предполагается, что рядом лежат:
  - cst_service.py
  - enum_detector_cst.py
  - fsm_enum_candidates_cst.py
  - fsm_graph_builder.py
"""

from typing import Any, Dict, List, Optional, Tuple
from pprint import pprint

from cst_service import CSTService
from fsm_graph_builder import build_fsm_graphs_from_cst


# ==============================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ СРАВНЕНИЯ
# ==============================

def normalize_cond(cond: Optional[str]) -> str:
    """Приводим условие к нормализованному виду для сравнения."""
    if cond is None:
        return "1"
    c = cond.strip()
    return c if c else "1"


def transitions_to_set(transitions: List[Dict[str, Any]]) -> set:
    """
    Преобразовать список переходов к множеству кортежей:
        (from, to, cond)
    где cond уже нормализован.
    """
    res = set()
    for t in transitions:
        frm = t.get("from")
        to = t.get("to")
        cond = normalize_cond(t.get("cond"))
        res.add((frm, to, cond))
    return res


def check_graph(actual: Dict[str, Any], expected: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Сравнить один реальный граф с ожидаемым.

    Проверяем:
      - scope (если указан в expected)
      - enum_name (если указан)
      - state_var (если указан)
      - множество состояний
      - множество переходов (from, to, cond)
    """
    # scope
    exp_scope = expected.get("scope")
    if exp_scope is not None and actual.get("scope") != exp_scope:
        return False, f"scope mismatch: expected {exp_scope}, got {actual.get('scope')}"

    # enum_name
    exp_enum = expected.get("enum_name")
    if exp_enum is not None and actual.get("enum_name") != exp_enum:
        return False, f"enum_name mismatch: expected {exp_enum}, got {actual.get('enum_name')}"

    # state_var
    exp_state_var = expected.get("state_var")
    if exp_state_var is not None and actual.get("state_var") != exp_state_var:
        return False, f"state_var mismatch: expected {exp_state_var}, got {actual.get('state_var')}"

    # states
    exp_states = set(expected.get("states", []))
    act_states = set(actual.get("states", []))
    if exp_states != act_states:
        return False, f"states mismatch:\n  expected: {sorted(exp_states)}\n  got:      {sorted(act_states)}"

    # transitions
    exp_tr = transitions_to_set(expected.get("transitions", []))
    act_tr = transitions_to_set(actual.get("transitions", []))
    if exp_tr != act_tr:
        return False, f"transitions mismatch:\n  expected: {sorted(exp_tr)}\n  got:      {sorted(act_tr)}"

    return True, "OK"


def run_test(name: str, sv_code: str, expected_graphs: List[Dict[str, Any]]):
    """
    Запустить один тест:
      - построить CST
      - собрать FSM-графы
      - сравнить с ожидаемыми (по количеству и содержимому)
    """
    print(f"\n=== TEST: {name} ===")
    cst = CSTService()
    tree = cst.build_cst_from_text(sv_code, f"{name}.sv")

    graphs = build_fsm_graphs_from_cst(tree)

    print("  Got graphs:")
    pprint(graphs)

    if len(graphs) != len(expected_graphs):
        print(f"  FAIL: expected {len(expected_graphs)} graph(s), got {len(graphs)}")
        return False

    all_ok = True
    for i, exp in enumerate(expected_graphs):
        if i >= len(graphs):
            print(f"  FAIL: missing actual graph for expected index {i}")
            all_ok = False
            continue
        ok, msg = check_graph(graphs[i], exp)
        if ok:
            print(f"  Graph {i}: PASS")
        else:
            print(f"  Graph {i}: FAIL -> {msg}")
            all_ok = False

    return all_ok


# ==============================
# ТЕСТОВЫЕ ПРИМЕРЫ FSM
# ==============================

# 1) БАЗОВЫЙ FSM С typedef enum В ПАКЕТЕ
TEST_1_SV = r"""
package defs;
  typedef enum logic [2:0] {IDLE, REQ, WAIT, GNT} state_t;
endpackage

module fsm_example(input  logic clk,
                   input  logic rst,
                   input  logic req,
                   input  logic gnt,
                   output logic gr);
  import defs::*;

  state_t state, next_state;

  always_ff @(posedge clk or posedge rst) begin
    if (rst)
      state <= IDLE;
    else
      state <= next_state;
  end

  always_comb begin
    next_state = state;
    unique case (state)
      IDLE: if (req)       next_state = REQ;
      REQ:                 next_state = WAIT;
      WAIT: if (gnt)       next_state = GNT;
      GNT:                 next_state = IDLE;
    endcase
  end

endmodule
"""

TEST_1_EXPECTED = [
    {
        "scope": "module fsm_example",
        "enum_name": "state_t",
        "state_var": "state",
        "states": ["IDLE", "REQ", "WAIT", "GNT"],
        "transitions": [
            {"from": "IDLE", "to": "REQ",  "cond": "req"},
            {"from": "REQ",  "to": "WAIT", "cond": "1"},
            {"from": "WAIT", "to": "GNT",  "cond": "gnt"},
            {"from": "GNT",  "to": "IDLE", "cond": "1"},
        ],
    }
]


# 2) INLINE enum В МОДУЛЕ: enum logic [1:0] {S0,S1,...} state, next_state;
TEST_2_SV = r"""
module inline_enum_fsm (
    input  logic clk,
    input  logic rst,
    input  logic a,
    input  logic b
);
  enum logic [1:0] {S0, S1, S2} state, next_state;

  always_ff @(posedge clk or posedge rst) begin
    if (rst)
      state <= S0;
    else
      state <= next_state;
  end

  always_comb begin
    next_state = state;
    case (state)
      S0: if (a)   next_state = S1;
      S1: if (b)   next_state = S2;
      S2:         next_state = S0;
    endcase
  end

endmodule
"""

TEST_2_EXPECTED = [
    {
        "scope": "module inline_enum_fsm",
        # анонимный enum, имя будет 'anonymous_enum_...'
        "enum_name": None,
        "state_var": "state",
        "states": ["S0", "S1", "S2"],
        "transitions": [
            {"from": "S0", "to": "S1", "cond": "a"},
            {"from": "S1", "to": "S2", "cond": "b"},
            {"from": "S2", "to": "S0", "cond": "1"},
        ],
    }
]


# 3) FSM БЕЗ NEXT_STATE: только state, переходы внутри одного always_ff
TEST_3_SV = r"""
module single_state_fsm (
    input  logic clk,
    input  logic rst,
    input  logic x
);
  typedef enum logic [1:0] {A, B, C} state_t;
  state_t state;

  always_ff @(posedge clk or posedge rst) begin
    if (rst)
      state <= A;
    else begin
      case (state)
        A: if (x)  state <= B;
        B:        state <= C;
        C:        state <= A;
      endcase
    end
  end

endmodule
"""

TEST_3_EXPECTED = [
    {
        "scope": "module single_state_fsm",
        "enum_name": "state_t",
        "state_var": "state",
        "states": ["A", "B", "C"],
        "transitions": [
            {"from": "A", "to": "B", "cond": "x"},
            {"from": "B", "to": "C", "cond": "1"},
            {"from": "C", "to": "A", "cond": "1"},
        ],
    }
]


# 4) ДВА РАЗНЫХ FSM В ОДНОМ МОДУЛЕ
TEST_4_SV = r"""
module two_fsms (
    input  logic clk,
    input  logic rst,
    input  logic start,
    input  logic done,
    input  logic err
);
  typedef enum logic [1:0] {IDLE, RUN} ctrl_t;
  typedef enum logic [1:0] {OK, FAIL} status_t;

  ctrl_t   ctrl_state, ctrl_next;
  status_t stat_state, stat_next;

  // FSM 1: ctrl
  always_ff @(posedge clk or posedge rst) begin
    if (rst)
      ctrl_state <= IDLE;
    else
      ctrl_state <= ctrl_next;
  end

  always_comb begin
    ctrl_next = ctrl_state;
    case (ctrl_state)
      IDLE: if (start) ctrl_next = RUN;
      RUN:  if (done)  ctrl_next = IDLE;
    endcase
  end

  // FSM 2: status
  always_ff @(posedge clk or posedge rst) begin
    if (rst)
      stat_state <= OK;
    else
      stat_state <= stat_next;
  end

  always_comb begin
    stat_next = stat_state;
    case (stat_state)
      OK:   if (err)  stat_next = FAIL;
      FAIL: if (!err) stat_next = OK;
    endcase
  end

endmodule
"""

TEST_4_EXPECTED = [
    {
        "scope": "module two_fsms",
        "enum_name": "ctrl_t",
        "state_var": "ctrl_state",
        "states": ["IDLE", "RUN"],
        "transitions": [
            {"from": "IDLE", "to": "RUN",  "cond": "start"},
            {"from": "RUN",  "to": "IDLE", "cond": "done"},
        ],
    },
    {
        "scope": "module two_fsms",
        "enum_name": "status_t",
        "state_var": "stat_state",
        "states": ["OK", "FAIL"],
        "transitions": [
            {"from": "OK",   "to": "FAIL", "cond": "err"},
            {"from": "FAIL", "to": "OK",   "cond": "!err"},
        ],
    },
]


# 5) Присутствует НЕ-FSM enum (типа tr_type), который НЕ должен давать граф
TEST_5_SV = r"""
package pkt_defs:
  typedef enum logic [1:0] {RD, WR} tr_type_t;
endpackage

module fsm_with_enum_and_data (
    input  logic clk,
    input  logic rst,
    input  logic req,
    input  logic gnt
);
  import pkt_defs::*;

  typedef enum logic [1:0] {S0, S1} state_t;

  state_t    state, next_state;
  tr_type_t  tr_type;  // это просто тип операции, не FSM

  always_ff @(posedge clk or posedge rst) begin
    if (rst)
      state <= S0;
    else
      state <= next_state;
  end

  always_comb begin
    next_state = state;
    case (state)
      S0: if (req) next_state = S1;
      S1: if (gnt) next_state = S0;
    endcase
  end

endmodule
"""

# Исправление двоеточия (чтобы не ломать парсер)
TEST_5_SV = TEST_5_SV.replace("package pkt_defs:", "package pkt_defs;")

TEST_5_EXPECTED = [
    {
        "scope": "module fsm_with_enum_and_data",
        "enum_name": "state_t",
        "state_var": "state",
        "states": ["S0", "S1"],
        "transitions": [
            {"from": "S0", "to": "S1", "cond": "req"},
            {"from": "S1", "to": "S0", "cond": "gnt"},
        ],
    }
]


# 6) "Боевой" протокольный FSM: IDLE/WAIT_ACK c handshaking
TEST_6_SV = r"""
module handshake_fsm (
    input  logic clk,
    input  logic rst,
    input  logic req,
    input  logic ack
);
  typedef enum logic [1:0] {IDLE, WAIT_ACK} hstate_t;

  hstate_t state, next_state;

  always_ff @(posedge clk or posedge rst) begin
    if (rst)
      state <= IDLE;
    else
      state <= next_state;
  end

  always_comb begin
    next_state = state;
    case (state)
      IDLE: if (req) next_state = WAIT_ACK;
      WAIT_ACK: if (ack) next_state = IDLE;
    endcase
  end

endmodule
"""

TEST_6_EXPECTED = [
    {
        "scope": "module handshake_fsm",
        "enum_name": "hstate_t",
        "state_var": "state",
        "states": ["IDLE", "WAIT_ACK"],
        "transitions": [
            {"from": "IDLE",     "to": "WAIT_ACK", "cond": "req"},
            {"from": "WAIT_ACK", "to": "IDLE",     "cond": "ack"},
        ],
    }
]


# 7) FSM с if / else if и веткой ошибки
TEST_7_SV = r"""
module fsm_with_error (
    input  logic clk,
    input  logic rst,
    input  logic start,
    input  logic fault,
    input  logic clear
);
  typedef enum logic [1:0] {IDLE, RUN, ERR} fsm_t;

  fsm_t state, next_state;

  always_ff @(posedge clk or posedge rst) begin
    if (rst)
      state <= IDLE;
    else
      state <= next_state;
  end

  always_comb begin
    next_state = state;
    case (state)
      IDLE: begin
        if (start)      next_state = RUN;
        else if (fault) next_state = ERR;
      end
      RUN: begin
        if (fault) next_state = ERR;
      end
      ERR: begin
        if (clear) next_state = IDLE;
      end
    endcase
  end

endmodule
"""

# Обрати внимание: наш текущий анализ условий не умеет строить (!start && fault).
# Для ветки IDLE -> ERR мы ожидаем cond="fault" (последний if перед присваиванием).
TEST_7_EXPECTED = [
    {
        "scope": "module fsm_with_error",
        "enum_name": "fsm_t",
        "state_var": "state",
        "states": ["IDLE", "RUN", "ERR"],
        "transitions": [
            {"from": "IDLE", "to": "RUN", "cond": "start"},
            {"from": "IDLE", "to": "ERR", "cond": "fault"},
            {"from": "RUN",  "to": "ERR", "cond": "fault"},
            {"from": "ERR",  "to": "IDLE", "cond": "clear"},
        ],
    }
]


# 8) priority case (state) + enum с префиксами состояний
TEST_8_SV = r"""
module priority_fsm (
    input  logic clk,
    input  logic rst,
    input  logic start,
    input  logic done
);
  typedef enum logic [1:0] {S_IDLE, S_BUSY} fsm_t;

  fsm_t state, next_state;

  always_ff @(posedge clk or posedge rst) begin
    if (rst)
      state <= S_IDLE;
    else
      state <= next_state;
  end

  always_comb begin
    next_state = state;
    priority case (state)
      S_IDLE: if (start) next_state = S_BUSY;
      S_BUSY: if (done)  next_state = S_IDLE;
    endcase
  end

endmodule
"""

TEST_8_EXPECTED = [
    {
        "scope": "module priority_fsm",
        "enum_name": "fsm_t",
        "state_var": "state",
        "states": ["S_IDLE", "S_BUSY"],
        "transitions": [
            {"from": "S_IDLE", "to": "S_BUSY", "cond": "start"},
            {"from": "S_BUSY", "to": "S_IDLE", "cond": "done"},
        ],
    }
]


# 9) INLINE ENUM + alias типа: enum {...} fsm_state; fsm_state state, next_state;
#    Это пример в духе detect_4_bit_sequence_using_fsm (по лекции).
TEST_9_SV = r"""
module detect_4_bit_sequence_using_fsm
(
  input  logic clk,
  input  logic rst,
  input  logic a,
  output logic detected
);

  // States (F — First, S — Second)
  enum logic[2:0]
  {
     IDLE = 3'b001,
     F1   = 3'b000,
     F0   = 3'b010,
     S1   = 3'b011,
     S0   = 3'b100
  }
  fsm_state;

  fsm_state next_state;
  fsm_state state;

  // State transition logic
  always_comb begin
    next_state = state;
    case (state)
      IDLE: if (  a) next_state = F1;
      F1:   if (~ a) next_state = F0;
      F0:   if (  a) next_state = S1;
            else     next_state = IDLE;
      S1:   if (~ a) next_state = S0;
            else     next_state = F1;
      S0:   if (  a) next_state = S1;
            else     next_state = IDLE;
    endcase
  end

  // Output logic (depends only on the current state)
  assign detected = (state == S0);

  // State update
  always_ff @ (posedge clk or posedge rst)
    if (rst)
      state <= IDLE;
    else
      state <= next_state;

endmodule
"""

TEST_9_EXPECTED = [
    {
        "scope": "module detect_4_bit_sequence_using_fsm",
        # enum анонимный: anonymous_enum_IDLE_1 (имя не фиксируем)
        "enum_name": None,
        "state_var": "state",
        "states": ["IDLE", "F1", "F0", "S1", "S0"],
        "transitions": [
            {"from": "IDLE", "to": "F1", "cond": "a"},
            {"from": "F1",   "to": "F0", "cond": "~a"},
            {"from": "F0",   "to": "S1", "cond": "a"},
            {"from": "F0",   "to": "IDLE", "cond": "1"},
            {"from": "S1",   "to": "S0", "cond": "~a"},
            {"from": "S1",   "to": "F1", "cond": "1"},
            {"from": "S0",   "to": "S1", "cond": "a"},
            {"from": "S0",   "to": "IDLE", "cond": "1"},
        ],
    }
]


# 10) always @* вместо always_comb + casez (редкий, но законный стиль)
TEST_10_SV = r"""
module casez_fsm (
    input  logic clk,
    input  logic rst_n,
    input  logic en
);
  typedef enum logic [1:0] {S0, S1} st_t;

  st_t state, next_state;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n)
      state <= S0;
    else
      state <= next_state;
  end

  always @* begin
    next_state = state;
    casez (state)
      S0: if (en) next_state = S1;
      S1: if (!en) next_state = S0;
    endcase
  end

endmodule
"""

TEST_10_EXPECTED = [
    {
        "scope": "module casez_fsm",
        "enum_name": "st_t",
        "state_var": "state",
        "states": ["S0", "S1"],
        "transitions": [
            {"from": "S0", "to": "S1", "cond": "en"},
            {"from": "S1", "to": "S0", "cond": "!en"},
        ],
    }
]


# 11) Раздельные декларации state и next_state (не в одной строке)
TEST_11_SV = r"""
module split_decl_fsm (
    input  logic clk,
    input  logic rst,
    input  logic a
);
  typedef enum logic [1:0] {S0, S1} st_t;

  st_t state;
  st_t next_state;

  always_ff @(posedge clk or posedge rst) begin
    if (rst)
      state <= S0;
    else
      state <= next_state;
  end

  always_comb begin
    next_state = state;
    case (state)
      S0: if (a) next_state = S1;
      S1:       next_state = S0;
    endcase
  end

endmodule
"""

TEST_11_EXPECTED = [
    {
        "scope": "module split_decl_fsm",
        "enum_name": "st_t",
        "state_var": "state",
        "states": ["S0", "S1"],
        "transitions": [
            {"from": "S0", "to": "S1", "cond": "a"},
            {"from": "S1", "to": "S0", "cond": "1"},
        ],
    }
]


# 12) Несколько модулей в одном файле:
#     - один настоящий FSM
#     - один "шумовой" модуль с enum, но без FSM-логики
TEST_12_SV = r"""
module noisy_enum_module (
    input  logic clk
);
  typedef enum logic [1:0] {X0, X1} noisy_t;
  noisy_t mode;

  // Нет ни case(mode), ни переходов вида mode <= ...
  always_ff @(posedge clk) begin
    mode <= X0;
  end
endmodule


module real_fsm (
    input  logic clk,
    input  logic rst,
    input  logic go,
    input  logic done
);
  typedef enum logic [1:0] {IDLE, BUSY} state_t;

  state_t state, next_state;

  always_ff @(posedge clk or posedge rst) begin
    if (rst)
      state <= IDLE;
    else
      state <= next_state;
  end

  always_comb begin
    next_state = state;
    case (state)
      IDLE: if (go)   next_state = BUSY;
      BUSY: if (done) next_state = IDLE;
    endcase
  end

endmodule
"""

TEST_12_EXPECTED = [
    {
        "scope": "module real_fsm",
        "enum_name": "state_t",
        "state_var": "state",
        "states": ["IDLE", "BUSY"],
        "transitions": [
            {"from": "IDLE", "to": "BUSY", "cond": "go"},
            {"from": "BUSY", "to": "IDLE", "cond": "done"},
        ],
    }
]


# ==============================
# ГЛАВНЫЙ ЗАПУСК ТЕСТОВ
# ==============================

def main():
    all_ok = True

    ok1 = run_test("basic_typedef_package_fsm", TEST_1_SV, TEST_1_EXPECTED)
    all_ok = all_ok and ok1

    ok2 = run_test("inline_enum_fsm", TEST_2_SV, TEST_2_EXPECTED)
    all_ok = all_ok and ok2

    ok3 = run_test("single_state_fsm", TEST_3_SV, TEST_3_EXPECTED)
    all_ok = all_ok and ok3

    ok4 = run_test("two_fsms_in_one_module", TEST_4_SV, TEST_4_EXPECTED)
    all_ok = all_ok and ok4

    ok5 = run_test("fsm_with_extra_enum", TEST_5_SV, TEST_5_EXPECTED)
    all_ok = all_ok and ok5

    ok6 = run_test("handshake_fsm", TEST_6_SV, TEST_6_EXPECTED)
    all_ok = all_ok and ok6

    ok7 = run_test("fsm_with_error", TEST_7_SV, TEST_7_EXPECTED)
    all_ok = all_ok and ok7

    ok8 = run_test("priority_fsm", TEST_8_SV, TEST_8_EXPECTED)
    all_ok = all_ok and ok8

    ok9 = run_test("alias_inline_enum_fsm", TEST_9_SV, TEST_9_EXPECTED)
    all_ok = all_ok and ok9

    ok10 = run_test("casez_fsm", TEST_10_SV, TEST_10_EXPECTED)
    all_ok = all_ok and ok10

    ok11 = run_test("split_decl_fsm", TEST_11_SV, TEST_11_EXPECTED)
    all_ok = all_ok and ok11

    ok12 = run_test("multi_module_with_noise", TEST_12_SV, TEST_12_EXPECTED)
    all_ok = all_ok and ok12

    print("\n==============================")
    if all_ok:
        print("ALL TESTS PASSED ✅")
    else:
        print("SOME TESTS FAILED ❌  — смотри лог выше")


if __name__ == "__main__":
    main()
