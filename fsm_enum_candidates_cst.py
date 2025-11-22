# -*- coding: utf-8 -*-
"""
fsm_enum_candidates_cst.py

Единственная публичная функция:
    detect_fsm_enum_candidates_from_cst(tree) -> List[Dict[str, Any]]

Назначение:
    Использует enum_detector_cst.detect_enum_variables_from_cst(tree),
    а затем выбирает из всех enum-переменных только те, которые
    с высокой вероятностью участвуют в FSM (состояния автоматов).

Критерии (эвристически):
  1) var_name содержит 'state' (без учета регистра), ИЛИ
     enum_name содержит 'state' (state_t, fsm_state_t, bus_state_t и т.п.).
  2) ИЛИ переменная:
       - встречается в case/unique case/priority case,
       - и/или в always-блоках с posedge/negedge.

Возвращает:
    Список таких же словарей, как detect_enum_variables_from_cst, но только для FSM-похожих переменных.
    Дополнительно добавляется поле 'fsm_reason' с объяснением, почему переменная признана кандидатом FSM.
"""

from typing import Any, Dict, List

from cst_service import (
    kind,
    children,
    find_all,
    collect_identifiers_inline,
    text_of,
)
from FindeENUM import detect_enum_variables_from_cst


def detect_fsm_enum_candidates_from_cst(tree: Any) -> List[Dict[str, Any]]:
    """
    Найти среди всех enum-переменных только те, которые похожи на FSM-состояния.

    Аргументы:
        tree: pyslang.SyntaxTree (или root-узел), совместимый с cst_service.

    Возвращает:
        Список dict, как у detect_enum_variables_from_cst, плюс поле 'fsm_reason':
        {
            "var_name": ...,
            "enum_name": ...,
            "enum_members": [...],
            "scope": ...,
            "position": {...},
            "fsm_reason": {
                "name_based": bool,
                "used_in_case": bool,
                "assigned_in_clocked_always": bool,
            }
        }
    """

    root = getattr(tree, "root", tree)

    # Все enum-переменные, которые уже умеет находить твой детектор
    enum_vars = detect_enum_variables_from_cst(tree)

    # ---------------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---------------- #

    def var_name_contains_state(var_name: str) -> bool:
        return "state" in (var_name or "").lower()

    def enum_name_contains_state(enum_name: str) -> bool:
        return "state" in (enum_name or "").lower()

    def is_used_in_case(root_node: Any, var_name: str) -> bool:
        """
        Грубая, но рабочая проверка:
          - ищем все узлы, где kind начинается с "Case" (CaseStatement, Case, UniqueCaseStatement и т.п.),
          - смотрим, встречается ли имя переменной в тексте этого узла.
        """
        if not var_name:
            return False

        # Ищем все узлы, у которых kind() начинается на "Case"
        # (чтобы захватить CaseStatement, CaseStatement, UniqueCaseStatement и др.)
        def dfs_case(n: Any, out: List[Any]):
            k = kind(n)
            if k.startswith("Case"):
                out.append(n)
            for ch in children(n):
                dfs_case(ch, out)

        case_nodes: List[Any] = []
        dfs_case(root_node, case_nodes)

        for node in case_nodes:
            txt = collect_identifiers_inline(node)
            if var_name in txt:
                return True
        return False

    def is_assigned_in_clocked_always(root_node: Any, var_name: str) -> bool:
        """
        Проверяем, фигурирует ли переменная в always-блоках с posedge/negedge.
        Уровень грубый: по тексту узла.
        """
        if not var_name:
            return False

        # Возможные названия kind для always-конструкций в pyslang:
        #   - AlwaysConstruct
        #   - AlwaysStatement
        #   - AlwaysKeyword уже не узел, а токен, поэтому его не берём.
        always_nodes = find_all(root_node, "AlwaysConstruct") + find_all(root_node, "AlwaysStatement")

        for node in always_nodes:
            txt = collect_identifiers_inline(node)
            # Должны одновременно встретиться имя переменной и posedge/negedge
            if var_name in txt and ("posedge" in txt or "negedge" in txt):
                return True
        return False

    # ---------------- ФИЛЬТРАЦИЯ КАНДИДАТОВ FSM ---------------- #

    fsm_candidates: List[Dict[str, Any]] = []

    for item in enum_vars:
        var_name = item.get("var_name", "")
        enum_name = item.get("enum_name", "")

        # 1) Эвристика по имени
        name_based = var_name_contains_state(var_name) or enum_name_contains_state(enum_name)

        # 2) Использование в case
        used_in_case = is_used_in_case(root, var_name)

        # 3) Использование в тактируемых always-блоках
        assigned_in_clocked_always = is_assigned_in_clocked_always(root, var_name)

        # Правило отбора:
        #   - либо по имени (state/...),
        #   - либо (case + always) дают сильный сигнал FSM.
        if name_based or used_in_case or assigned_in_clocked_always:
            enriched = dict(item)
            enriched["fsm_reason"] = {
                "name_based": bool(name_based),
                "used_in_case": bool(used_in_case),
                "assigned_in_clocked_always": bool(assigned_in_clocked_always),
            }
            fsm_candidates.append(enriched)

    return fsm_candidates


if __name__ == "__main__":
    # Пример использования на простом FSM
    from cst_service import CSTService
    from pprint import pprint

    example_code = r"""
//----------------------------------------------------------------------------
// Example
//----------------------------------------------------------------------------

module detect_4_bit_sequence_using_fsm
(
  input  clk,
  input  rst,
  input  a,
  output detected
);

  // Detection of the "1010" sequence

  // States (F — First, S — Second)
  enum logic[2:0]
  {
     IDLE   = 3'b001,
     F1 = 3'b000,
     F0   = 3'b010,
     S1   = 3'b011,
     S0   = 3'b100
  }
  fsm_state;

  fsm_state next_state;
  fsm_state state;

  // State transition logic
  always_comb
  begin
    next_state = state;

    // This lint warning is bogus because we assign the default value above
    // verilator lint_off CASEINCOMPLETE

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

    // verilator lint_on CASEINCOMPLETE

  end

  // Output logic (depends only on the current state)
  assign detected = (state == S0);

  // State update
  always_ff @ (posedge clk)
    if (rst)
      state <= IDLE;
    else
      state <= next_state;

endmodule

//----------------------------------------------------------------------------
// Task
//----------------------------------------------------------------------------

module detect_6_bit_sequence_using_fsm
(
  input  clk,
  input  rst,
  input  a,
  output detected
);

  // Task:
  // Implement a module that detects the "110011" input sequence
  //
  // Hint: See Lecture 3 for details


endmodule

    """

    cst = CSTService()
    tree = cst.build_cst_from_text(example_code, "fsm_example.sv")

    all_enums = detect_enum_variables_from_cst(tree)
    print("=== ALL ENUM VARIABLES ===")
    pprint(all_enums)

    fsm_enums = detect_fsm_enum_candidates_from_cst(tree)
    print("\n=== FSM CANDIDATE ENUM VARIABLES ===")
    pprint(fsm_enums)
