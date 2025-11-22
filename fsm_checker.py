# -*- coding: utf-8 -*-
# fsm_checker.py
"""
Проверка наличия конечного автомата (FSM) в SystemVerilog-модуле.

Использует:
  - CSTService (cst_service.py)
  - CompleteASTService (complete_ast_service_pyslang.py)
  - FSMDetectorService (fsm_detector_service.py)

Пример использования из консоли:

  python fsm_checker.py path/to/file.sv

  python fsm_checker.py path/to/file.sv --module detect_4_bit_sequence_using_fsm

  python fsm_checker.py path/to/file.sv --json out/fsm_result.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from cst_service import CSTService
from test_free import CompleteASTService
from fsm_detector_service import FSMDetectorService


def detect_fsm_in_file(
    filepath: str | Path,
    module_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Запускает полный пайплайн:
      1) парсинг SystemVerilog в CST,
      2) построение полного AST,
      3) поиск FSM в выбранном модуле.

    :param filepath: путь к .sv / .svh / .v файлу
    :param module_name: имя модуля (если None — берётся первый модуль)
    :return: словарь с информацией о FSM (формат FSMDetectorService.detect_finite_state_machines)
    """
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"Файл не найден: {path}")

    source_text = path.read_text(encoding="utf-8")

    # 1. Строим CST
    cst_service = CSTService()
    tree = cst_service.build_cst_from_text(source_text, path.name)

    # 2. Строим ПОЛНЫЙ AST (с нормализацией под FSMDetectorService)
    complete_service = CompleteASTService()
    complete_ast = complete_service.build_complete_ast_from_cst(tree)

    modules = complete_ast.get("modules", []) or []
    if not modules:
        raise ValueError("В AST не найдено ни одного модуля — нечего анализировать.")

    # 3. Выбираем модуль
    if module_name:
        module = next((m for m in modules if m.get("name") == module_name), None)
        if module is None:
            available = ", ".join(m.get("name", "?") for m in modules)
            raise ValueError(
                f"Модуль с именем '{module_name}' не найден. "
                f"Доступные модули: {available}"
            )
    else:
        module = modules[0]

    # 4. Запускаем FSM-детектор
    detector = FSMDetectorService()
    fsm_info = detector.detect_finite_state_machines(module, tree)

    # Добавим немного контекста сверху
    fsm_info_wrapped: Dict[str, Any] = {
        "file": str(path),
        "module": module.get("name", ""),
        "fsm": fsm_info,
    }
    return fsm_info_wrapped


def print_fsm_result(result: Dict[str, Any]) -> None:
    """
    Красивый вывод результата FSM-анализа в консоль.
    """
    file = result.get("file", "<unknown>")
    module_name = result.get("module", "<unnamed>")
    fsm = result.get("fsm", {})

    print("\n" + "=" * 80)
    print("FSM ANALYSIS RESULT")
    print("=" * 80)
    print(f"Файл:   {file}")
    print(f"Модуль: {module_name}")

    if not fsm.get("detected", False):
        print("\n❌ Конечный автомат в данном модуле НЕ обнаружен.")
        return

    print("\n✅ Обнаружен конечный автомат.")
    print(f"Тип FSM: {fsm.get('type', 'unknown')}")
    print(f"Тактовый сигнал: {fsm.get('clock_signal', 'unknown')}")
    print(f"Условие сброса:  {fsm.get('reset_condition', 'unknown')}")

    # Переменные состояния
    state_vars = fsm.get("state_variables", [])
    if state_vars:
        print("\nПеременные состояния:")
        for sv in state_vars:
            name = sv.get("name", "?")
            vtype = sv.get("type", "")
            width = sv.get("width", "")
            patt = sv.get("pattern_match", "")
            extra = f", width={width}" if width else ""
            pm = f" (match: {patt})" if patt else ""
            print(f"  - {name} [{vtype}{extra}]{pm}")

    # Состояния
    states = fsm.get("states", [])
    if states:
        print("\nСписок состояний:")
        for st in states:
            name = st.get("name", "?")
            stype = st.get("type", "")
            src = st.get("source", "")
            enum_name = st.get("enum") or st.get("enum_type") or ""
            enum_suffix = f", enum={enum_name}" if enum_name else ""
            print(f"  - {name} ({stype}{enum_suffix}, source={src})")
    else:
        print("\nСписок состояний пуст (детектор не смог их выделить).")

    # Переходы
    transitions = fsm.get("transitions", [])
    if transitions:
        print("\nПереходы:")
        for t in transitions:
            src = t.get("from_state", "?")
            dst = t.get("to_state", "?")
            cond = t.get("condition", "???")
            typ = t.get("type", "")
            print(f"  - {src}  ->  {dst}   [{cond}, {typ}]")
    else:
        print("\nПереходы не найдены (детектор не смог их вывести).")

    print("\n" + "=" * 80 + "\n")


def save_result_json(result: Dict[str, Any], out_path: str | Path) -> None:
    """
    Сохранить результат FSM-анализа в JSON.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[fsm_checker] Результат FSM-анализа сохранён в: {out_path}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Проверка наличия конечного автомата (FSM) в SystemVerilog-файле."
    )
    parser.add_argument(
        "file",
        help="Путь к SystemVerilog-файлу (.sv, .svh, .v и т.п.)",
    )
    parser.add_argument(
        "--module",
        dest="module_name",
        help="Имя модуля для анализа (если не указано — берётся первый в файле).",
    )
    parser.add_argument(
        "--json",
        dest="json_out",
        help="Путь для сохранения результата в JSON.",
    )

    args = parser.parse_args()

    try:
        result = detect_fsm_in_file(args.file, module_name=args.module_name)
        print_fsm_result(result)

        if args.json_out:
            save_result_json(result, args.json_out)

    except Exception as e:
        print("\n‼ Ошибка при анализе FSM:")
        print(f"   {e}")


if __name__ == "__main__":
    main()
