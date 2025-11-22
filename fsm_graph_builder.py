# -*- coding: utf-8 -*-
"""
fsm_graph_builder.py

Публичные функции:
    build_fsm_graphs_from_cst(tree) -> List[Dict[str, Any]]
    fsm_graph_to_dot(graph) -> str
    fsm_graphs_to_dot(graphs) -> str

Назначение:
    По Concrete Syntax Tree (pyslang.SyntaxTree + cst_service) и результатам
    detect_fsm_enum_candidates_from_cst строит граф(ы) переходов FSM.

Граф описывается так:

[
  {
    "scope": "module fsm_example",
    "state_var": "state",
    "next_state_var": "next_state",   # может быть None (одновариантный FSM)
    "enum_name": "state_t",
    "states": ["IDLE", "REQ", "WAIT", "GNT"],
    "reset_state": "IDLE" или None,
    "transitions": [
        {"from": "IDLE", "to": "REQ",  "cond": "req"},
        {"from": "REQ",  "to": "WAIT", "cond": "1"},
        ...
    ],
    "metadata": {
        "num_transitions": int,
        "num_states": int,
    }
  },
  ...
]

Допущения:
  - классический стиль FSM:
      typedef enum {...} state_t;
      state_t state, next_state;
      always_ff @(posedge clk ...) state <= next_state;
      always_comb begin
        next_state = state;
        case (state)
          ...
        endcase
      end

  - частично работает и для варианта без next_state (state <= ... внутри case).
"""

from typing import Any, Dict, List, Tuple, Optional
import re

from cst_service import (
    kind,
    children,
    collect_identifiers_inline,
    text_of,
    first_identifier_text,
)
from fsm_enum_candidates_cst import detect_fsm_enum_candidates_from_cst
from FindeENUM import detect_enum_variables_from_cst


# ============================================================
# ПУБЛИЧНАЯ ФУНКЦИЯ: построение графов FSM
# ============================================================

def build_fsm_graphs_from_cst(tree: Any) -> List[Dict[str, Any]]:
    """
    Построить графы FSM на основе CST.

    Аргументы:
        tree: pyslang.SyntaxTree (или корневой узел), как в cst_service.

    Возвращает:
        Список описаний FSM-графов (см. формат в докстринге модуля).
    """
    root = getattr(tree, "root", tree)

    # Все enum-переменные, которые в принципе похожи на FSM-состояния
    fsm_candidates = detect_fsm_enum_candidates_from_cst(tree)
    # Все enum-переменные (для доступа к enum_members)
    all_enum_vars = detect_enum_variables_from_cst(tree)

    # Индекс по (scope, var_name) -> enum_var_info
    enum_index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for ev in all_enum_vars:
        key = (ev.get("scope", ""), ev.get("var_name", ""))
        enum_index[key] = ev

    # Группируем FSM-кандидатов по (scope, enum_name)
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for cand in fsm_candidates:
        scope = cand.get("scope", "")
        enum_name = cand.get("enum_name", "")
        if not enum_name:
            continue
        key = (scope, enum_name)
        groups.setdefault(key, []).append(cand)

    # Собираем карту scope -> узел дерева, чтобы работать в рамках модуля/класса
    scope_nodes = _collect_scope_nodes(root)

    graphs: List[Dict[str, Any]] = []

    for (scope, enum_name), vars_in_group in groups.items():
        scope_node = scope_nodes.get(scope)
        if scope_node is None:
            continue

        # Берём список состояний из первого enum-переменного в этой группе
        enum_members: List[str] = []
        for v in vars_in_group:
            idx_key = (scope, v.get("var_name", ""))
            if idx_key in enum_index:
                enum_members = enum_index[idx_key].get("enum_members") or []
                break

        if not enum_members:
            continue

        # Определяем state_var и next_state_var
        state_var, next_state_var = _choose_state_and_next(scope_node, vars_in_group)
        if not state_var:
            continue

        # Находим все always-блоки внутри scope
        always_nodes = _collect_always_nodes(scope_node)

        # Находим case (state)
        case_nodes = _find_case_nodes_on_state(scope_node, state_var)

        # Собираем переходы с попыткой выдернуть условия
        transitions = _build_transitions_from_cases(
            case_nodes, state_var, next_state_var, enum_members
        )

        # Пытаемся определить reset-состояние
        reset_state = _detect_reset_state(always_nodes, state_var, enum_members)

        # Дедуп переходов
        unique_transitions = []
        seen_edges = set()
        for t in transitions:
            key = (t["from"], t["to"], t.get("cond"))
            if key not in seen_edges:
                seen_edges.add(key)
                unique_transitions.append(t)

        graph = {
            "scope": scope,
            "state_var": state_var,
            "next_state_var": next_state_var,
            "enum_name": enum_name,
            "states": enum_members,
            "reset_state": reset_state,
            "transitions": unique_transitions,
            "metadata": {
                "num_states": len(enum_members),
                "num_transitions": len(unique_transitions),
            },
        }
        graphs.append(graph)

    return graphs


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def _collect_scope_nodes(root: Any) -> Dict[str, Any]:
    """Построить карту: scope_name -> узел scope'а."""
    scope_nodes: Dict[str, Any] = {}
    scope_kinds = {
        "ModuleDeclaration": "module",
        "InterfaceDeclaration": "interface",
        "PackageDeclaration": "package",
        "ClassDeclaration": "class",
        "ProgramDeclaration": "program",
        "CheckerDeclaration": "checker",
        "ConfigDeclaration": "config",
    }

    def dfs(node: Any):
        k = kind(node)
        if k in scope_kinds:
            nm = first_identifier_text(node) or ""
            prefix = scope_kinds[k]
            scope_name = f"{prefix} {nm}".strip()
            scope_nodes[scope_name] = node
        for ch in children(node):
            dfs(ch)

    dfs(root)
    return scope_nodes


def _collect_always_nodes(scope_node: Any) -> List[Any]:
    """Собрать все always-конструкции внутри заданного scope."""
    always_nodes: List[Any] = []

    def dfs(node: Any):
        k = kind(node)
        if "Always" in k:
            always_nodes.append(node)
        for ch in children(node):
            dfs(ch)

    dfs(scope_node)
    return always_nodes


def _safe_text(node: Any) -> str:
    """Удобный хелпер: text_of или collect_identifiers_inline, без None."""
    return (text_of(node) or "") + (collect_identifiers_inline(node) or "")


def _is_clocked_always(node: Any) -> bool:
    """Грубая проверка, что always-тело тактируемое (posedge/negedge)."""
    txt = _safe_text(node)
    return ("posedge" in txt) or ("negedge" in txt)


def _is_comb_always(node: Any) -> bool:
    """Грубая проверка, что always-комбинационный."""
    txt = _safe_text(node)
    return ("always_comb" in txt) or ("@*" in txt)


def _var_written_in_always(node: Any, var_name: str) -> bool:
    """
    Эвристика:
    считаем, что переменная записывается в always, если в тексте есть
    'var_name<=' или 'var_name='.
    """
    if not var_name:
        return False
    txt = collect_identifiers_inline(node) or ""
    # Убираем пробелы для упрощения поиска
    compact = re.sub(r"\s+", "", txt)
    pat1 = f"{var_name}<="
    pat2 = f"{var_name}="
    return (pat1 in compact) or (pat2 in compact)


def _choose_state_and_next(
    scope_node: Any, vars_in_group: List[Dict[str, Any]]
) -> Tuple[Optional[str], Optional[str]]:
    """
    Выбор основной переменной состояния (state_var) и переменной next-state.

    Эвристики:
      - state_var: пишется в тактируемом always-блоке.
      - next_state_var: пишется в комбин. always-блоке.
      - если несколько кандидатов, отбор по имени.
      - если next_state_var не найден, допускаем FSM с одним регистром состояния.
    """
    always_nodes = _collect_always_nodes(scope_node)

    written_clock: Dict[str, bool] = {}
    written_comb: Dict[str, bool] = {}

    for v in vars_in_group:
        name = v.get("var_name", "")
        written_clock[name] = False
        written_comb[name] = False
        for a in always_nodes:
            if _var_written_in_always(a, name):
                if _is_clocked_always(a):
                    written_clock[name] = True
                elif _is_comb_always(a):
                    written_comb[name] = True

    # Кандидаты в state_var: пишутся в clocked always
    state_candidates = [v for v in vars_in_group if written_clock.get(v.get("var_name", ""), False)]
    # Кандидаты в next_state_var: пишутся в comb always
    next_candidates = [v for v in vars_in_group if written_comb.get(v.get("var_name", ""), False)]

    # Если ничего не нашли для state_candidates — fallback: все
    if not state_candidates:
        state_candidates = vars_in_group[:]

    def score_state_name(name: str) -> int:
        n = name.lower()
        score = 0
        if n == "state":
            score += 3
        if "state" in n:
            score += 2
        if "next" in n or "nxt" in n or n.endswith("_d") or n.endswith("_ns"):
            score -= 2
        return score

    best_state_var = None
    best_score = -999
    for v in state_candidates:
        name = v.get("var_name", "")
        sc = score_state_name(name)
        if sc > best_score:
            best_score = sc
            best_state_var = name

    state_var = best_state_var

    def score_next_name(name: str) -> int:
        n = name.lower()
        score = 0
        if "next" in n or "nxt" in n:
            score += 3
        if n.endswith("_d") or n.endswith("_ns"):
            score += 2
        if "state" in n:
            score += 1
        if state_var and name == state_var:
            score -= 3
        return score

    best_next_var = None
    best_next_score = -999
    if next_candidates:
        for v in next_candidates:
            name = v.get("var_name", "")
            sc = score_next_name(name)
            if sc > best_next_score:
                best_next_score = sc
                best_next_var = name

    next_state_var = best_next_var if best_next_score > -999 else None

    return state_var, next_state_var


def _find_case_nodes_on_state(scope_node: Any, state_var: str) -> List[Any]:
    """Найти все case-конструкции вида case(state_var) / unique case (state_var)."""
    result: List[Any] = []

    def is_case_on_state(node: Any) -> bool:
        k = kind(node)
        if not k.startswith("Case"):
            return False
        full = collect_identifiers_inline(node) or ""
        # Убираем пробелы, чтобы понимать case( state ) / case (state)
        compact = re.sub(r"\s+", "", full)
        if f"case({state_var})" in compact:
            return True
        # Также для uniquecase, prioritycase и т.п.
        if f"uniquecase({state_var})" in compact or f"prioritycase({state_var})" in compact:
            return True
        return False

    def dfs(node: Any):
        k = kind(node)
        if k.startswith("Case") and is_case_on_state(node):
            result.append(node)
        for ch in children(node):
            dfs(ch)

    dfs(scope_node)
    return result


def _build_transitions_from_cases(
    case_nodes: List[Any],
    state_var: str,
    next_state_var: Optional[str],
    enum_members: List[str],
) -> List[Dict[str, Any]]:
    """
    Построить список переходов из case-блоков.

    Эвристики:
      - from_state: первый enum-элемент в заголовке CaseItem.
      - to_state: все enum-элементы, которые присваиваются lhs (next_state или state)
                  в этом CaseItem.
      - cond: если присваивание внутри 'if (COND) lhs = STATE;'
              -> cond = текст внутри скобок.
              Если if не найден -> cond = "1" (безусловный переход).
    """
    transitions: List[Dict[str, Any]] = []

    lhs_name = next_state_var if next_state_var else state_var

    if not lhs_name:
        return transitions

    for case_node in case_nodes:
        # Ищем CaseItem-подузлы (названия kind могут варьироваться, поэтому ищем по подстроке)
        case_items: List[Any] = []

        def dfs_items(node: Any):
            k = kind(node)
            if "CaseItem" in k:
                case_items.append(node)
            else:
                for ch in children(node):
                    dfs_items(ch)

        dfs_items(case_node)

        for item in case_items:
            item_text = collect_identifiers_inline(item) or ""
            if not item_text:
                continue

            from_state = _find_first_enum_in_text(enum_members, item_text)
            if not from_state:
                # default: можно обработать отдельно, пока пропускаем
                continue

            # Ищем все присваивания lhs_name = ENUM_MEMBER в этом CaseItem
            assigns = _find_assignments_with_conditions(item_text, lhs_name, enum_members)

            for to_state, cond in assigns:
                transitions.append(
                    {
                        "from": from_state,
                        "to": to_state,
                        "cond": cond,
                    }
                )

    return transitions


def _find_first_enum_in_text(enum_members: List[str], text: str) -> Optional[str]:
    """Найти первое (по позиции) упоминание enum-элемента в строке."""
    best_idx = None
    best_member = None
    for m in enum_members:
        idx = text.find(m)
        if idx != -1 and (best_idx is None or idx < best_idx):
            best_idx = idx
            best_member = m
    return best_member


def _find_assignments_with_conditions(
    text: str, lhs_name: str, enum_members: List[str]
) -> List[Tuple[str, str]]:
    """
    Найти все пары (ENUM_MEMBER, cond), для которых в тексте есть присваивания:
       lhs_name = ENUM_MEMBER;
       lhs_name <= ENUM_MEMBER;
    cond:
       - если перед присваиванием есть if (COND) ... -> cond = "COND"
       - иначе cond = "1" (безусловный переход)
    """
    result: List[Tuple[str, str]] = []

    # Ищем все if (...) и все присваивания в этом куске текста
    if_pattern = re.compile(r"if\s*\((.*?)\)")
    assign_pattern = re.compile(
        rf"{re.escape(lhs_name)}\s*<?=\s*([A-Za-z_]\w*)"
    )

    if_matches = list(if_pattern.finditer(text))
    assign_matches = list(assign_pattern.finditer(text))

    for am in assign_matches:
        assigned_name = am.group(1)
        if assigned_name not in enum_members:
            continue

        # Ищем ближайший if(...) перед этим присваиванием
        cond = "1"  # по умолчанию — безусловно
        assign_start = am.start()
        prev_ifs = [m for m in if_matches if m.start() < assign_start]
        if prev_ifs:
            last_if = prev_ifs[-1]
            cond = last_if.group(1).strip()

        result.append((assigned_name, cond))

    # Дедуп
    uniq: List[Tuple[str, str]] = []
    seen = set()
    for r in result:
        if r not in seen:
            seen.add(r)
            uniq.append(r)
    return uniq


def _detect_reset_state(
    always_nodes: List[Any],
    state_var: str,
    enum_members: List[str],
) -> Optional[str]:
    """
    Попытаться определить reset-состояние:
      - смотрим тактируемые always-блоки,
      - ищем присваивания state_var <= ENUM_VALUE (обычно в ветке reset).
    """
    for a in always_nodes:
        if not _is_clocked_always(a):
            continue
        txt = collect_identifiers_inline(a) or ""
        if state_var not in txt:
            continue
        compact = re.sub(r"\s+", "", txt)
        for m in enum_members:
            pat1 = f"{state_var}={m}"
            pat2 = f"{state_var}<={m}"
            if pat1 in compact or pat2 in compact:
                return m
    return None


# ============================================================
# DOT / GraphViz экспорт
# ============================================================

def fsm_graph_to_dot(graph: Dict[str, Any]) -> str:
    """
    Преобразовать один FSM-граф в строку формата DOT (GraphViz).

    Пример:
        dot = fsm_graph_to_dot(graph)
        # дальше можно сохранить в .dot и через dot -Tpng визуализировать
    """
    scope = graph.get("scope", "fsm")
    state_var = graph.get("state_var", "state")
    name = f"{scope}_{state_var}".replace(" ", "_")

    lines: List[str] = []
    lines.append(f'digraph "{name}" {{')

    # Ноды
    reset_state = graph.get("reset_state")
    for s in graph.get("states", []):
        if reset_state and s == reset_state:
            lines.append(f'  {s} [shape=doublecircle];')
        else:
            lines.append(f'  {s} [shape=circle];')

    # Рёбра
    for t in graph.get("transitions", []):
        frm = t.get("from")
        to = t.get("to")
        cond = t.get("cond")
        if cond and cond != "1":
            lines.append(f'  {frm} -> {to} [label="{cond}"];')
        else:
            lines.append(f'  {frm} -> {to};')

    lines.append("}")
    return "\n".join(lines)


def fsm_graphs_to_dot(graphs: List[Dict[str, Any]]) -> str:
    """
    Объединить несколько FSM-графов в один DOT (с подграфами-кластерами по scope).
    """
    lines: List[str] = []
    lines.append("digraph FSMs {")
    lines.append('  compound=true;')

    for i, g in enumerate(graphs):
        scope = g.get("scope", f"fsm_{i}")
        state_var = g.get("state_var", "state")
        cluster_name = f"cluster_{i}"
        label = f"{scope} ({state_var})"

        lines.append(f'  subgraph {cluster_name} {{')
        lines.append(f'    label="{label}";')

        reset_state = g.get("reset_state")
        for s in g.get("states", []):
            if reset_state and s == reset_state:
                lines.append(f'    {s} [shape=doublecircle];')
            else:
                lines.append(f'    {s} [shape=circle];')

        for t in g.get("transitions", []):
            frm = t.get("from")
            to = t.get("to")
            cond = t.get("cond")
            if cond and cond != "1":
                lines.append(f'    {frm} -> {to} [label="{cond}"];')
            else:
                lines.append(f'    {frm} -> {to};')

        lines.append("  }")

    lines.append("}")
    return "\n".join(lines)


# ============================================================
# Пример использования
# ============================================================

if __name__ == "__main__":
    from cst_service import CSTService
    from pprint import pprint

    example_code = r"""
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

      // Регистры состояния
      always_ff @(posedge clk or posedge rst) begin
        if (rst)
          state <= IDLE;
        else
          state <= next_state;
      end

      // Логика переходов
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

    cst = CSTService()
    tree = cst.build_cst_from_text(example_code, "fsm_example.sv")

    graphs = build_fsm_graphs_from_cst(tree)
    print("=== FSM GRAPHS ===")
    pprint(graphs)

    if graphs:
        print("\n=== DOT FOR FIRST GRAPH ===")
        print(fsm_graph_to_dot(graphs[0]))
