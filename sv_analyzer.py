# -*- coding: utf-8 -*-
# sv_analyzer.py
"""
Утилита для анализа SystemVerilog-кода.

Использует:
  - CSTService (cst_service.py)                      — построение Concrete Syntax Tree (CST)
  - ASTService (ast_service.py)                      — базовый Unified AST
  - CompleteASTService (complete_ast_service_pyslang.py)
        — расширенный AST с pyslang + нормализация под FSMDetectorService

CLI-примеры:

  # Полный расширенный отчёт по файлу
  python sv_analyzer.py path/to/file.sv

  # Только базовый AST (без pyslang-расширений)
  python sv_analyzer.py path/to/file.sv --basic

  # Сохранить AST в JSON
  python sv_analyzer.py path/to/file.sv --dump-ast out/ast.json

  # Сохранить FSM-пэйлоад для конкретного модуля
  python sv_analyzer.py path/to/file.sv --dump-fsm out/fsm_module.json --module MyModule
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, List

from cst_service import CSTService
from ast_service import ASTService, print_unified_ast
from test_free import (
    CompleteASTService,
    print_complete_ast,
)


# =====================================================================
# Базовые функции анализа
# =====================================================================

def analyze_systemverilog_code(
    source_text: str,
    filename: str = "source.sv",
    use_complete_ast: bool = True,
) -> Dict[str, Any]:
    """
    Построить AST по коду SystemVerilog.

    Параметры:
        source_text: текст SystemVerilog.
        filename: логическое имя файла (будет видно в pyslang).
        use_complete_ast:
            - True  — использовать CompleteASTService (расширенный AST + нормализация).
            - False — использовать только базовый ASTService.

    Возвращает:
        AST как словарь (dict).
    """
    # 1. CST
    cst_service = CSTService()
    tree = cst_service.build_cst_from_text(source_text, filename)

    # 2. Базовый AST
    ast_service = ASTService()
    base_ast = ast_service.build_ast_from_cst(tree)

    if not use_complete_ast:
        # Можно сразу вернуть базовый AST
        return base_ast

    # 3. Полный AST с pyslang-расширениями и нормализацией
    complete_service = CompleteASTService()
    complete_ast = complete_service.build_complete_ast_from_cst(tree)
    return complete_ast


def analyze_file(
    path: str | Path,
    use_complete_ast: bool = True,
) -> Dict[str, Any]:
    """
    Анализ одного файла SystemVerilog по пути.

    Параметры:
        path: путь к .sv / .svh / .v файлу.
        use_complete_ast: см. analyze_systemverilog_code.

    Возвращает:
        AST как dict.
    """
    path = Path(path)
    source_text = path.read_text(encoding="utf-8")
    return analyze_systemverilog_code(
        source_text=source_text,
        filename=path.name,
        use_complete_ast=use_complete_ast,
    )


def save_json(data: Dict[str, Any], out_path: str | Path, pretty: bool = True) -> None:
    """
    Сохранить dict в JSON-файл.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        if pretty:
            json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def export_fsm_detector_payload(
    ast: Dict[str, Any],
    out_path: str | Path,
    module_name: Optional[str] = None,
    pretty: bool = True,
) -> Dict[str, Any]:
    """
    Сохранить модуль в формате, пригодном для FSMDetectorService.

    Внутри использует CompleteASTService.save_fsm_detector_input.
    Если ast ещё не нормализован — метод сам его доведёт до нужного вида.

    Параметры:
        ast: полный AST (лучше результат analyze_* при use_complete_ast=True).
        out_path: путь для сохранения JSON.
        module_name: имя модуля (если None — берётся первый модуль).
        pretty: человеко-читаемый формат JSON.

    Возвращает:
        payload, который был записан в файл (dict, содержит ключ "module").
    """
    service = CompleteASTService()
    return service.save_fsm_detector_input(
        ast=ast,
        filepath=str(out_path),
        module_name=module_name,
        pretty=pretty,
    )


# =====================================================================
# Красивый отчёт по AST
# =====================================================================

def _print_section(title: str, char: str = "=", pad: int = 80) -> None:
    print("\n" + char * pad)
    print(title)
    print(char * pad)


def _format_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def print_ast_report(
    ast: Dict[str, Any],
    *,
    filename: Optional[str] = None,
    use_complete_ast: bool = True,
    verbose_internal: bool = False,
) -> None:
    """
    Печать "человеческого" отчёта по AST.

    Если use_complete_ast=True и в AST есть enhanced_analysis,
    дополнительно выводятся:
        - статистика по типам
        - информация по модулям
        - краткий FSM-обзор
        - тайминговый анализ
    """
    modules: List[Dict[str, Any]] = ast.get("modules", []) or []
    typedefs = ast.get("typedefs", []) or []
    structs = ast.get("structs", []) or []
    enums = ast.get("enums", []) or []
    unions = ast.get("unions", []) or []
    metadata = ast.get("metadata", {}) or {}
    enhanced = ast.get("enhanced_analysis", {}) if use_complete_ast else {}

    # -----------------------------------------------------------------
    # Заголовок
    # -----------------------------------------------------------------
    _print_section("SYSTEMVERILOG ANALYSIS REPORT")

    if filename:
        print(f"Файл:        {filename}")
    print(f"AST тип:     {ast.get('type', 'Unknown')}")
    print(f"Парсер:      {ast.get('parser_used', 'unknown')}")
    print(f"Версия AST:  {ast.get('version', 'n/a')}")

    print()
    print(f"Модулей:     {len(modules)}")
    print(f"Typedef'ов:  {len(typedefs)}")
    print(f"Struct'ов:   {len(structs)}")
    print(f"Enum'ов:     {len(enums)}")
    print(f"Union'ов:    {len(unions)}")

    if metadata:
        print("\nМетаинформация:")
        for k, v in metadata.items():
            print(f"  - {k}: {v}")

    # -----------------------------------------------------------------
    # Обзор по модулям
    # -----------------------------------------------------------------
    if modules:
        _print_section("ОБЗОР ПО МОДУЛЯМ", "-")
        for m in modules:
            name = m.get("name", "?")
            ports = m.get("ports", []) or []
            signals = m.get("signals", []) or []
            always_blocks = m.get("always_blocks", []) or []
            assigns = m.get("assigns", []) or []
            instances = m.get("instances", []) or []

            print(f"\nМодуль: {name}")
            print(f"  Портов:           {len(ports)}")
            print(f"  Сигналов:         {len(signals)}")
            print(f"  always-блоков:    {len(always_blocks)}")
            print(f"  assign'ов:        {len(assigns)}")
            print(f"  инстансов модулей:{len(instances)}")

            # Сводка по портам
            if ports:
                in_cnt = sum(1 for p in ports if str(p.get("direction", "")).lower().startswith("input"))
                out_cnt = sum(1 for p in ports if str(p.get("direction", "")).lower().startswith("output"))
                inout_cnt = sum(1 for p in ports if "inout" in str(p.get("direction", "")).lower())
                print(f"    ➜ input: {in_cnt}, output: {out_cnt}, inout: {inout_cnt}")

            # Сводка по always-блокам
            sync_cnt = 0
            comb_cnt = 0
            for blk in always_blocks:
                sens = str(blk.get("sensitivity", "")).lower()
                if "posedge" in sens or "negedge" in sens:
                    sync_cnt += 1
                elif "@*" in sens or "always_comb" in sens:
                    comb_cnt += 1
            if always_blocks:
                print(f"    ➜ sync: {sync_cnt}, comb: {comb_cnt}, other: {len(always_blocks) - sync_cnt - comb_cnt}")

    # -----------------------------------------------------------------
    # Расширенный анализ (если есть)
    # -----------------------------------------------------------------
    if enhanced:
        # ---------------------- Типы данных ---------------------------
        data_types = enhanced.get("data_types", {}) or {}
        if any(data_types.get(k) for k in ("typedefs", "structs", "enums", "unions")):
            _print_section("РАСШИРЕННЫЙ АНАЛИЗ: ТИПЫ ДАННЫХ", "-")

            for key, label in (
                ("typedefs", "Typedef'ы"),
                ("structs", "Struct'ы"),
                ("enums", "Enum'ы"),
                ("unions", "Union'ы"),
            ):
                lst = data_types.get(key, []) or []
                if not lst:
                    continue
                print(f"\n{label} ({len(lst)}):")
                for t in lst[:10]:  # не засоряем вывод бесконечным списком
                    nm = t.get("name", "unnamed")
                    extra = ""
                    if key == "enums":
                        mem = t.get("members") or []
                        if mem:
                            extra = f"  {{{', '.join(mem[:8])}{'…' if len(mem) > 8 else ''}}}"
                    print(f"  - {nm}{extra} [pyslang]")

                if len(lst) > 10:
                    print(f"  ... ещё {len(lst) - 10} элементов")

        # ---------------------- Поведенческие элементы ----------------
        behavioral = enhanced.get("behavioral_elements", {}) or {}
        funcs = behavioral.get("functions", []) or []
        tasks = behavioral.get("tasks", []) or []
        if funcs or tasks:
            _print_section("РАСШИРЕННЫЙ АНАЛИЗ: ФУНКЦИИ И TASK'И", "-")
            if funcs:
                print(f"\nФункции ({len(funcs)}):")
                for f in funcs[:15]:
                    print(f"  - {f.get('name', 'unnamed')} [pyslang]")
                if len(funcs) > 15:
                    print(f"  ... ещё {len(funcs) - 15} функций")

            if tasks:
                print(f"\nTasks ({len(tasks)}):")
                for t in tasks[:15]:
                    print(f"  - {t.get('name', 'unnamed')} [pyslang]")
                if len(tasks) > 15:
                    print(f"  ... ещё {len(tasks) - 15} tasks")

        # ---------------------- Соединения и иерархия ----------------
        conn_graph = enhanced.get("connection_graph", {}) or {}
        hierarchies = enhanced.get("hierarchies", []) or []
        if conn_graph or hierarchies:
            _print_section("РАСШИРЕННЫЙ АНАЛИЗ: СВЯЗИ И ИЕРАРХИЯ", "-")
            if conn_graph:
                nodes = conn_graph.get("nodes", []) or []
                edges = conn_graph.get("edges", []) or []
                print(f"\nГраф соединений:")
                print(f"  Узлов:  {len(nodes)}")
                print(f"  Рёбер:  {len(edges)}")
                if edges:
                    print("  Примеры рёбер (до 5):")
                    for e in edges[:5]:
                        src = e.get("source", "?")
                        dst = e.get("target", "?")
                        inst = e.get("instance_name", "")
                        print(f"    - {src} --[{inst}]--> {dst}")
                    if len(edges) > 5:
                        print(f"    ... ещё {len(edges) - 5} рёбер")

            if hierarchies:
                print(f"\nДеревья иерархии модулей: {len(hierarchies)} (корневых вершин)")
                # Покажем верхний уровень названий
                root_names = [h.get("name", "?") for h in hierarchies]
                print("  Корни иерархий:", ", ".join(root_names))

        # ---------------------- Тайминговый анализ -------------------
        timing = enhanced.get("timing_analysis", {}) or {}
        if timing:
            _print_section("РАСШИРЕННЫЙ АНАЛИЗ: ТАЙМИНГ", "-")
            sync_mods = _format_int(timing.get("synchronous_modules", 0))
            comb_mods = _format_int(timing.get("combinational_modules", 0))
            mixed_mods = _format_int(timing.get("mixed_modules", 0))

            print(f"\nКлассификация модулей по типу логики:")
            print(f"  - последовательные (synchronous):  {sync_mods}")
            print(f"  - комбинационные (combinational): {comb_mods}")
            print(f"  - смешанные (mixed):               {mixed_mods}")

            module_timing = timing.get("module_timing", []) or []
            if module_timing:
                print("\nПо модулям:")
                for mt in module_timing:
                    print(
                        f"  - {mt.get('module', '?')}: "
                        f"type={mt.get('type', 'unknown')}, "
                        f"always={mt.get('always_blocks', 0)}"
                    )

            clock_domains = timing.get("clock_domains", []) or []
            if clock_domains:
                print("\nТактовые домены:")
                for cd in clock_domains:
                    print(
                        f"  - {cd.get('module', '?')}: "
                        f"{cd.get('type', 'unknown')} "
                        f"(always={cd.get('always_blocks_count', 0)})"
                    )

            reset_analysis = timing.get("reset_analysis", []) or []
            if reset_analysis:
                print("\nСигналы сброса:")
                for ra in reset_analysis:
                    rs = ", ".join(ra.get("reset_signals", []))
                    print(
                        f"  - {ra.get('module', '?')}: "
                        f"{ra.get('reset_type', 'unknown')} reset(s): {rs}"
                    )

            assign_stat = timing.get("assignment_analysis", {}) or {}
            if assign_stat:
                total_ca = assign_stat.get("continuous_assignments", 0)
                print(f"\nНепрерывных assign'ов всего: {total_ca}")
                mods_with_ca = assign_stat.get("modules_with_assignments", []) or []
                if mods_with_ca:
                    print("  По модулям (только модули с assign'ами):")
                    for row in mods_with_ca:
                        print(
                            f"    - {row.get('module', '?')}: "
                            f"continuous={row.get('continuous', 0)}, "
                            f"total={row.get('total', 0)}"
                        )

        # ---------------------- FSM-обзор (из enhanced_analysis) -----
        fsm_summary = enhanced.get("fsm", {}) or {}
        if fsm_summary:
            _print_section("РАСШИРЕННЫЙ АНАЛИЗ: FSM (ОБЗОР)", "-")
            total_like = fsm_summary.get("total_modules_with_fsm_like", 0)
            print(f"\nМодулей с FSM-подобным паттерном: {total_like}")

            for m in fsm_summary.get("modules", []) or []:
                mod_name = m.get("module", "?")
                state_sigs = m.get("state_signals") or []
                enum_states = m.get("enum_states") or []
                if not (state_sigs or enum_states):
                    continue
                print(f"\nМодуль: {mod_name}")
                if state_sigs:
                    ss = ", ".join(
                        f"{s.get('name', '?')}[{s.get('width', '')}]"
                        for s in state_sigs
                    )
                    print(f"  Переменные состояния: {ss}")
                if enum_states:
                    es = ", ".join(s.get("name", "?") for s in enum_states)
                    print(f"  Состояния (из enum):  {es}")

    # -----------------------------------------------------------------
    # Внутренний "сырой" вывод, если нужен (для отладки)
    # -----------------------------------------------------------------
    if verbose_internal:
        _print_section("НИЖЕЛЕЖАЩЕЕ ДЕРЕВО AST", "=")
        if use_complete_ast:
            print_complete_ast(ast)
        else:
            print_unified_ast(ast)


# =====================================================================
# CLI
# =====================================================================

def main() -> None:
    """
    CLI-интерфейс:
        python sv_analyzer.py path/to/file.sv
        python sv_analyzer.py path/to/file.sv --basic
        python sv_analyzer.py path/to/file.sv --dump-ast ast.json
        python sv_analyzer.py path/to/file.sv --dump-fsm fsm_module.json --module TicketVendorBotOneHot
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Анализ SystemVerilog-кода через CST/AST/CompleteAST."
    )
    parser.add_argument(
        "file",
        help="Путь к SystemVerilog-файлу (.sv, .svh, .v и т.п.)",
    )
    parser.add_argument(
        "--basic",
        action="store_true",
        help="Использовать только базовый ASTService (без CompleteASTService).",
    )
    parser.add_argument(
        "--dump-ast",
        metavar="PATH",
        help="Сохранить полный AST в указанный JSON-файл.",
    )
    parser.add_argument(
        "--dump-fsm",
        metavar="PATH",
        help="Сохранить модуль в формате FSMDetectorService в JSON-файл.",
    )
    parser.add_argument(
        "--module",
        dest="module_name",
        metavar="NAME",
        help="Имя модуля для экспорта FSM-пэйлоада (по умолчанию первый модуль).",
    )
    parser.add_argument(
        "--no-print",
        action="store_true",
        help="Не печатать человекочитаемый отчёт в консоль.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Дополнительно вывести 'сырой' AST (print_complete_ast / print_unified_ast).",
    )

    args = parser.parse_args()

    # 1. Анализ файла
    use_complete_ast = not args.basic
    ast = analyze_file(args.file, use_complete_ast=use_complete_ast)

    # 2. Печать отчёта
    if not args.no_print:
        print_ast_report(
            ast,
            filename=args.file,
            use_complete_ast=use_complete_ast,
            verbose_internal=args.raw,
        )

    # 3. Опциональный дамп полного AST
    if args.dump_ast:
        save_json(ast, args.dump_ast, pretty=True)
        print(f"\n[sv_analyzer] Полный AST сохранён в: {args.dump_ast}")

    # 4. Опциональный экспорт в формат FSMDetectorService
    if args.dump_fsm:
        payload = export_fsm_detector_payload(
            ast=ast,
            out_path=args.dump_fsm,
            module_name=args.module_name,
            pretty=True,
        )
        print(f"[sv_analyzer] FSM-пэйлоад сохранён в: {args.dump_fsm}")
        print(f"[sv_analyzer] Экспортирован модуль: {payload['module'].get('name','<unknown>')}")


if __name__ == "__main__":
    main()
