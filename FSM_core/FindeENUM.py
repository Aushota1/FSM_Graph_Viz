# -*- coding: utf-8 -*-
"""
enum_detector_cst.py

Единственная публичная функция:
    detect_enum_variables_from_cst(tree) -> List[Dict[str, Any]]

Назначение:
    По Concrete Syntax Tree (pyslang.SyntaxTree + cst_service) находит
    все переменные enum-типа и возвращает список описаний:
        - имя переменной,
        - имя enum-типа (typedef-имя либо сгенерированное для анонимного enum),
        - список членов enum,
        - scope (module / class / package / ...),
        - позиция в файле (если pyslang её даёт).

Формат результата:
    [
        {
            "var_name": "State",
            "enum_name": "state_t",              # или anonymous_enum_X_1 для анонимного
            "enum_members": ["IDLE", "RUN", ...],
            "scope": "module TicketVendorBotOneHot",
            "position": {
                "line": ...,
                "column": ...,
                "start": ...,
                "end": ...
            }
        },
        ...
    ]
"""

from typing import Any, Dict, List
from AST_CST.cst_service import (
    kind,
    children,
    find_all,
    first_identifier_text,
    collect_identifiers_inline,
    text_of,
)


def detect_enum_variables_from_cst(tree: Any) -> List[Dict[str, Any]]:
    """Найти все переменные enum-типа в CST (на базе cst_service / pyslang.SyntaxTree)."""

    # На всякий случай поддержим и tree.root, и сразу корневой узел
    root = getattr(tree, "root", tree)

    # ---------------- ВСПОМОГАТЕЛЬНЫЕ ВНУТРЕННИЕ ФУНКЦИИ ---------------- #

    def get_position(node: Any) -> Dict[str, Any]:
        """Позиция узла в исходнике (совместимо с CSTService._get_node_position)."""
        return {
            "line": getattr(node, "line", None),
            "column": getattr(node, "column", None),
            "start": getattr(node, "start", None),
            "end": getattr(node, "end", None),
        }

    def find_enum_members(enum_node: Any) -> List[str]:
        """Собрать имена элементов enum'а."""
        members: List[str] = []

        # Нормальный случай: есть узлы Enumerator
        enumerator_nodes = find_all(enum_node, "Enumerator")
        if enumerator_nodes:
            for en in enumerator_nodes:
                nm = first_identifier_text(en) or text_of(en)
                if nm:
                    members.append(nm)
            return members

        # Запасной вариант: вытащить список из текста внутри { ... }
        brace_text = text_of(enum_node) or collect_identifiers_inline(enum_node)
        if "{" in brace_text and "}" in brace_text:
            inner = brace_text.split("{", 1)[1].rsplit("}", 1)[0]
            parts = [p.strip() for p in inner.replace("\n", " ").split(",")]
            for p in parts:
                if not p:
                    continue
                # Поддержка вида NAME = CONST: берём только NAME
                name_part = p.split("=", 1)[0].strip()
                if name_part:
                    members.append(name_part)
        return members

    def build_enum_index(root_node: Any):
        """
        Строим индекс enum-типов:

          - enum_info_by_id: id(enum_node) -> {
                "enum_node": node,
                "enum_name": str,       # typedef-имя или сгенерированное
                "enum_members": [str],
            }

          - typedef_to_enum: имя typedef enum / inline-алиаса -> enum_id

        Имя typedef ищем через родителя EnumType, чтобы обработать:
            typedef enum logic [..] {A,B} state_t;

        ДОПОЛНИТЕЛЬНО (НЕ ЛОМАЯ СТАРОЕ ПОВЕДЕНИЕ):
            enum logic[2:0] {IDLE,F1,F0,S1,S0} fsm_state;
            fsm_state next_state;
            fsm_state state;
        Здесь `fsm_state` добавляется в typedef_to_enum, но enum_name остаётся
        анонимным (как и раньше, чтобы тесты не сломались).
        """
        enum_nodes_with_parents: List[Dict[str, Any]] = []

        # DFS с явным стеком, чтобы знать родителя
        stack: List[Any] = []

        def dfs_collect(n: Any):
            stack.append(n)
            k = kind(n)
            if k == "EnumType":
                parent = stack[-2] if len(stack) >= 2 else None
                enum_nodes_with_parents.append({"enum_node": n, "parent": parent})
            for ch in children(n):
                dfs_collect(ch)
            stack.pop()

        dfs_collect(root_node)

        enum_info_by_id: Dict[int, Dict[str, Any]] = {}
        typedef_to_enum: Dict[str, int] = {}

        for item in enum_nodes_with_parents:
            en = item["enum_node"]
            parent = item["parent"]

            members = find_enum_members(en)
            enum_id = id(en)

            # По умолчанию считаем enum анонимным, потом пробуем найти typedef-имя
            enum_name = ""

            if parent is not None:
                parent_text = collect_identifiers_inline(parent)

                # --- 1) Классический случай: typedef enum {...} state_t; ---
                if "typedef" in parent_text and "enum" in parent_text:
                    parent_ids = find_all(parent, "Identifier")
                    enum_ids = {id(x) for x in find_all(en, "Identifier")}

                    keyword_like = {
                        "enum",
                        "logic",
                        "reg",
                        "wire",
                        "bit",
                        "byte",
                        "shortint",
                        "int",
                        "longint",
                        "signed",
                        "unsigned",
                        "integer",
                        "time",
                        "real",
                        "realtime",
                    }

                    typedef_name = ""
                    for id_node in parent_ids:
                        # Пропускаем идентификаторы, которые относятся к самому enum-типу
                        if id(id_node) in enum_ids:
                            continue
                        nm = text_of(id_node)
                        if not nm:
                            continue
                        if nm in keyword_like or nm in members:
                            continue
                        typedef_name = nm
                        break

                    if typedef_name:
                        enum_name = typedef_name
                        typedef_to_enum[typedef_name] = enum_id

                # --- 2) Inline enum без typedef: enum {...} fsm_state; ---
                # Старое поведение: enum_name остаётся пустым, затем анонимным.
                # Новое поведение: И ДОБАВЛЯЕМ имена-после-enum в typedef_to_enum,
                # чтобы их можно было использовать как тип (fsm_state state;).
                if "enum" in parent_text and "typedef" not in parent_text:
                    parent_ids = find_all(parent, "Identifier")
                    enum_ids = {id(x) for x in find_all(en, "Identifier")}

                    keyword_like = {
                        "enum",
                        "logic",
                        "reg",
                        "wire",
                        "bit",
                        "byte",
                        "shortint",
                        "int",
                        "longint",
                        "signed",
                        "unsigned",
                        "integer",
                        "time",
                        "real",
                        "realtime",
                    }

                    inline_aliases: List[str] = []
                    for id_node in parent_ids:
                        if id(id_node) in enum_ids:
                            continue
                        nm = text_of(id_node)
                        if not nm:
                            continue
                        if nm in keyword_like or nm in members:
                            continue
                        inline_aliases.append(nm)

                    # ВАЖНО: enum_name НЕ трогаем, чтобы старые тесты не изменились.
                    # Только заполняем typedef_to_enum для последующих деклараций.
                    for alias in inline_aliases:
                        typedef_to_enum[alias] = enum_id

            enum_info_by_id[enum_id] = {
                "enum_node": en,
                "enum_name": enum_name,  # может остаться пустым до генерации анонимного имени
                "enum_members": members,
            }

        # Для анонимных enum'ов генерируем стабильные имена
        anon_counter = 0
        for enum_id, info in enum_info_by_id.items():
            if not info["enum_name"]:
                anon_counter += 1
                members = info["enum_members"] or []
                suffix = members[0] if members else str(anon_counter)
                info["enum_name"] = f"anonymous_enum_{suffix}_{anon_counter}"

        return enum_info_by_id, typedef_to_enum

    def detect_enum_for_declaration(
        decl_node: Any,
        enum_info_by_id: Dict[int, Dict[str, Any]],
        typedef_to_enum: Dict[str, int],
    ) -> Dict[str, Any]:
        """
        Понять, есть ли в декларации enum-тип.
        Возвращает:
          {"enum_id": int|None, "enum_name": str, "enum_members": List[str]}
        """
        full_text = collect_identifiers_inline(decl_node)

        # НОВЫЙ ПОРЯДОК:
        # 1) Сначала обрабатываем декларации, где явно есть "enum"
        #    (чтобы не сломать старое поведение inline enum).
        if "enum" in full_text:
            # Прямой inline enum в декларации:
            #   enum logic [1:0] {A,B} var;
            local_enums = find_all(decl_node, "EnumType")
            if local_enums:
                en = local_enums[0]
                enum_id = id(en)
                info = enum_info_by_id.get(enum_id)
                if info:
                    return {
                        "enum_id": enum_id,
                        "enum_name": info["enum_name"],
                        "enum_members": info["enum_members"],
                    }
                # fallback: на всякий случай, если чего-то не занесли в индекс
                members = find_enum_members(en)
                return {
                    "enum_id": enum_id,
                    "enum_name": "",
                    "enum_members": members,
                }

            # Если "enum" есть, но EnumType не нашли — считаем, что это не наш случай
            return {"enum_id": None, "enum_name": "", "enum_members": []}

        # 2) Декларации без "enum": это как раз typedef-имена и inline-алиасы:
        #       state_t cur_state;
        #       fsm_state next_state;
        for td_name, enum_id in typedef_to_enum.items():
            if td_name and td_name in full_text:
                info = enum_info_by_id[enum_id]
                return {
                    "enum_id": enum_id,
                    "enum_name": info["enum_name"],
                    "enum_members": info["enum_members"],
                }

        return {"enum_id": None, "enum_name": "", "enum_members": []}

    def extract_var_names_from_declaration(
        decl_node: Any,
        enum_name: str,
        enum_members: List[str],
    ) -> List[str]:
        """
        Собрать имена переменных в декларации:
          enum_name var1, var2;
          typedef_enum_name var3;
          enum {...} var4;
          output enum {...} port;

        Поведение для существующих тестов не меняем.
        Дополнительно появятся переменные из строк вида:
            fsm_state state;
            fsm_state next_state;
        если fsm_state был алиасом inline enum.
        """
        id_nodes = find_all(decl_node, "Identifier")
        all_ids: List[str] = []
        for idn in id_nodes:
            t = text_of(idn)
            if t:
                all_ids.append(t)

        # Типовые ключевые слова/типы, которые точно не являются именами переменных
        keyword_like = {
            "typedef",
            "enum",
            "logic",
            "reg",
            "wire",
            "bit",
            "byte",
            "shortint",
            "int",
            "longint",
            "signed",
            "unsigned",
            "integer",
            "time",
            "real",
            "realtime",
        }

        # Пропускаем также само имя enum-типа и имена его элементов
        to_skip = set(enum_members) | keyword_like
        if enum_name:
            to_skip.add(enum_name)

        var_names: List[str] = []
        for name in all_ids:
            if name in to_skip:
                continue
            var_names.append(name)

        # Дедуп с сохранением порядка
        seen = set()
        uniq_vars: List[str] = []
        for v in var_names:
            if v not in seen:
                seen.add(v)
                uniq_vars.append(v)
        return uniq_vars

    # --------------------- ОСНОВНАЯ ЛОГИКА ФУНКЦИИ --------------------- #

    enum_info_by_id, typedef_to_enum = build_enum_index(root)

    results: List[Dict[str, Any]] = []
    if not enum_info_by_id:
        return results

    scope_stack: List[str] = []
    # Какие узлы считаем scope-ами
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

        # Новый scope (module / class / package / ...)
        if k in scope_kinds:
            nm = first_identifier_text(node) or ""
            prefix = scope_kinds[k]
            scope_stack.append(f"{prefix} {nm}".strip())
            for ch in children(node):
                dfs(ch)
            scope_stack.pop()
            return

        # Любой *Declaration считаем кандидатом на декларацию переменных
        if k.endswith("Declaration"):
            enum_info = detect_enum_for_declaration(node, enum_info_by_id, typedef_to_enum)
            if enum_info["enum_id"] is not None:
                enum_name = enum_info["enum_name"]
                enum_members = enum_info["enum_members"]
                var_names = extract_var_names_from_declaration(node, enum_name, enum_members)
                if var_names:
                    scope_str = scope_stack[-1] if scope_stack else ""
                    pos = get_position(node)
                    for vn in var_names:
                        results.append(
                            {
                                "var_name": vn,
                                "enum_name": enum_name,
                                "enum_members": enum_members,
                                "scope": scope_str,
                                "position": pos,
                            }
                        )

        for ch in children(node):
            dfs(ch)

    dfs(root)

    # Глобальная дедупликация результатов:
    # иногда одна и та же декларация может обрабатываться через несколько *Declaration-узлов.
    unique: Dict[tuple, Dict[str, Any]] = {}
    for r in results:
        pos = r.get("position", {}) or {}
        key = (
            r.get("var_name"),
            r.get("enum_name"),
            r.get("scope"),
            pos.get("line"),
            pos.get("column"),
        )
        if key not in unique:
            unique[key] = r

    return list(unique.values())


if __name__ == "__main__":
    # Небольшая самопроверка на простом примере
    from cst_service import CSTService
    from pprint import pprint

    example_code = r"""
    package bus_defs;
      typedef enum logic [1:0] {IDLE, BUSY, ERROR} bus_state_t;
    endpackage

    module bus_ctrl(input logic clk);
      import bus_defs::*;

      bus_state_t bus_state;

      enum logic [1:0] {REQ, GNT} arb_state;
    endmodule

    class Transaction;
      typedef enum {READ, WRITE} tr_type_t;
      tr_type_t tr_type;
    endclass

    // Пример inline enum + использование имени как типа
    module detect_4_bit_sequence_using_fsm
    (
      input  clk,
      input  rst,
      input  a,
      output detected
    );
      enum logic[2:0]
      {
         IDLE   = 3'b001,
         F1     = 3'b000,
         F0     = 3'b010,
         S1     = 3'b011,
         S0     = 3'b100
      }
      fsm_state;

      fsm_state next_state;
      fsm_state state;
    endmodule
    """

    cst = CSTService()
    tree = cst.build_cst_from_text(example_code, "example.sv")

    res = detect_enum_variables_from_cst(tree)
    print("=== ENUM VARIABLES DETECTED ===")
    pprint(res)
