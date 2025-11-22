# -*- coding: utf-8 -*-
# fsm_detector_gui.py
"""
Графический интерфейс для детектирования конечных автоматов (FSM)
в SystemVerilog коде.

Использует:
  - CSTService (cst_service.py)
  - CompleteASTService (complete_ast_service_pyslang.py)
  - FSMDetectorService (fsm_detector_service.py)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
from pathlib import Path
from datetime import datetime

# Добавляем путь к текущей папке, чтобы видеть остальные модули
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импорт сервисов анализа
from cst_service import CSTService
from test_free import CompleteASTService
from fsm_detector_service import FSMDetectorService


class FSMDetectorGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("FSM Detector – SystemVerilog Analyzer")
        self.root.geometry("1100x750")

        # Сервисы
        self.cst_service = CSTService()
        self.ast_service = CompleteASTService()
        self.fsm_service = FSMDetectorService()

        # Текущее состояние
        self.current_file: Path | None = None
        self.current_tree = None
        self.current_ast: dict | None = None
        self.current_modules: list[dict] = []
        self.fsm_results_by_module: dict[str, dict] = {}

        self._build_ui()

    # -------------------------------------------------------------------------
    # UI
    # -------------------------------------------------------------------------

    def _build_ui(self) -> None:
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.grid(row=0, column=0, sticky="nsew")

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # --- Верх: выбор файла ------------------------------------------------
        file_frame = ttk.LabelFrame(main_frame, text="Выбор файла", padding=10)
        file_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for i in range(5):
            file_frame.columnconfigure(i, weight=0)
        file_frame.columnconfigure(1, weight=1)

        ttk.Label(file_frame, text="SystemVerilog файл:").grid(row=0, column=0, sticky="w")

        self.file_path_var = tk.StringVar()
        entry = ttk.Entry(file_frame, textvariable=self.file_path_var)
        entry.grid(row=0, column=1, sticky="ew", padx=5)

        ttk.Button(file_frame, text="Обзор…", command=self._browse_file).grid(row=0, column=2, padx=5)
        ttk.Button(file_frame, text="Анализ", command=self._analyze_file).grid(row=0, column=3, padx=5)

        # Модуль (комбобокс)
        ttk.Label(file_frame, text="Модуль:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.module_names_var = tk.StringVar(value=[])
        self.module_combo = ttk.Combobox(
            file_frame,
            textvariable=tk.StringVar(),
            values=[],
            state="readonly",
            width=40,
        )
        self.module_combo.grid(row=1, column=1, sticky="w", padx=5, pady=(8, 0))
        self.module_combo.bind("<<ComboboxSelected>>", self._on_module_selected)

        self.modules_summary_var = tk.StringVar(value="Модулей: 0, FSM: 0")
        ttk.Label(file_frame, textvariable=self.modules_summary_var).grid(
            row=1, column=2, columnspan=2, sticky="w", pady=(8, 0)
        )

        # --- Информация о файле ----------------------------------------------
        info_frame = ttk.LabelFrame(main_frame, text="Информация о файле", padding=10)
        info_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        info_frame.columnconfigure(0, weight=1)

        self.file_info_text = scrolledtext.ScrolledText(info_frame, height=4, wrap="word")
        self.file_info_text.grid(row=0, column=0, sticky="nsew")
        self.file_info_text.configure(font=("Consolas", 9))

        # --- Результаты FSM ---------------------------------------------------
        results_frame = ttk.LabelFrame(main_frame, text="Результаты анализа", padding=10)
        results_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        results_frame.rowconfigure(0, weight=1)
        results_frame.columnconfigure(0, weight=1)

        self.results_notebook = ttk.Notebook(results_frame)
        self.results_notebook.grid(row=0, column=0, sticky="nsew")

        # Вкладка Summary
        self.summary_frame = ttk.Frame(self.results_notebook, padding=10)
        self.results_notebook.add(self.summary_frame, text="Сводка")
        self._build_summary_tab()

        # Вкладка States
        self.states_frame = ttk.Frame(self.results_notebook, padding=10)
        self.results_notebook.add(self.states_frame, text="Состояния")
        self._build_states_tab()

        # Вкладка Transitions
        self.transitions_frame = ttk.Frame(self.results_notebook, padding=10)
        self.results_notebook.add(self.transitions_frame, text="Переходы")
        self._build_transitions_tab()

        # Вкладка Module Info
        self.module_frame = ttk.Frame(self.results_notebook, padding=10)
        self.results_notebook.add(self.module_frame, text="Модуль")
        self._build_module_tab()

        # --- Превью кода ------------------------------------------------------
        code_frame = ttk.LabelFrame(main_frame, text="Код", padding=10)
        code_frame.grid(row=3, column=0, sticky="nsew")
        code_frame.rowconfigure(0, weight=1)
        code_frame.columnconfigure(0, weight=1)

        self.code_text = scrolledtext.ScrolledText(code_frame, wrap="none", height=12)
        self.code_text.grid(row=0, column=0, sticky="nsew")
        self.code_text.configure(font=("Consolas", 10))

        # --- Статус-бар -------------------------------------------------------
        self.status_var = tk.StringVar(value="Готов к анализу SystemVerilog файлов")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w")
        status_label.grid(row=4, column=0, sticky="ew", pady=(5, 0))

    # --- Вкладка Summary ------------------------------------------------------

    def _build_summary_tab(self) -> None:
        f = self.summary_frame
        f.columnconfigure(1, weight=1)

        def add_row(row: int, label: str, var_attr: str, default: str):
            ttk.Label(f, text=label, font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=default)
            setattr(self, var_attr, var)
            ttk.Label(f, textvariable=var, font=("Arial", 10)).grid(row=row, column=1, sticky="w", pady=2)

        add_row(0, "FSM обнаружен:", "fsm_detected_var", "—")
        add_row(1, "Тип FSM:", "fsm_type_var", "—")
        add_row(2, "Переменные состояния:", "state_vars_var", "—")
        add_row(3, "Тактовый сигнал:", "clock_var", "—")
        add_row(4, "Условие сброса:", "reset_var", "—")
        add_row(5, "Кол-во состояний:", "states_count_var", "0")
        add_row(6, "Кол-во переходов:", "transitions_count_var", "0")

    # --- Вкладка States -------------------------------------------------------

    def _build_states_tab(self) -> None:
        f = self.states_frame
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)

        columns = ("Name", "Type", "Source")
        self.states_tree = ttk.Treeview(f, columns=columns, show="headings", height=8)

        for col in columns:
            self.states_tree.heading(col, text=col)
            self.states_tree.column(col, width=160, anchor="w")

        vsb = ttk.Scrollbar(f, orient="vertical", command=self.states_tree.yview)
        self.states_tree.configure(yscrollcommand=vsb.set)

        self.states_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

    # --- Вкладка Transitions --------------------------------------------------

    def _build_transitions_tab(self) -> None:
        f = self.transitions_frame
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)

        columns = ("From", "To", "Condition", "Type", "Sensitivity")
        self.transitions_tree = ttk.Treeview(f, columns=columns, show="headings", height=8)

        for col in columns:
            self.transitions_tree.heading(col, text=col)
            self.transitions_tree.column(col, width=140 if col != "Sensitivity" else 200, anchor="w")

        vsb = ttk.Scrollbar(f, orient="vertical", command=self.transitions_tree.yview)
        self.transitions_tree.configure(yscrollcommand=vsb.set)

        self.transitions_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

    # --- Вкладка Module Info --------------------------------------------------

    def _build_module_tab(self) -> None:
        f = self.module_frame
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)

        self.module_info_text = scrolledtext.ScrolledText(f, wrap="word")
        self.module_info_text.grid(row=0, column=0, sticky="nsew")
        self.module_info_text.configure(font=("Consolas", 9))

    # -------------------------------------------------------------------------
    # Действия
    # -------------------------------------------------------------------------

    def _browse_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Выбор SystemVerilog файла",
            filetypes=[
                ("SystemVerilog files", "*.sv *.svh"),
                ("Verilog files", "*.v *.vh"),
                ("All files", "*.*"),
            ],
        )
        if not file_path:
            return

        self.current_file = Path(file_path)
        self.file_path_var.set(str(self.current_file))
        self._load_file_contents()

    def _load_file_contents(self) -> None:
        if not self.current_file:
            return

        try:
            text = self.current_file.read_text(encoding="utf-8", errors="ignore")
            self.code_text.delete("1.0", tk.END)
            self.code_text.insert("1.0", text)

            st = self.current_file.stat()
            size = st.st_size
            mtime = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

            info = (
                f"Файл:  {self.current_file.name}\n"
                f"Путь:  {self.current_file.parent}\n"
                f"Размер: {size} байт\n"
                f"Изменён: {mtime}\n"
            )
            self.file_info_text.delete("1.0", tk.END)
            self.file_info_text.insert("1.0", info)

            self.status_var.set(f"Загружен файл: {self.current_file.name}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл: {e}")
            self.status_var.set("Ошибка чтения файла")

    def _analyze_file(self) -> None:
        if not self.current_file or not self.current_file.exists():
            messagebox.showwarning("Предупреждение", "Сначала выберите корректный файл.")
            return

        try:
            self.status_var.set("Парсинг SystemVerilog и построение AST...")
            self.root.update_idletasks()

            code = self.current_file.read_text(encoding="utf-8", errors="ignore")

            # 1) CST
            tree = self.cst_service.build_cst_from_text(code, self.current_file.name)
            self.current_tree = tree

            # 2) Полный AST с нормализацией (под FSMDetectorService)
            ast = self.ast_service.build_complete_ast_from_cst(tree)
            self.current_ast = ast

            modules = ast.get("modules", []) or []
            self.current_modules = modules

            if not modules:
                messagebox.showinfo("Результат", "В файле не найдено ни одного модуля.")
                self._clear_results()
                self.status_var.set("Модули не найдены")
                return

            # 3) Прогоняем FSM-детектор по всем модулям
            self.fsm_results_by_module = {}
            fsm_count = 0
            for m in modules:
                name = m.get("name", "<unnamed>")
                info = self.fsm_service.detect_finite_state_machines(m, tree)
                self.fsm_results_by_module[name] = info
                if info.get("detected"):
                    fsm_count += 1

            # Обновляем Combobox модулей
            module_names = [m.get("name", f"module_{i}") for i, m in enumerate(modules)]
            if not module_names:
                module_names = ["<нет модулей>"]
            self.module_combo["values"] = module_names
            self.module_combo.set(module_names[0])

            self.modules_summary_var.set(f"Модулей: {len(modules)}, FSM обнаружено: {fsm_count}")
            self.status_var.set("Анализ завершён. Выберите модуль для просмотра результатов.")

            # Показываем результаты для первого модуля
            self._update_results_for_module(module_names[0])

        except Exception as e:
            messagebox.showerror("Ошибка анализа", str(e))
            self.status_var.set("Ошибка при анализе файла")

    def _on_module_selected(self, event=None) -> None:
        name = self.module_combo.get()
        if not name:
            return
        self._update_results_for_module(name)

    # -------------------------------------------------------------------------
    # Обновление результатов по выбранному модулю
    # -------------------------------------------------------------------------

    def _clear_results(self) -> None:
        self.fsm_detected_var.set("—")
        self.fsm_type_var.set("—")
        self.state_vars_var.set("—")
        self.clock_var.set("—")
        self.reset_var.set("—")
        self.states_count_var.set("0")
        self.transitions_count_var.set("0")

        self.states_tree.delete(*self.states_tree.get_children())
        self.transitions_tree.delete(*self.transitions_tree.get_children())
        self.module_info_text.delete("1.0", tk.END)

    def _update_results_for_module(self, module_name: str) -> None:
        if not self.current_modules or not self.current_tree:
            return

        # Находим модуль
        module = next((m for m in self.current_modules if m.get("name") == module_name), None)
        if module is None:
            # на случай, если имена как-то не совпали
            module = self.current_modules[0]

        fsm_info = self.fsm_results_by_module.get(module.get("name", ""), None)
        if fsm_info is None:
            fsm_info = self.fsm_service.detect_finite_state_machines(module, self.current_tree)
            self.fsm_results_by_module[module.get("name", "")] = fsm_info

        # --- Summary ---
        detected = fsm_info.get("detected", False)
        self.fsm_detected_var.set("Да" if detected else "Нет")
        self.fsm_type_var.set(fsm_info.get("type", "unknown"))

        state_vars = ", ".join(v.get("name", "?") for v in fsm_info.get("state_variables", []) or [])
        self.state_vars_var.set(state_vars if state_vars else "—")

        self.clock_var.set(fsm_info.get("clock_signal", "unknown"))
        self.reset_var.set(fsm_info.get("reset_condition", "unknown"))

        states = fsm_info.get("states", []) or []
        transitions = fsm_info.get("transitions", []) or []

        self.states_count_var.set(str(len(states)))
        self.transitions_count_var.set(str(len(transitions)))

        # --- States tab ---
        self.states_tree.delete(*self.states_tree.get_children())
        for st in states:
            self.states_tree.insert(
                "",
                tk.END,
                values=(
                    st.get("name", ""),
                    st.get("type", ""),
                    st.get("source", ""),
                ),
            )

        # --- Transitions tab ---
        self.transitions_tree.delete(*self.transitions_tree.get_children())
        for tr in transitions:
            self.transitions_tree.insert(
                "",
                tk.END,
                values=(
                    tr.get("from_state", ""),
                    tr.get("to_state", ""),
                    tr.get("condition", ""),
                    tr.get("type", ""),
                    tr.get("sensitivity", ""),
                ),
            )

        # --- Module Info tab ---
        self._update_module_info(module)

    def _update_module_info(self, module: dict) -> None:
        lines: list[str] = []
        name = module.get("name", "<unnamed>")
        lines.append(f"MODULE {name}")
        lines.append("")

        # Параметры
        params = module.get("parameters", []) or []
        if params:
            lines.append("Параметры:")
            for p in params:
                lines.append(f"  {p.get('name', '?')} = {p.get('value', '')}")
            lines.append("")

        # Порты
        ports = module.get("ports", []) or []
        if ports:
            lines.append("Порты:")
            for p in ports:
                direction = p.get("direction", "")
                width = p.get("width", "")
                wtxt = f" {width}" if width else ""
                lines.append(f"  {direction:7s} {p.get('name','?')}{wtxt}")
            lines.append("")

        # Сигналы
        signals = module.get("signals", []) or []
        if signals:
            lines.append("Сигналы:")
            for s in signals:
                width = s.get("width", "")
                wtxt = f" {width}" if width else ""
                lines.append(f"  {s.get('name','?')}{wtxt} ({s.get('type','var')})")
            lines.append("")

        # Assigns
        assigns = module.get("assigns", []) or []
        if assigns:
            lines.append("Непрерывные присваивания (assign):")
            for a in assigns:
                lines.append(f"  {a.get('left','?')} {a.get('op','=')} {a.get('right','?')}")
            lines.append("")

        # Always
        always_blocks = module.get("always_blocks", []) or []
        if always_blocks:
            lines.append("Always-блоки:")
            for ab in always_blocks:
                sens = ab.get("sensitivity", "")
                lines.append(f"  always ({sens})")
                for asg in ab.get("assignments", []) or []:
                    lines.append(f"    {asg.get('left','?')} {asg.get('op','=')} {asg.get('right','?')}")
            lines.append("")

        # Инстансы
        instances = module.get("instances", []) or []
        if instances:
            lines.append("Инстансы модулей:")
            for inst in instances:
                lines.append(f"  {inst.get('name','?')} : {inst.get('type','?')}")
            lines.append("")

        if not lines:
            lines.append("Нет дополнительной информации по модулю.")

        self.module_info_text.delete("1.0", tk.END)
        self.module_info_text.insert("1.0", "\n".join(lines))


def main() -> None:
    root = tk.Tk()
    app = FSMDetectorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
