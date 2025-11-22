# -*- coding: utf-8 -*-
# complete_ast_analysis_report.py
"""
ПОЛНЫЙ АНАЛИЗ И ОТЧЕТ ДЛЯ SYSTEMVERILOG AST
Выводит ВСЮ статистику, ВСЕ ENUM, ВСЕ сигналы и ВСЕ элементы
С учетом логики FSMDetectorService для определения состояний
"""

import json
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from datetime import datetime

class CompleteASTAnalysisReport:
    """ПОЛНЫЙ ОТЧЕТ ПО АНАЛИЗУ AST С ВЫВОДОМ ВСЕХ ДАННЫХ"""
    
    def __init__(self, ast_data: Dict[str, Any]):
        self.ast = ast_data
        self.report_lines = []
        self.analysis_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._init_fsm_patterns()
    
    def _init_fsm_patterns(self):
        """Инициализация паттернов FSM как в FSMDetectorService"""
        self.fsm_patterns = {
            "state_variables": {
                "state", "current_state", "next_state", "new_state", 
                "fsm_state", "ctrl_state", "present_state", "future_state"
            },
            "state_enum_prefixes": {"state_", "st_", "fsm_", "s_"},
            "state_keywords": {
                "IDLE", "READY", "BUSY", "WAIT", "DONE", "ERROR", 
                "INIT", "START", "STOP", "RUN", "PAUSE", "RESET", 
                "WORK", "FINISH", "F1", "F0", "S1", "S0"  # Добавлены состояния из вашего кода
            }
        }
    
    def generate_complete_report(self, output_file: str = None) -> str:
        """Сгенерировать ПОЛНЫЙ отчет со ВСЕМИ данными"""
        self.report_lines = []
        
        self._add_header("ПОЛНЫЙ АНАЛИЗ SYSTEMVERILOG AST")
        self._add_section("ОБЩАЯ СТАТИСТИКА")
        self._print_general_statistics()
        
        self._add_section("МЕТАДАННЫЕ АНАЛИЗА")
        self._print_metadata()
        
        self._add_section("ДЕТАЛЬНЫЙ АНАЛИЗ МОДУЛЕЙ")
        self._print_modules_detailed()
        
        self._add_section("ВСЕ TYPEDEF")
        self._print_all_typedefs()
        
        self._add_section("ВСЕ STRUCT")
        self._print_all_structs()
        
        self._add_section("ВСЕ ENUM - ПОЛНЫЙ ВЫВОД")
        self._print_all_enums_detailed()
        
        self._add_section("ВСЕ UNION")
        self._print_all_unions()
        
        self._add_section("ВСЕ ИНТЕРФЕЙСЫ")
        self._print_all_interfaces()
        
        self._add_section("ВСЕ ПАКЕТЫ")
        self._print_all_packages()
        
        self._add_section("ВСЕ КЛАССЫ")
        self._print_all_classes()
        
        self._add_section("ВСЕ PROGRAM БЛОКИ")
        self._print_all_programs()
        
        self._add_section("ВСЕ CHECKER БЛОКИ")
        self._print_all_checkers()
        
        self._add_section("ВСЕ CONFIG БЛОКИ")
        self._print_all_configs()
        
        self._add_section("ВСЕ ФУНКЦИИ")
        self._print_all_functions()
        
        self._add_section("ВСЕ ЗАДАЧИ")
        self._print_all_tasks()
        
        self._add_section("ВСЕ ПАРАМЕТРЫ")
        self._print_all_parameters()
        
        self._add_section("АНАЛИЗ FSM - РАСШИРЕННЫЙ")
        self._print_enhanced_fsm_analysis()
        
        self._add_section("ГРАФ СОЕДИНЕНИЙ")
        self._print_connection_graph()
        
        self._add_section("ИЕРАРХИЯ МОДУЛЕЙ")
        self._print_hierarchies()
        
        self._add_section("ТАЙМИНГ АНАЛИЗ")
        self._print_timing_analysis()
        
        self._add_section("СИГНАЛЫ СБРОСА")
        self._print_reset_analysis()
        
        self._add_section("АНАЛИЗ ПРИСВАИВАНИЙ")
        self._print_assignment_analysis()
        
        self._add_footer()
        
        report_text = "\n".join(self.report_lines)
        
        # Сохранение в файл
        if output_file:
            self._save_report_to_file(report_text, output_file)
        
        return report_text
    
    def _add_header(self, title: str):
        """Добавить заголовок"""
        self.report_lines.append("=" * 100)
        self.report_lines.append(f" {title}")
        self.report_lines.append("=" * 100)
        self.report_lines.append(f"Время анализа: {self.analysis_time}")
        self.report_lines.append("")
    
    def _add_section(self, section_name: str):
        """Добавить раздел"""
        self.report_lines.append("")
        self.report_lines.append("-" * 80)
        self.report_lines.append(f" {section_name}")
        self.report_lines.append("-" * 80)
    
    def _add_footer(self):
        """Добавить подвал"""
        self.report_lines.append("")
        self.report_lines.append("=" * 100)
        self.report_lines.append(" АНАЛИЗ ЗАВЕРШЕН ")
        self.report_lines.append("=" * 100)
    
    def _print_general_statistics(self):
        """Вывести общую статистику"""
        metadata = self.ast.get("metadata", {})
        
        stats = [
            f"Всего модулей: {metadata.get('total_modules_enhanced', 0)}",
            f"Интерфейсов: {metadata.get('total_interfaces', 0)}",
            f"Пакетов: {metadata.get('total_packages', 0)}",
            f"Классов: {metadata.get('total_classes', 0)}",
            f"Program блоков: {metadata.get('total_programs', 0)}",
            f"Checker блоков: {metadata.get('total_checkers', 0)}",
            f"Config блоков: {metadata.get('total_configs', 0)}",
            f"Typedef: {metadata.get('total_typedefs', 0)}",
            f"Struct: {metadata.get('total_structs', 0)}",
            f"Enum: {metadata.get('total_enums', 0)}",
            f"Union: {metadata.get('total_unions', 0)}",
            f"Функций: {metadata.get('total_functions', 0)}",
            f"Задач: {metadata.get('total_tasks', 0)}",
            f"Парсер: {self.ast.get('parser_used', 'unknown')}",
            f"Тип AST: {self.ast.get('type', 'unknown')}",
            f"Версия: {self.ast.get('version', 'unknown')}"
        ]
        
        for stat in stats:
            self.report_lines.append(f"  {stat}")
    
    def _print_metadata(self):
        """Вывести метаданные"""
        metadata = self.ast.get("metadata", {})
        for key, value in metadata.items():
            self.report_lines.append(f"  {key}: {value}")
    
    def _print_modules_detailed(self):
        """Детальный вывод информации о модулях"""
        modules = self.ast.get("modules", [])
        
        for i, module in enumerate(modules, 1):
            self.report_lines.append(f"")
            self.report_lines.append(f"  МОДУЛЬ {i}: {module.get('name', 'unnamed')}")
            self.report_lines.append(f"  {'='*50}")
            
            # Порты
            ports = module.get("ports", [])
            self.report_lines.append(f"    ПОРТЫ ({len(ports)}):")
            for port in ports:
                self.report_lines.append(f"      {port.get('direction', 'unknown'):<10} {port.get('name', 'unnamed'):<20} {port.get('width', '')}")
            
            # Сигналы - ВЫВОДИМ ВСЕ СИГНАЛЫ
            signals = module.get("signals", [])
            self.report_lines.append(f"    СИГНАЛЫ ({len(signals)}):")
            for signal in signals:
                signal_type = signal.get('type', signal.get('kind', 'unknown'))
                signal_name = signal.get('name', 'unnamed')
                signal_width = signal.get('width', '')
                
                # Определяем тип сигнала по логике FSMDetector
                signal_category = self._classify_signal(signal_name, signal_type, signal_width)
                
                self.report_lines.append(f"      {signal_type:<10} {signal_name:<20} {signal_width:<10} [{signal_category}]")
            
            # Параметры
            parameters = module.get("parameters", [])
            if parameters:
                self.report_lines.append(f"    ПАРАМЕТРЫ ({len(parameters)}):")
                for param in parameters:
                    self.report_lines.append(f"      parameter {param.get('name', 'unnamed')} = {param.get('value', '')}")
            
            # Always блоки
            always_blocks = module.get("always_blocks", [])
            self.report_lines.append(f"    ALWAYS БЛОКИ ({len(always_blocks)}):")
            for j, block in enumerate(always_blocks, 1):
                sens = block.get("sensitivity", "")
                assignments = block.get("assignments", [])
                self.report_lines.append(f"      Блок {j}: {sens}")
                for assign in assignments:
                    self.report_lines.append(f"        {assign.get('left', '')} {assign.get('op', '=')} {assign.get('right', '')}")
            
            # Assign
            assigns = module.get("assigns", [])
            if assigns:
                self.report_lines.append(f"    ASSIGN ({len(assigns)}):")
                for assign in assigns:
                    self.report_lines.append(f"      assign {assign.get('left', '')} = {assign.get('right', '')}")
            
            # Инстансы
            instances = module.get("instances", [])
            if instances:
                self.report_lines.append(f"    ИНСТАНСЫ ({len(instances)}):")
                for inst in instances:
                    self.report_lines.append(f"      {inst.get('name', 'unnamed')} : {inst.get('type', 'unknown')}")
    
    def _classify_signal(self, signal_name: str, signal_type: str, signal_width: str) -> str:
        """Классифицировать сигнал по логике FSMDetector"""
        name_lower = signal_name.lower()
        
        # Проверка на state переменные
        for pattern in self.fsm_patterns["state_variables"]:
            if pattern in name_lower:
                return "STATE_VARIABLE"
        
        # Проверка на префиксы state
        for prefix in self.fsm_patterns["state_enum_prefixes"]:
            if name_lower.startswith(prefix):
                return "STATE_PREFIX"
        
        # Проверка на состояния
        for keyword in self.fsm_patterns["state_keywords"]:
            if keyword.upper() == signal_name.upper():
                return "FSM_STATE"
        
        # Проверка на clock/reset
        if any(p in name_lower for p in ["clk", "clock"]):
            return "CLOCK_SIGNAL"
        if any(p in name_lower for p in ["rst", "reset"]):
            return "RESET_SIGNAL"
        
        return "REGULAR_SIGNAL"
    
    def _print_all_typedefs(self):
        """Вывести ВСЕ typedef"""
        data_types = self.ast.get("enhanced_analysis", {}).get("data_types", {})
        typedefs = data_types.get("typedefs", [])
        
        if not typedefs:
            self.report_lines.append("  Typedef не найдены")
            return
        
        for i, typedef in enumerate(typedefs, 1):
            self.report_lines.append(f"  TYPEDEF {i}: {typedef.get('name', 'unnamed')}")
            self.report_lines.append(f"    Определение: {typedef.get('definition', 'N/A')}")
            self.report_lines.append(f"    Файл: {self._format_location(typedef.get('file_info', {}))}")
            self.report_lines.append("")
    
    def _print_all_structs(self):
        """Вывести ВСЕ struct"""
        data_types = self.ast.get("enhanced_analysis", {}).get("data_types", {})
        structs = data_types.get("structs", [])
        
        if not structs:
            self.report_lines.append("  Struct не найдены")
            return
        
        for i, struct in enumerate(structs, 1):
            self.report_lines.append(f"  STRUCT {i}: {struct.get('name', 'unnamed')}")
            self.report_lines.append(f"    Файл: {self._format_location(struct.get('file_info', {}))}")
            self.report_lines.append("")
    
    def _print_all_enums_detailed(self):
        """Вывести ВСЕ enum ПОДРОБНО с привязкой к модулям"""
        data_types = self.ast.get("enhanced_analysis", {}).get("data_types", {})
        enums = data_types.get("enums", [])
        
        if not enums:
            self.report_lines.append("  Enum не найдены")
            return
        
        self.report_lines.append(f"  НАЙДЕНО ENUM: {len(enums)}")
        self.report_lines.append("")
        
        for i, enum in enumerate(enums, 1):
            self.report_lines.append(f"  ENUM {i}:")
            self.report_lines.append(f"    Имя: {enum.get('name', 'unnamed')}")
            
            members = enum.get("members", [])
            if members:
                self.report_lines.append(f"    Элементы ({len(members)}):")
                for member in members:
                    self.report_lines.append(f"      - {member}")
            else:
                self.report_lines.append("    Элементы: нет элементов")
            
            self.report_lines.append(f"    Файл: {self._format_location(enum.get('file_info', {}))}")
            
            # Поиск модулей, которые используют этот enum
            using_modules = self._find_modules_using_enum(enum.get('name', ''), enum.get('members', []))
            if using_modules:
                self.report_lines.append(f"    Используется в модулях: {', '.join(using_modules)}")
            
            self.report_lines.append("")
    
    def _print_all_unions(self):
        """Вывести ВСЕ union"""
        data_types = self.ast.get("enhanced_analysis", {}).get("data_types", {})
        unions = data_types.get("unions", [])
        
        if not unions:
            self.report_lines.append("  Union не найдены")
            return
        
        for i, union in enumerate(unions, 1):
            self.report_lines.append(f"  UNION {i}: {union.get('name', 'unnamed')}")
            self.report_lines.append(f"    Файл: {self._format_location(union.get('file_info', {}))}")
            self.report_lines.append("")
    
    def _print_all_interfaces(self):
        """Вывести ВСЕ интерфейсы"""
        interfaces = self.ast.get("systemverilog_elements", {}).get("interfaces", [])
        
        if not interfaces:
            self.report_lines.append("  Интерфейсы не найдены")
            return
        
        for i, interface in enumerate(interfaces, 1):
            self.report_lines.append(f"  ИНТЕРФЕЙС {i}: {interface.get('name', 'unnamed')}")
            self.report_lines.append(f"    Тип: {interface.get('type', 'N/A')}")
            self.report_lines.append(f"    Файл: {self._format_location(interface.get('file_info', {}))}")
            self.report_lines.append("")
    
    def _print_all_packages(self):
        """Вывести ВСЕ пакеты"""
        packages = self.ast.get("systemverilog_elements", {}).get("packages", [])
        
        if not packages:
            self.report_lines.append("  Пакеты не найдены")
            return
        
        for i, package in enumerate(packages, 1):
            self.report_lines.append(f"  ПАКЕТ {i}: {package.get('name', 'unnamed')}")
            self.report_lines.append(f"    Тип: {package.get('type', 'N/A')}")
            self.report_lines.append(f"    Файл: {self._format_location(package.get('file_info', {}))}")
            self.report_lines.append("")
    
    def _print_all_classes(self):
        """Вывести ВСЕ классы"""
        classes = self.ast.get("systemverilog_elements", {}).get("classes", [])
        
        if not classes:
            self.report_lines.append("  Классы не найдены")
            return
        
        for i, cls in enumerate(classes, 1):
            self.report_lines.append(f"  КЛАСС {i}: {cls.get('name', 'unnamed')}")
            self.report_lines.append(f"    Тип: {cls.get('type', 'N/A')}")
            self.report_lines.append(f"    Файл: {self._format_location(cls.get('file_info', {}))}")
            self.report_lines.append("")
    
    def _print_all_programs(self):
        """Вывести ВСЕ program блоки"""
        programs = self.ast.get("systemverilog_elements", {}).get("programs", [])
        
        if not programs:
            self.report_lines.append("  Program блоки не найдены")
            return
        
        for i, program in enumerate(programs, 1):
            self.report_lines.append(f"  PROGRAM {i}: {program.get('name', 'unnamed')}")
            self.report_lines.append(f"    Тип: {program.get('type', 'N/A')}")
            self.report_lines.append(f"    Файл: {self._format_location(program.get('file_info', {}))}")
            self.report_lines.append("")
    
    def _print_all_checkers(self):
        """Вывести ВСЕ checker блоки"""
        checkers = self.ast.get("systemverilog_elements", {}).get("checkers", [])
        
        if not checkers:
            self.report_lines.append("  Checker блоки не найдены")
            return
        
        for i, checker in enumerate(checkers, 1):
            self.report_lines.append(f"  CHECKER {i}: {checker.get('name', 'unnamed')}")
            self.report_lines.append(f"    Тип: {checker.get('type', 'N/A')}")
            self.report_lines.append(f"    Файл: {self._format_location(checker.get('file_info', {}))}")
            self.report_lines.append("")
    
    def _print_all_configs(self):
        """Вывести ВСЕ config блоки"""
        configs = self.ast.get("systemverilog_elements", {}).get("configs", [])
        
        if not configs:
            self.report_lines.append("  Config блоки не найдены")
            return
        
        for i, config in enumerate(configs, 1):
            self.report_lines.append(f"  CONFIG {i}: {config.get('name', 'unnamed')}")
            self.report_lines.append(f"    Тип: {config.get('type', 'N/A')}")
            self.report_lines.append(f"    Файл: {self._format_location(config.get('file_info', {}))}")
            self.report_lines.append("")
    
    def _print_all_functions(self):
        """Вывести ВСЕ функции"""
        behavioral = self.ast.get("enhanced_analysis", {}).get("behavioral_elements", {})
        functions = behavioral.get("functions", [])
        
        if not functions:
            self.report_lines.append("  Функции не найдены")
            return
        
        for i, func in enumerate(functions, 1):
            self.report_lines.append(f"  ФУНКЦИЯ {i}: {func.get('name', 'unnamed')}")
            self.report_lines.append(f"    Тип: {func.get('type', 'N/A')}")
            self.report_lines.append(f"    Файл: {self._format_location(func.get('file_info', {}))}")
            self.report_lines.append("")
    
    def _print_all_tasks(self):
        """Вывести ВСЕ задачи"""
        behavioral = self.ast.get("enhanced_analysis", {}).get("behavioral_elements", {})
        tasks = behavioral.get("tasks", [])
        
        if not tasks:
            self.report_lines.append("  Задачи не найдены")
            return
        
        for i, task in enumerate(tasks, 1):
            self.report_lines.append(f"  ЗАДАЧА {i}: {task.get('name', 'unnamed')}")
            self.report_lines.append(f"    Тип: {task.get('type', 'N/A')}")
            self.report_lines.append(f"    Файл: {self._format_location(task.get('file_info', {}))}")
            self.report_lines.append("")
    
    def _print_all_parameters(self):
        """Вывести ВСЕ параметры"""
        parameters_data = self.ast.get("enhanced_analysis", {}).get("parameters", {})
        
        parameters = parameters_data.get("parameters", [])
        defparams = parameters_data.get("defparams", [])
        defines = parameters_data.get("preprocessor_defines", [])
        
        if parameters:
            self.report_lines.append("  PARAMETERS:")
            for param in parameters:
                self.report_lines.append(f"    {param.get('name', 'unnamed')} = {param.get('value', '?')}")
        
        if defparams:
            self.report_lines.append("  DEFPARAMS:")
            for defparam in defparams:
                self.report_lines.append(f"    {defparam.get('name', 'unnamed')}")
        
        if defines:
            self.report_lines.append("  PREPROCESSOR DEFINES:")
            for define in defines:
                self.report_lines.append(f"    `define {define.get('name', 'unnamed')}")
    
    def _print_enhanced_fsm_analysis(self):
        """Расширенный анализ FSM с использованием логики FSMDetector"""
        modules = self.ast.get("modules", [])
        
        if not modules:
            self.report_lines.append("  Нет модулей для анализа FSM")
            return
        
        total_fsm_detected = 0
        
        for module in modules:
            module_name = module.get("name", "unnamed")
            self.report_lines.append(f"")
            self.report_lines.append(f"  МОДУЛЬ: {module_name}")
            self.report_lines.append(f"  {'='*40}")
            
            # Анализ FSM по логике FSMDetector
            fsm_analysis = self._analyze_module_fsm(module)
            
            if fsm_analysis["detected"]:
                total_fsm_detected += 1
                self.report_lines.append(f"    FSM ОБНАРУЖЕН: ДА")
                self.report_lines.append(f"    Тип FSM: {fsm_analysis['type']}")
                
                # State переменные
                state_vars = fsm_analysis["state_variables"]
                if state_vars:
                    self.report_lines.append(f"    State переменные ({len(state_vars)}):")
                    for var in state_vars:
                        self.report_lines.append(f"      - {var['name']} ({var['type']}, {var.get('width', 'N/A')})")
                
                # Состояния
                states = fsm_analysis["states"]
                if states:
                    self.report_lines.append(f"    Состояния FSM ({len(states)}):")
                    for state in states:
                        self.report_lines.append(f"      - {state['name']} ({state['type']}, источник: {state['source']})")
                
                # Переходы
                transitions = fsm_analysis["transitions"]
                if transitions:
                    self.report_lines.append(f"    Переходы ({len(transitions)}):")
                    for trans in transitions:
                        self.report_lines.append(f"      {trans['from_state']} -> {trans['to_state']} [условие: {trans['condition']}]")
                
                # Clock/Reset
                if fsm_analysis["clock_signal"]:
                    self.report_lines.append(f"    Тактовый сигнал: {fsm_analysis['clock_signal']}")
                if fsm_analysis["reset_condition"]:
                    self.report_lines.append(f"    Сброс: {fsm_analysis['reset_condition']}")
            else:
                self.report_lines.append(f"    FSM ОБНАРУЖЕН: НЕТ")
                # Показываем почему не обнаружен
                state_vars = self._find_state_variables(module)
                if not state_vars:
                    self.report_lines.append(f"    Причина: не найдены state переменные")
                else:
                    self.report_lines.append(f"    Найдены state переменные ({len(state_vars)}), но недостаточно данных для FSM")
                    for var in state_vars:
                        self.report_lines.append(f"      - {var['name']}")
        
        self.report_lines.append(f"")
        self.report_lines.append(f"  ВСЕГО МОДУЛЕЙ С FSM: {total_fsm_detected} из {len(modules)}")
    
    def _analyze_module_fsm(self, module: Dict[str, Any]) -> Dict[str, Any]:
        """Анализ FSM модуля по логике FSMDetector"""
        fsm_info = {
            "detected": False,
            "type": "unknown",
            "state_variables": [],
            "states": [],
            "transitions": [],
            "clock_signal": "",
            "reset_condition": ""
        }
        
        # 1. Поиск state переменных
        state_vars = self._find_state_variables(module)
        if not state_vars:
            return fsm_info
        
        fsm_info["state_variables"] = state_vars
        fsm_info["detected"] = True
        
        # 2. Определение типа FSM
        fsm_info["type"] = self._determine_fsm_type(module, state_vars)
        
        # 3. Извлечение состояний
        states = self._extract_fsm_states(module, state_vars)
        fsm_info["states"] = states
        
        # 4. Извлечение переходов
        transitions = self._extract_transitions(module, state_vars, states)
        fsm_info["transitions"] = transitions
        
        # 5. Поиск clock/reset
        clock, reset = self._find_clock_reset(module)
        fsm_info["clock_signal"] = clock
        fsm_info["reset_condition"] = reset
        
        return fsm_info
    
    def _find_state_variables(self, module: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Поиск state переменных как в FSMDetector"""
        state_vars = []
        
        for signal in module.get("signals", []) or []:
            if not isinstance(signal, dict):
                continue
            
            name = signal.get("name", "").lower()
            original_name = signal.get("name", "")
            
            # Проверка паттернов state переменных
            matched_pattern = None
            for pattern in self.fsm_patterns["state_variables"]:
                if pattern in name:
                    matched_pattern = pattern
                    break
            
            # Проверка префиксов
            matched_prefix = None
            if not matched_pattern:
                for prefix in self.fsm_patterns["state_enum_prefixes"]:
                    if name.startswith(prefix):
                        matched_prefix = prefix
                        break
            
            if matched_pattern or matched_prefix:
                state_vars.append({
                    "name": original_name,
                    "type": "signal",
                    "width": signal.get("width", ""),
                    "pattern_match": matched_pattern or f"prefix_{matched_prefix}"
                })
        
        return state_vars
    
    def _determine_fsm_type(self, module: Dict[str, Any], state_vars: List[Dict]) -> str:
        """Определение типа FSM"""
        always_blocks = module.get("always_blocks", [])
        
        has_sequential = False
        has_combinational = False
        
        for block in always_blocks:
            sensitivity = str(block.get("sensitivity", "")).lower()
            
            # Проверка на sequential логику
            if any(p in sensitivity for p in ["posedge", "negedge"]):
                has_sequential = True
            
            # Проверка на combinational логику
            if sensitivity == "@*" or "always_comb" in sensitivity:
                has_combinational = True
        
        if has_sequential and has_combinational:
            return "mealy"
        elif has_sequential:
            return "moore"
        elif has_combinational:
            return "combinational"
        else:
            return "unknown"
    
    def _extract_fsm_states(self, module: Dict[str, Any], state_vars: List[Dict]) -> List[Dict[str, Any]]:
        """Извлечение состояний FSM по логике FSMDetector"""
        states = []
        
        # 1. Из fsm_states (от CompleteASTService)
        fsm_states = module.get("fsm_states", [])
        for st in fsm_states:
            if isinstance(st, dict) and st.get("name"):
                states.append({
                    "name": st["name"],
                    "type": "enum_member",
                    "source": st.get("source", "enum"),
                    "enum": st.get("enum", "")
                })
        
        # 2. Из enums модуля
        enums = module.get("enums", [])
        for enum in enums:
            if isinstance(enum, dict):
                enum_name = enum.get("name", "anonymous_enum")
                members = enum.get("members", [])
                for member in members:
                    states.append({
                        "name": member,
                        "type": "enum_member", 
                        "source": "enum",
                        "enum": enum_name
                    })
        
        # 3. Из сигналов с state ключевыми словами
        for signal in module.get("signals", []) or []:
            if not isinstance(signal, dict):
                continue
            
            signal_name = signal.get("name", "")
            for keyword in self.fsm_patterns["state_keywords"]:
                if keyword.upper() == signal_name.upper():
                    states.append({
                        "name": signal_name,
                        "type": "state_signal",
                        "source": "signal_keyword"
                    })
                    break
        
        # 4. Из параметров
        for param in module.get("parameters", []) or []:
            if not isinstance(param, dict):
                continue
            
            param_name = param.get("name", "")
            for keyword in self.fsm_patterns["state_keywords"]:
                if keyword.upper() in param_name.upper():
                    states.append({
                        "name": param_name,
                        "type": "parameter",
                        "source": "parameter",
                        "value": param.get("value", "")
                    })
                    break
        
        # Дедупликация
        seen = set()
        unique_states = []
        for state in states:
            if state["name"] not in seen:
                seen.add(state["name"])
                unique_states.append(state)
        
        return unique_states
    
    def _extract_transitions(self, module: Dict[str, Any], state_vars: List[Dict], states: List[Dict]) -> List[Dict[str, Any]]:
        """Извлечение переходов между состояниями"""
        transitions = []
        state_names = {st["name"] for st in states}
        
        for block in module.get("always_blocks", []) or []:
            if not isinstance(block, dict):
                continue
            
            sensitivity = str(block.get("sensitivity", "")).lower()
            is_clocked = any(p in sensitivity for p in ["posedge", "negedge"])
            
            for assign in block.get("assignments", []) or []:
                if not isinstance(assign, dict):
                    continue
                
                left_var = assign.get("left", "")
                right_expr = assign.get("right", "")
                
                # Проверяем, присваиваем ли state переменную
                is_state_assignment = any(
                    var["name"].lower() in left_var.lower() 
                    for var in state_vars
                )
                
                if is_state_assignment:
                    # Ищем состояние в правой части
                    to_state = self._find_state_in_expression(right_expr, state_names)
                    from_state = "current_state" if is_clocked else "any_state"
                    
                    condition = "clock_edge" if is_clocked else "combinational"
                    
                    transitions.append({
                        "from_state": from_state,
                        "to_state": to_state,
                        "condition": condition,
                        "type": "clocked" if is_clocked else "combinational",
                        "assignment": f"{left_var} = {right_expr}"
                    })
        
        return transitions
    
    def _find_state_in_expression(self, expression: str, state_names: Set[str]) -> str:
        """Найти состояние в выражении"""
        expr_upper = expression.upper()
        
        for state_name in state_names:
            if state_name.upper() in expr_upper:
                return state_name
        
        return "unknown_state"
    
    def _find_clock_reset(self, module: Dict[str, Any]) -> tuple[str, str]:
        """Поиск clock и reset сигналов"""
        clock_signal = ""
        reset_condition = ""
        
        for block in module.get("always_blocks", []) or []:
            if not isinstance(block, dict):
                continue
            
            sensitivity = str(block.get("sensitivity", "")).lower()
            
            # Поиск clock
            if "posedge" in sensitivity or "negedge" in sensitivity:
                parts = sensitivity.split()
                for i, part in enumerate(parts):
                    if part in ["posedge", "negedge"] and i + 1 < len(parts):
                        candidate = parts[i + 1]
                        if any(p in candidate for p in ["clk", "clock"]):
                            clock_signal = candidate
                            break
            
            # Поиск reset
            if any(p in sensitivity for p in ["rst", "reset"]):
                reset_condition = "asynchronous_reset"
        
        return clock_signal, reset_condition
    
    def _print_connection_graph(self):
        """Вывести граф соединений"""
        connection_graph = self.ast.get("enhanced_analysis", {}).get("connection_graph", {})
        
        if not connection_graph:
            self.report_lines.append("  Граф соединений не построен")
            return
        
        nodes = connection_graph.get("nodes", [])
        edges = connection_graph.get("edges", [])
        
        self.report_lines.append(f"  Узлов: {len(nodes)}")
        self.report_lines.append(f"  Рёбер: {len(edges)}")
        
        if edges:
            self.report_lines.append("  СОЕДИНЕНИЯ:")
            for edge in edges:
                source = edge.get("source", "?")
                target = edge.get("target", "?")
                instance = edge.get("instance_name", "?")
                self.report_lines.append(f"    {source} --[{instance}]--> {target}")
    
    def _print_hierarchies(self):
        """Вывести иерархии модулей"""
        hierarchies = self.ast.get("enhanced_analysis", {}).get("hierarchies", [])
        
        if not hierarchies:
            self.report_lines.append("  Иерархии не построены")
            return
        
        self.report_lines.append(f"  Деревьев иерархии: {len(hierarchies)}")
        
        for i, hierarchy in enumerate(hierarchies, 1):
            self.report_lines.append(f"  Дерево {i}:")
            self._print_hierarchy_tree(hierarchy)
    
    def _print_hierarchy_tree(self, node: Dict, level: int = 0):
        """Рекурсивно напечатать дерево иерархии"""
        indent = "    " + "  " * level
        node_name = node.get("name", "?")
        node_type = node.get("type", "")
        instance_count = node.get("instance_count", 0)
        cycle = " [ЦИКЛ]" if node.get("cycle") else ""
        
        line = f"{indent}{node_name}"
        if node_type:
            line += f" ({node_type})"
        if instance_count > 0:
            line += f" [{instance_count} inst]"
        line += cycle
        
        self.report_lines.append(line)
        
        for child in node.get("children", []):
            self._print_hierarchy_tree(child, level + 1)
    
    def _print_timing_analysis(self):
        """Вывести анализ тайминга"""
        timing_analysis = self.ast.get("enhanced_analysis", {}).get("timing_analysis", {})
        
        if not timing_analysis:
            self.report_lines.append("  Тайминг анализ не выполнен")
            return
        
        clock_domains = timing_analysis.get("clock_domains", [])
        timing_info = timing_analysis.get("timing_info", {})
        
        self.report_lines.append(f"  Синхронных модулей: {timing_info.get('synchronous_modules', 0)}")
        self.report_lines.append(f"  Комбинационных модулей: {timing_info.get('combinational_modules', 0)}")
        self.report_lines.append(f"  Смешанных модулей: {timing_info.get('mixed_modules', 0)}")
        
        if clock_domains:
            self.report_lines.append("  ТАКТОВЫЕ ДОМЕНЫ:")
            for cd in clock_domains:
                module = cd.get("module", "?")
                clocks = cd.get("clocks", [])
                module_type = cd.get("type", "?")
                self.report_lines.append(f"    {module}: {module_type} ({', '.join(clocks)})")
    
    def _print_reset_analysis(self):
        """Вывести анализ сигналов сброса"""
        reset_analysis = self.ast.get("enhanced_analysis", {}).get("timing_analysis", {}).get("reset_analysis", [])
        
        if not reset_analysis:
            self.report_lines.append("  Сигналы сброса не найдены")
            return
        
        self.report_lines.append("  СИГНАЛЫ СБРОСА:")
        for reset_info in reset_analysis:
            module = reset_info.get("module", "?")
            reset_signals = reset_info.get("reset_signals", [])
            reset_type = reset_info.get("reset_type", "?")
            self.report_lines.append(f"    {module}: {reset_type} ({', '.join(reset_signals)})")
    
    def _print_assignment_analysis(self):
        """Вывести анализ присваиваний"""
        assignment_analysis = self.ast.get("enhanced_analysis", {}).get("timing_analysis", {}).get("assignment_analysis", {})
        
        if not assignment_analysis:
            self.report_lines.append("  Анализ присваиваний не выполнен")
            return
        
        continuous = assignment_analysis.get("continuous_assignments", 0)
        modules_with_assigns = assignment_analysis.get("modules_with_assignments", [])
        
        self.report_lines.append(f"  Непрерывных assign'ов: {continuous}")
        self.report_lines.append(f"  Модулей с assign'ами: {len(modules_with_assigns)}")
        
        for module_assign in modules_with_assigns:
            module = module_assign.get("module", "?")
            continuous_count = module_assign.get("continuous", 0)
            self.report_lines.append(f"    {module}: {continuous_count} assign'ов")
    
    def _format_location(self, location: Dict) -> str:
        """Форматировать информацию о расположении"""
        if not location:
            return "N/A"
        
        start_line = location.get("start_line", 0)
        start_col = location.get("start_column", 0)
        end_line = location.get("end_line", 0)
        end_col = location.get("end_column", 0)
        
        if start_line > 0:
            if end_line > start_line:
                return f"строки {start_line}-{end_line}"
            else:
                return f"строка {start_line}"
        else:
            return "N/A"
    
    def _find_modules_using_enum(self, enum_name: str, enum_members: List[str]) -> List[str]:
        """Найти модули, которые используют указанный enum"""
        using_modules = []
        
        for module in self.ast.get("modules", []):
            module_name = module.get("name", "")
            
            # Проверяем сигналы модуля на совпадение с элементами enum
            signals = module.get("signals", [])
            for signal in signals:
                signal_name = signal.get("name", "")
                if signal_name in enum_members:
                    using_modules.append(module_name)
                    break
            
            # Проверяем наличие enum в модуле
            module_enums = module.get("enums", [])
            for module_enum in module_enums:
                if module_enum.get("name") == enum_name:
                    using_modules.append(module_name)
                    break
        
        return list(set(using_modules))
    
    def _save_report_to_file(self, report_text: str, output_file: str):
        """Сохранить отчет в файл"""
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            
            print(f"Отчет сохранен в: {output_path}")
        except Exception as e:
            print(f"Ошибка сохранения отчета: {e}")


# =========================
# ФУНКЦИИ ДЛЯ БЫСТРОГО ИСПОЛЬЗОВАНИЯ
# =========================

def generate_complete_analysis_report(ast_data: Dict[str, Any], 
                                    output_file: str = None,
                                    console_output: bool = True) -> str:
    """
    Сгенерировать ПОЛНЫЙ отчет анализа AST
    
    Args:
        ast_data: Данные AST
        output_file: Путь для сохранения отчета (опционально)
        console_output: Выводить ли отчет в консоль
    
    Returns:
        Текст отчета
    """
    reporter = CompleteASTAnalysisReport(ast_data)
    report = reporter.generate_complete_report(output_file)
    
    if console_output:
        print(report)
    
    return report


def save_ast_json(ast_data: Dict[str, Any], output_file: str = "ast_complete.json"):
    """
    Сохранить полные данные AST в JSON файл
    """
    try:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(ast_data, f, ensure_ascii=False, indent=2)
        
        print(f"Полные данные AST сохранены в: {output_path}")
    except Exception as e:
        print(f"Ошибка сохранения AST JSON: {e}")


# =========================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# =========================

def example_usage():
    """Пример использования полного анализатора"""
    
    # Пример данных AST (замените на реальные данные из вашего сервиса)
    example_ast = {
        "type": "CompleteAST",
        "parser_used": "pyslang_enhanced",
        "version": "1.0",
        "modules": [
            {
                "name": "detect_4_bit_sequence_using_fsm",
                "ports": [
                    {"name": "clk", "direction": "input", "width": ""},
                    {"name": "rst", "direction": "input", "width": ""},
                    {"name": "a", "direction": "input", "width": ""},
                    {"name": "detected", "direction": "output", "width": ""}
                ],
                "signals": [
                    {"name": "state", "type": "reg", "width": "[2:0]"},
                    {"name": "new_state", "type": "reg", "width": "[2:0]"},
                    {"name": "IDLE", "type": "parameter", "width": ""},
                    {"name": "F1", "type": "parameter", "width": ""},
                    {"name": "F0", "type": "parameter", "width": ""},
                    {"name": "S1", "type": "parameter", "width": ""},
                    {"name": "S0", "type": "parameter", "width": ""}
                ],
                "always_blocks": [
                    {
                        "sensitivity": "posedge clk",
                        "assignments": [
                            {"left": "state", "right": "new_state", "line": 1, "op": "<="}
                        ]
                    }
                ],
                "assigns": [
                    {"left": "detected", "right": "state == S0", "line": 1, "op": "="}
                ],
                "fsm_states": [
                    {"name": "IDLE", "enum": "StateEnum", "source": "enum"},
                    {"name": "F1", "enum": "StateEnum", "source": "enum"},
                    {"name": "F0", "enum": "StateEnum", "source": "enum"},
                    {"name": "S1", "enum": "StateEnum", "source": "enum"},
                    {"name": "S0", "enum": "StateEnum", "source": "enum"}
                ]
            }
        ],
        "enhanced_analysis": {
            "data_types": {
                "enums": [
                    {
                        "name": "StateEnum",
                        "members": ["IDLE", "F1", "F0", "S1", "S0"],
                        "file_info": {"start_line": 10, "end_line": 15}
                    }
                ]
            }
        },
        "metadata": {
            "total_modules_enhanced": 2,
            "total_enums": 1,
            "total_typedefs": 0
        }
    }
    
    # Генерация полного отчета
    report = generate_complete_analysis_report(
        example_ast, 
        output_file="complete_analysis_report.txt",
        console_output=True
    )
    
    # Сохранение полных данных AST
    save_ast_json(example_ast, "complete_ast_data.json")
    
    return report


if __name__ == "__main__":
    example_usage()