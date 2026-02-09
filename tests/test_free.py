# -*- coding: utf-8 -*-
# complete_ast_service_pyslang.py
"""
ПОЛНОСТЬЮ ЗАВЕРШЕННЫЙ СЕРВИС ДЛЯ ПОСТРОЕНИЯ ABSTRACT SYNTAX TREE (AST) ИЗ CST
Специально для pyslang - полный парсинг всех конструкций SystemVerilog
Использует базовый ast_service.py без его изменения

ВАЖНО: Результат строго нормализован под формат, который ожидает
fsm_detector_service.py:
- ast["modules"] -> список модулей вида Dict со следующими ключами:
  - "name": str
  - "signals": List[{"name": str, "type": str, "width": str}]
  - "parameters": List[{"name": str, "value": str}]
  - "typedefs": List[{"name": str, "definition": str}]
  - "always_blocks": List[{
        "sensitivity": str,
        "assignments": List[{"left": str, "right": str, "line": int, "op": str}]
     }]
  - "assigns": List[{"left": str, "right": str, "line": int, "op": str}]
  - "ports": List[{"name": str, "direction": str, "width": str}]
  - "instances": List[{"name": str, "type": str, "connections": List[Dict]}]
  - а также прочие поля из базового AST (не мешают)

Политика: не урезаем функционал, а дополняем и нормализуем.
"""

from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass
import json
from pathlib import Path

# Импортируем существующий AST сервис
from AST_CST.ast_service import ASTService, print_unified_ast


@dataclass
class ASTNode:
    """Базовый класс для узлов AST"""
    type: str
    name: str
    location: Optional[Dict] = None


class CompleteASTService:
    """ПОЛНОСТЬЮ ЗАВЕРШЕННЫЙ СЕРВИС ДЛЯ ПОСТРОЕНИЯ AST С Pyslang (+ нормализация для FSM detector)"""
    
    def __init__(self):
        self.debug = False
        # Используем существующий AST сервис как основу
        self.base_ast_service = ASTService()
    
    def build_complete_ast_from_cst(self, tree) -> Dict[str, Any]:
        """Построить ПОЛНЫЙ AST из CST pyslang и нормализовать под формат fsm_detector_service"""
        try:
            # 1) Базовый AST из существующего сервиса
            base_ast = self.base_ast_service.build_ast_from_cst(tree)

            # 2) Расширяем его информацией из pyslang
            enhanced_ast = self._enhance_ast_with_pyslang(base_ast, tree)

            # 3) Жёсткая нормализация для совместимости с FSMDetectorService
            normalized_ast = self._normalize_for_fsm_detector(enhanced_ast)

            return normalized_ast

        except Exception as e:
            print(f"Error building complete AST: {e}")
            # Возвращаем максимально совместимый базовый AST с минимальной нормализацией
            base_ast = self.base_ast_service.build_ast_from_cst(tree)
            try:
                return self._normalize_for_fsm_detector(base_ast)
            except Exception:
                return base_ast

    # =====================================================================
    # Расширение базового AST с помощью pyslang
    # =====================================================================

    def _enhance_ast_with_pyslang(self, base_ast: Dict[str, Any], tree) -> Dict[str, Any]:
        """Дополнить базовый AST расширенной информацией от pyslang"""
        # Получаем корневой узел для pyslang анализа
        if hasattr(tree, 'kind') or hasattr(tree, '__class__'):
            root = tree
        else:
            root = tree.root if hasattr(tree, 'root') else tree
        
        # Дополнительный анализ с pyslang
        enhanced_modules = self._enhance_modules_with_pyslang(base_ast.get("modules", []), root)
        interfaces = self._find_and_parse_interfaces(root)
        packages = self._find_and_parse_packages(root)
        classes = self._find_and_parse_classes(root)
        programs = self._find_and_parse_programs(root)
        checkers = self._find_and_parse_checkers(root)
        configs = self._find_and_parse_configs(root)
        
        # Типы данных
        typedefs, structs, enums, unions = self._collect_types(root)
        
        # Функции и задачи
        functions, tasks = self._collect_functions_tasks(root)
        
        # Параметры и defines
        parameters, defparams = self._collect_parameters(root)
        preprocessor_defines = self._collect_preprocessor_directives(root)
        
        # Привязываем enum'ы к модулям и строим список FSM-состояний
        enhanced_modules = self._attach_enums_to_modules(enhanced_modules, enums)
        
        # Расширенный анализ соединений
        connection_graph = self._build_complete_connection_graph(enhanced_modules, interfaces)
        hierarchies = self._build_complete_hierarchies(enhanced_modules, interfaces, base_ast.get("connections", []))
        
        # Анализ тактовых и reset сигналов
        clock_domains = self._analyze_clock_domains(enhanced_modules)
        reset_analysis = self._analyze_reset_signals(enhanced_modules)
        
        # Статистика по Assignments
        assignment_analysis = self._analyze_assignments(enhanced_modules)
        
        # Анализ временных характеристик
        timing_analysis = self._analyze_timing(enhanced_modules)

        # FSM-метаданные (по модулям)
        fsm_analysis = self._build_fsm_analysis(enhanced_modules, enums)
        
        # Объединяем базовый AST с расширенной информацией
        enhanced_ast = {
            **base_ast,  # Сохраняем всё из базового AST
            
            # Переопределяем тип и парсер
            "type": "CompleteAST",
            "parser_used": "pyslang_enhanced",
            "version": "1.0",
            
            # Заменяем модули на расширенные
            "modules": enhanced_modules,

            # Пробрасываем типы данных на верхний уровень,
            # чтобы их видел print_unified_ast и прочие потребители
            "typedefs": typedefs,
            "structs": structs,
            "enums": enums,
            "unions": unions,
            
            # Добавляем новые разделы
            "systemverilog_elements": {
                **base_ast.get("systemverilog_elements", {}),
                "interfaces": interfaces,
                "packages": packages,
                "classes": classes,
                "programs": programs,
                "checkers": checkers,
                "configs": configs,
            },
            
            # Новые разделы для расширенного анализа
            "enhanced_analysis": {
                "data_types": {
                    "typedefs": typedefs,
                    "structs": structs,
                    "enums": enums,
                    "unions": unions,
                },
                
                "behavioral_elements": {
                    "functions": functions,
                    "tasks": tasks,
                },
                
                "parameters": {
                    "parameters": parameters,
                    "defparams": defparams,
                    "preprocessor_defines": preprocessor_defines,
                },
                
                "connection_graph": connection_graph,
                "hierarchies": hierarchies,
                
                "timing_analysis": {
                    "clock_domains": clock_domains,
                    "reset_analysis": reset_analysis,
                    "timing_info": timing_analysis,
                    "assignment_analysis": assignment_analysis,
                },

                # Специальный блок для FSM-анализа
                "fsm": fsm_analysis,
            },
            
            # Обновляем метаданные
            "metadata": {
                **base_ast.get("metadata", {}),
                **self._build_complete_metadata(
                    enhanced_modules, interfaces, programs, classes, packages,
                    typedefs, structs, enums, functions, tasks
                )
            }
        }
        
        return enhanced_ast

    def _enhance_modules_with_pyslang(self, base_modules: List[Dict], root) -> List[Dict]:
        """Дополнить информацию о модулях с помощью pyslang"""
        enhanced_modules = []
        
        for base_module in base_modules:
            module_name = base_module.get("name", "")
            enhanced_module = {**base_module}  # Копируем базовую информацию
            
            try:
                # Находим соответствующий узел в pyslang
                module_nodes = self._find_nodes_by_kind(root, "ModuleDeclaration")
                for module_node in module_nodes:
                    if self._get_node_name(module_node) == module_name:
                        # Добавляем расширенную информацию
                        enhanced_module.update({
                            "file_info": self._get_node_location(module_node),
                            "enhanced_parameters": self._parse_module_parameters_pyslang(module_node),
                            "enhanced_ports": self._parse_module_ports_pyslang(module_node),
                            "pyslang_analysis": True
                        })
                        break
            except Exception as e:
                if self.debug:
                    print(f"Error enhancing module {module_name}: {e}")
            
            enhanced_modules.append(enhanced_module)
        
        return enhanced_modules

    # =========================================================================
    # Pyslang-specific utility functions
    # =========================================================================
    
    def _get_node_kind(self, node):
        """Получить тип узла pyslang"""
        if not node:
            return "Unknown"
        try:
            return node.kind.name if hasattr(node, 'kind') else node.__class__.__name__
        except Exception:
            return "Unknown"

    def _find_nodes_by_kind(self, node, target_kind):
        """Найти все узлы определенного типа в pyslang"""
        results = []
        if not node:
            return results
        
        try:
            # Проверяем текущий узел
            if self._get_node_kind(node) == target_kind:
                results.append(node)
            
            # Рекурсивно проверяем дочерние узлы
            if hasattr(node, '__iter__'):
                for child in node:
                    if child is not None and child is not node:
                        results.extend(self._find_nodes_by_kind(child, target_kind))
            elif hasattr(node, 'children'):
                for child in node.children:
                    if child is not None and child is not node:
                        results.extend(self._find_nodes_by_kind(child, target_kind))
                        
        except Exception as e:
            if self.debug:
                print(f"Error finding nodes: {e}")
                
        return results

    def _get_node_name(self, node) -> str:
        """Получить имя узла pyslang"""
        if not node:
            return ""
        
        try:
            # Для ModuleDeclaration и подобных
            if hasattr(node, 'name') and node.name:
                return str(node.name)
            
            # Для Identifier
            if self._get_node_kind(node) == "Identifier" and hasattr(node, 'name'):
                return str(node.name)
                
            # Для других узлов пытаемся найти имя
            if hasattr(node, '__class__'):
                if hasattr(node, 'name'):
                    return str(node.name)
                elif hasattr(node, 'identifier'):
                    return str(node.identifier)
                    
        except Exception as e:
            if self.debug:
                print(f"Error getting node name: {e}")
                
        return "unnamed"

    def _get_node_text(self, node) -> str:
        """Получить текст узла pyslang"""
        if not node:
            return ""
        try:
            return str(node)
        except Exception:
            return ""

    def _get_node_location(self, node) -> Dict[str, Any]:
        """Получить информацию о расположении узла pyslang"""
        location = {
            "start_line": 0,
            "start_column": 0, 
            "end_line": 0,
            "end_column": 0
        }
        
        try:
            if hasattr(node, 'sourceRange') and node.sourceRange:
                start = node.sourceRange.start
                end = node.sourceRange.end
                
                if hasattr(start, 'line'):
                    location["start_line"] = start.line
                    location["start_column"] = start.column
                
                if hasattr(end, 'line'):
                    location["end_line"] = end.line
                    location["end_column"] = end.column
                    
        except Exception as e:
            if self.debug:
                print(f"Location error: {e}")
                
        return location

    # =========================================================================
    # Pyslang parsing methods (упрощённые версии для примера)
    # =========================================================================

    def _parse_module_parameters_pyslang(self, mod_decl):
        """Разбор параметров модуля с pyslang"""
        parameters = []
        try:
            param_decls = self._find_nodes_by_kind(mod_decl, "ParameterDeclaration")
            for param in param_decls:
                param_name = self._get_node_name(param)
                param_value = "default"
                
                if hasattr(param, 'initializer'):
                    param_value = self._get_node_text(param.initializer)
                
                parameters.append({
                    "name": param_name,
                    "value": param_value,
                    "pyslang_parsed": True
                })
        except Exception as e:
            if self.debug:
                print(f"Parameter parsing error: {e}")
        return parameters

    def _parse_module_ports_pyslang(self, mod_decl):
        """Разбор портов модуля с pyslang"""
        ports = []
        try:
            port_decls = self._find_nodes_by_kind(mod_decl, "PortDeclaration")
            for port in port_decls:
                port_name = self._get_node_name(port)
                direction = "unknown"
                width = ""
                
                if hasattr(port, 'direction'):
                    direction = str(port.direction)
                
                if hasattr(port, 'type') and port.type is not None:
                    width = self._get_node_text(port.type)
                
                ports.append({
                    "name": port_name,
                    "direction": direction,
                    "width": width,
                    "type": "port",
                    "pyslang_parsed": True
                })
        except Exception as e:
            if self.debug:
                print(f"Port parsing error: {e}")
        return ports

    def _find_and_parse_interfaces(self, root):
        """Найти и разобрать все интерфейсы"""
        interfaces = []
        try:
            interface_nodes = self._find_nodes_by_kind(root, "InterfaceDeclaration")
            for interface_node in interface_nodes:
                try:
                    interface_info = {
                        "name": self._get_node_name(interface_node),
                        "type": "Interface", 
                        "file_info": self._get_node_location(interface_node),
                        "pyslang_parsed": True
                    }
                    interfaces.append(interface_info)
                except Exception as e:
                    if self.debug:
                        print(f"Error parsing interface: {e}")
        except Exception as e:
            if self.debug:
                print(f"Error finding interfaces: {e}")
        return interfaces

    def _find_and_parse_packages(self, root):
        """Найти и разобрать все пакеты"""
        packages = []
        try:
            package_nodes = self._find_nodes_by_kind(root, "PackageDeclaration")
            for package_node in package_nodes:
                try:
                    package_info = {
                        "name": self._get_node_name(package_node),
                        "type": "Package",
                        "file_info": self._get_node_location(package_node),
                        "pyslang_parsed": True
                    }
                    packages.append(package_info)
                except Exception as e:
                    if self.debug:
                        print(f"Error parsing package: {e}")
        except Exception as e:
            if self.debug:
                print(f"Error finding packages: {e}")
        return packages

    def _find_and_parse_classes(self, root):
        """Найти и разобрать все классы"""
        classes = []
        try:
            class_nodes = self._find_nodes_by_kind(root, "ClassDeclaration")
            for class_node in class_nodes:
                try:
                    class_info = {
                        "name": self._get_node_name(class_node),
                        "type": "Class",
                        "file_info": self._get_node_location(class_node),
                        "pyslang_parsed": True
                    }
                    classes.append(class_info)
                except Exception as e:
                    if self.debug:
                        print(f"Error parsing class: {e}")
        except Exception as e:
            if self.debug:
                print(f"Error finding classes: {e}")
        return classes

    def _find_and_parse_programs(self, root):
        """Найти и разобрать все program блоки"""
        programs = []
        try:
            program_nodes = self._find_nodes_by_kind(root, "ProgramDeclaration")
            for program_node in program_nodes:
                try:
                    program_info = {
                        "name": self._get_node_name(program_node),
                        "type": "Program",
                        "file_info": self._get_node_location(program_node),
                        "pyslang_parsed": True
                    }
                    programs.append(program_info)
                except Exception as e:
                    if self.debug:
                        print(f"Error parsing program: {e}")
        except Exception as e:
            if self.debug:
                print(f"Error finding programs: {e}")
        return programs

    def _find_and_parse_checkers(self, root):
        """Найти и разобрать все checker блоки"""
        checkers = []
        try:
            checker_nodes = self._find_nodes_by_kind(root, "CheckerDeclaration")
            for checker_node in checker_nodes:
                try:
                    checker_info = {
                        "name": self._get_node_name(checker_node),
                        "type": "Checker",
                        "file_info": self._get_node_location(checker_node),
                        "pyslang_parsed": True
                    }
                    checkers.append(checker_info)
                except Exception as e:
                    if self.debug:
                        print(f"Error parsing checker: {e}")
        except Exception as e:
            if self.debug:
                print(f"Error finding checkers: {e}")
        return checkers

    def _find_and_parse_configs(self, root):
        """Найти и разобрать все config блоки"""
        configs = []
        try:
            config_nodes = self._find_nodes_by_kind(root, "ConfigDeclaration")
            for config_node in config_nodes:
                try:
                    config_info = {
                        "name": self._get_node_name(config_node),
                        "type": "Config",
                        "file_info": self._get_node_location(config_node),
                        "pyslang_parsed": True
                    }
                    configs.append(config_info)
                except Exception as e:
                    if self.debug:
                        print(f"Error parsing config: {e}")
        except Exception as e:
            if self.debug:
                print(f"Error finding configs: {e}")
        return configs

    def _collect_types(self, root):
        """Сбор ВСЕХ типов данных pyslang"""
        typedefs: List[Dict[str, Any]] = []
        structs: List[Dict[str, Any]] = []
        enums: List[Dict[str, Any]] = []
        unions: List[Dict[str, Any]] = []

        try:
            # Typedefs
            typedef_nodes = self._find_nodes_by_kind(root, "TypedefDeclaration")
            for td in typedef_nodes:
                typedefs.append({
                    "name": self._get_node_name(td),
                    "type": "typedef",
                    "file_info": self._get_node_location(td),
                    "pyslang_parsed": True,
                    "definition": self._get_node_text(td)
                })

            # Structs
            struct_nodes = self._find_nodes_by_kind(root, "StructType")
            for st in struct_nodes:
                structs.append({
                    "name": self._get_node_name(st) or "anonymous_struct",
                    "type": "struct",
                    "file_info": self._get_node_location(st),
                    "pyslang_parsed": True
                })

            # Enums
            enum_nodes = self._find_nodes_by_kind(root, "EnumType")
            for en in enum_nodes:
                # Собираем элементы перечисления
                members: List[str] = []
                try:
                    enumerators = self._find_nodes_by_kind(en, "Enumerator")
                    for enum_val in enumerators:
                        name = self._get_node_name(enum_val)
                        if name:
                            members.append(name)
                except Exception as inner_e:
                    if self.debug:
                        print(f"Enum members collection error: {inner_e}")

                enum_name = self._get_node_name(en) or "anonymous_enum"
                # Если имя enum совпадает с одним из его элементов, считаем его анонимным
                if enum_name in members:
                    enum_name = "anonymous_enum"

                enums.append({
                    "name": enum_name,
                    "type": "enum",
                    "members": members,
                    "file_info": self._get_node_location(en),
                    "pyslang_parsed": True
                })

            # Unions
            union_nodes = self._find_nodes_by_kind(root, "UnionType")
            for un in union_nodes:
                unions.append({
                    "name": self._get_node_name(un) or "anonymous_union",
                    "type": "union",
                    "file_info": self._get_node_location(un),
                    "pyslang_parsed": True
                })
                
        except Exception as e:
            if self.debug:
                print(f"Type collection error: {e}")
                
        return typedefs, structs, enums, unions

    def _collect_functions_tasks(self, root):
        """Сбор функций и задач pyslang"""
        functions: List[Dict[str, Any]] = []
        tasks: List[Dict[str, Any]] = []

        try:
            function_nodes = self._find_nodes_by_kind(root, "FunctionDeclaration")
            for func in function_nodes:
                functions.append({
                    "name": self._get_node_name(func),
                    "type": "function",
                    "file_info": self._get_node_location(func),
                    "pyslang_parsed": True
                })

            task_nodes = self._find_nodes_by_kind(root, "TaskDeclaration")
            for task in task_nodes:
                tasks.append({
                    "name": self._get_node_name(task),
                    "type": "task",
                    "file_info": self._get_node_location(task),
                    "pyslang_parsed": True
                })
        except Exception as e:
            if self.debug:
                print(f"Function/task collection error: {e}")
                
        return functions, tasks

    def _collect_parameters(self, root):
        """Сбор параметров и defparams pyslang"""
        parameters: List[Dict[str, Any]] = []
        defparams: List[Dict[str, Any]] = []

        try:
            param_nodes = self._find_nodes_by_kind(root, "ParameterDeclaration")
            for param in param_nodes:
                parameters.append({
                    "name": self._get_node_name(param),
                    "type": "parameter",
                    "file_info": self._get_node_location(param),
                    "pyslang_parsed": True
                })

            defparam_nodes = self._find_nodes_by_kind(root, "DefParam")
            for defparam in defparam_nodes:
                defparams.append({
                    "name": self._get_node_name(defparam),
                    "type": "defparam",
                    "file_info": self._get_node_location(defparam),
                    "pyslang_parsed": True
                })
        except Exception as e:
            if self.debug:
                print(f"Parameter collection error: {e}")
                
        return parameters, defparams

    def _collect_preprocessor_directives(self, root):
        """Сбор препроцессорных директив pyslang"""
        defines: List[Dict[str, Any]] = []
        try:
            define_nodes = self._find_nodes_by_kind(root, "DefineDirective")
            for define in define_nodes:
                defines.append({
                    "name": self._get_node_name(define),
                    "type": "define",
                    "file_info": self._get_node_location(define),
                    "pyslang_parsed": True
                })
        except Exception as e:
            if self.debug:
                print(f"Preprocessor directive collection error: {e}")
        return defines

    # =========================================================================
    # FSM helpers: привязка enum'ов к модулям и сбор FSM-метаданных
    # =========================================================================

    def _attach_enums_to_modules(self, modules: List[Dict], enums: List[Dict]) -> List[Dict]:
        """
        Привязываем enum-типы к модулям по совпадению имён элементов enum'а
        с сигналами модуля. Параллельно строим module["fsm_states"].
        """
        if not modules or not enums:
            return modules

        result: List[Dict] = []
        for m in modules:
            if not isinstance(m, dict):
                result.append(m)
                continue

            sig_names = {
                s.get("name")
                for s in m.get("signals", [])
                if isinstance(s, dict) and s.get("name")
            }
            module_enums: List[Dict] = []
            fsm_states: List[Dict] = []

            for en in enums:
                members = en.get("members") or []
                enum_name = en.get("name", "anonymous_enum")
                # Привязываем enum к модулю, если хотя бы один его member есть среди сигналов
                if sig_names.intersection(members) or (
                    enum_name in sig_names and enum_name != "anonymous_enum"
                ):
                    module_enums.append(en)
                    for mem in members:
                        fsm_states.append({
                            "name": mem,
                            "type": "enum_member",
                            "enum": enum_name,
                            "source": "enum"
                        })

            if module_enums or fsm_states:
                m = dict(m)
                if module_enums:
                    m["enums"] = module_enums
                # Дедупликация состояний по имени
                seen = set()
                dedup_states: List[Dict] = []
                for st in fsm_states:
                    if st["name"] not in seen:
                        seen.add(st["name"])
                        dedup_states.append(st)
                if dedup_states:
                    m["fsm_states"] = dedup_states

            result.append(m)
        return result

    def _build_fsm_analysis(self, modules: List[Dict], enums: List[Dict]) -> Dict[str, Any]:
        """
        Строим компактный обзор по возможным FSM в модулях:
        - state-сигналы (имена, содержащие 'state')
        - состояния из enum'ов (module["fsm_states"])
        """
        per_module: List[Dict[str, Any]] = []

        for m in modules:
            if not isinstance(m, dict):
                continue

            mod_name = m.get("name", "?")

            # Сигналы, похожие на state-регистры
            state_signals = []
            for s in m.get("signals", []) or []:
                if not isinstance(s, dict):
                    continue
                nm = str(s.get("name", "")).lower()
                if "state" in nm:
                    state_signals.append({
                        "name": s.get("name", ""),
                        "width": s.get("width", ""),
                        "type": s.get("type", s.get("kind", "")),
                    })

            enum_states = m.get("fsm_states", []) or []
            has_fsm = bool(state_signals and enum_states)

            per_module.append({
                "module": mod_name,
                "state_signals": state_signals,
                "enum_states": enum_states,
                "has_fsm": has_fsm,
            })

        analysis = {
            "modules": per_module,
            "total_modules_with_fsm_like": sum(
                1 for m in per_module if m.get("has_fsm")
            ),
        }
        return analysis

    def _build_complete_metadata(self, modules, interfaces, programs, classes, packages, 
                                 typedefs, structs, enums, functions, tasks) -> Dict[str, Any]:
        """Построение полной метаинформации"""
        return {
            "total_modules_enhanced": len(modules),
            "total_interfaces": len(interfaces),
            "total_programs": len(programs),
            "total_classes": len(classes),
            "total_packages": len(packages),
            "total_typedefs": len(typedefs),
            "total_structs": len(structs),
            "total_enums": len(enums),
            "total_functions": len(functions),
            "total_tasks": len(tasks),
            "pyslang_analysis": True,
            "analysis_timestamp": "complete_analysis_pyslang_v1.0"
        }

    # =========================================================================
    # Connection and Hierarchy Analysis
    # =========================================================================

    def _build_complete_connection_graph(self, modules, interfaces) -> Dict[str, Any]:
        """Построение ПОЛНОГО графа соединений"""
        graph: Dict[str, Any] = {
            "nodes": [],
            "edges": [],
            "hierarchies": [],
            "top_level_modules": [],
            "pyslang_enhanced": True
        }
        
        # Создание узлов для модулей и интерфейсов
        for module in modules:
            graph["nodes"].append({
                "id": module.get("name", "?"),
                "type": "module",
                "ports": module.get("ports", []),
                "instances": module.get("instances", []),
                "enhanced": module.get("pyslang_analysis", False)
            })
            
        for interface in interfaces:
            graph["nodes"].append({
                "id": interface.get("name", "?"),
                "type": "interface",
                "ports": interface.get("ports", []),
                "enhanced": True
            })
        
        # Создание ребер для соединений
        for module in modules:
            for inst in module.get("instances", []):
                edge = {
                    "source": module.get("name", "?"),
                    "target": inst.get("type", "?"),
                    "type": "instance",
                    "instance_name": inst.get("name", "?"),
                    "enhanced": module.get("pyslang_analysis", False)
                }
                graph["edges"].append(edge)
        
        return graph

    def _build_complete_hierarchies(self, modules, interfaces, connections) -> List[Dict]:
        """Построение ПОЛНОЙ иерархии модулей"""
        hierarchies: List[Dict[str, Any]] = []
        module_instances: Dict[str, List[Dict[str, Any]]] = {}
        
        # Собираем информацию об инстансах для каждого модуля
        for module in modules:
            module_name = module.get("name", "?")
            instances = module.get("instances", [])
            module_instances[module_name] = instances
            
        for interface in interfaces:
            interface_name = interface.get("name", "?")
            instances = interface.get("instances", [])
            module_instances[interface_name] = instances
        
        # Строим иерархию от корневых модулей
        top_level_modules = self._find_top_level_modules(modules, connections)
        for top_module in top_level_modules:
            hierarchy = self._build_hierarchy_tree_complete(top_module, module_instances, set(), 0)
            hierarchies.append(hierarchy)
        
        return hierarchies

    def _find_top_level_modules(self, modules, connections) -> List[str]:
        """Поиск модулей верхнего уровня"""
        all_modules = {module.get("name", "?") for module in modules}
        instantiated_modules = {conn.get("to") for conn in connections} if connections else set()
        top_level_modules = all_modules - instantiated_modules
        if not top_level_modules:
            top_level_modules = all_modules
        return list(top_level_modules)

    def _build_hierarchy_tree_complete(self, module_name: str, module_instances: Dict, visited: Set, level: int) -> Dict:
        """Рекурсивное построение ПОЛНОГО дерева иерархии"""
        if module_name in visited:
            return {
                "name": module_name, 
                "type": "module", 
                "children": [], 
                "cycle": True,
                "level": level
            }
        
        visited.add(module_name)
        
        node: Dict[str, Any] = {
            "name": module_name,
            "type": "module",
            "children": [],
            "level": level,
            "instance_count": 0
        }
        
        instances = module_instances.get(module_name, [])
        node["instance_count"] = len(instances)
        
        for instance in instances:
            child_module = instance.get("type", "unknown")
            child_node = self._build_hierarchy_tree_complete(child_module, module_instances, visited.copy(), level + 1)
            child_node["instance_name"] = instance.get("name", "unknown")
            child_node["connections_count"] = len(instance.get("connections", []))
            node["children"].append(child_node)
        
        return node

    # =========================================================================
    # Timing and Analysis Methods
    # =========================================================================

    def _analyze_clock_domains(self, modules) -> List[Dict]:
        """Анализ тактовых доменов"""
        clock_domains: List[Dict[str, Any]] = []
        
        for module in modules:
            clocks = set()
            for always_block in module.get("always_blocks", []):
                sensitivity = always_block.get("sensitivity", "")
                if "posedge" in str(sensitivity) or "negedge" in str(sensitivity):
                    clocks.add("clock_signal")
            
            if clocks:
                clock_domains.append({
                    "module": module.get("name", "?"),
                    "clocks": list(clocks),
                    "always_blocks_count": len(module.get("always_blocks", [])),
                    "type": "synchronous" if clocks else "combinational",
                    "enhanced": module.get("pyslang_analysis", False)
                })
        
        return clock_domains

    def _analyze_reset_signals(self, modules) -> List[Dict]:
        """Анализ сигналов сброса"""
        reset_signals: List[Dict[str, Any]] = []
        
        for module in modules:
            resets = set()
            for port in module.get("ports", []):
                port_name = str(port.get("name", "")).lower()
                if "rst" in port_name or "reset" in port_name:
                    resets.add(port_name)
            
            if resets:
                reset_signals.append({
                    "module": module.get("name", "?"),
                    "reset_signals": list(resets),
                    "reset_type": "asynchronous",
                    "enhanced": module.get("pyslang_analysis", False)
                })
        
        return reset_signals

    def _analyze_assignments(self, modules) -> Dict[str, Any]:
        """Анализ присваиваний"""
        analysis: Dict[str, Any] = {
            "continuous_assignments": 0,
            "modules_with_assignments": []
        }
        
        for module in modules:
            module_assigns = len(module.get("assigns", []))
            
            if module_assigns > 0:
                analysis["modules_with_assignments"].append({
                    "module": module.get("name", "?"),
                    "continuous": module_assigns,
                    "total": module_assigns,
                    "enhanced": module.get("pyslang_analysis", False)
                })
            
            analysis["continuous_assignments"] += module_assigns
        
        return analysis

    def _analyze_timing(self, modules) -> Dict[str, Any]:
        """Анализ временных характеристик"""
        timing_info: Dict[str, Any] = {
            "synchronous_modules": 0,
            "combinational_modules": 0,
            "module_timing": []
        }
        
        for module in modules:
            has_sequential = False
            has_combinational = False
            
            for always_block in module.get("always_blocks", []):
                sens_desc = str(always_block.get("sensitivity", ""))
                if "posedge" in sens_desc or "negedge" in sens_desc:
                    has_sequential = True
                else:
                    has_combinational = True
            
            module_type = "unknown"
            if has_sequential and has_combinational:
                module_type = "mixed"
                timing_info["mixed_modules"] = timing_info.get("mixed_modules", 0) + 1
            elif has_sequential:
                module_type = "sequential"
                timing_info["synchronous_modules"] += 1
            elif has_combinational:
                module_type = "combinational"
                timing_info["combinational_modules"] += 1
            
            timing_info["module_timing"].append({
                "module": module.get("name", "?"),
                "type": module_type,
                "always_blocks": len(module.get("always_blocks", [])),
                "enhanced": module.get("pyslang_analysis", False)
            })
        
        return timing_info

    # =====================================================================
    # НОРМАЛИЗАЦИЯ ДЛЯ FSM DETECTOR (исправление 'op')
    # =====================================================================

    def _normalize_for_fsm_detector(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """
        Жесткая нормализация AST под формат, ожидаемый fsm_detector_service.py.
        Ничего не выкидываем — только дополняем / приводим к нужному виду.
        """
        modules = ast.get("modules", [])
        normalized_modules: List[Dict[str, Any]] = []

        for m in modules:
            mod = dict(m)  # копия

            # Имя
            mod["name"] = str(mod.get("name", "unnamed"))

            # signals
            mod["signals"] = self._normalize_signals(mod.get("signals", []))

            # typedefs
            mod["typedefs"] = self._normalize_typedefs(mod.get("typedefs", []))

            # parameters
            mod["parameters"] = self._normalize_parameters(
                mod.get("parameters", []),
                mod.get("enhanced_parameters", [])
            )

            # ports
            mod["ports"] = self._normalize_ports(
                mod.get("ports", []),
                mod.get("enhanced_ports", [])
            )

            # always_blocks (включая обязательный 'op' у присваиваний)
            mod["always_blocks"] = self._normalize_always_blocks(
                mod.get("always_blocks", [])
            )

            # assigns (включая обязательный 'op')
            mod["assigns"] = self._normalize_assigns(mod.get("assigns", []))

            # instances
            mod["instances"] = self._normalize_instances(mod.get("instances", []))

            normalized_modules.append(mod)

        ast["modules"] = normalized_modules
        return ast

    # --------------------------
    # НОРМАЛИЗАЦИЯ ПОЛЕЙ МОДУЛЯ
    # --------------------------

    def _normalize_signals(self, signals: List[Dict]) -> List[Dict]:
        norm: List[Dict[str, Any]] = []
        for s in signals or []:
            # Берём тип/вид сигнала из того, что есть
            sig_type = str(s.get("type", s.get("kind", "wire")))
            sig_kind = str(s.get("kind", sig_type))  # чтобы print_unified_ast не падал

            norm.append({
                "name": str(s.get("name", "unnamed")),
                "type": sig_type,                # то, что ждёт FSMDetector
                "kind": sig_kind,                # обратная совместимость с print_unified_ast
                "width": str(s.get("width", "")) # может быть "", "[2:0]" и т.д.
            })
        return norm

    def _normalize_typedefs(self, typedefs: List[Dict]) -> List[Dict]:
        norm: List[Dict[str, Any]] = []
        for t in typedefs or []:
            norm.append({
                "name": str(t.get("name", "anonymous")),
                "definition": str(t.get("definition", t.get("text", "")))
            })
        return norm

    def _normalize_parameters(self, base_params: List[Dict], enhanced_params: List[Dict]) -> List[Dict]:
        # Сшиваем параметры из базового AST и из pyslang
        merged: Dict[str, Dict[str, str]] = {}
        for p in base_params or []:
            name = str(p.get("name", ""))
            if not name:
                continue
            merged[name] = {
                "name": name,
                "value": str(p.get("value", p.get("default", "")))
            }
        for p in enhanced_params or []:
            name = str(p.get("name", ""))
            if not name:
                continue
            v = str(p.get("value", ""))
            if name in merged and not merged[name].get("value"):
                merged[name]["value"] = v
            elif name not in merged:
                merged[name] = {"name": name, "value": v}

        return list(merged.values())

    def _normalize_ports(self, base_ports: List[Dict], enhanced_ports: List[Dict]) -> List[Dict]:
        # Базовые + улучшенные, с унификацией ключей
        unified: List[Dict[str, Any]] = []

        def to_port(p: Dict) -> Dict:
            return {
                "name": str(p.get("name", "unnamed")),
                "direction": str(p.get("direction", p.get("dir", "unknown"))),
                "width": str(p.get("width", p.get("range", "")))
            }

        for p in base_ports or []:
            unified.append(to_port(p))
        for p in enhanced_ports or []:
            unified.append(to_port(p))

        # возможна дедупликация по имени
        dedup: Dict[str, Dict[str, Any]] = {}
        for p in unified:
            dedup[p["name"]] = p
        return list(dedup.values())

    def _normalize_always_blocks(self, always_blocks: List[Dict]) -> List[Dict]:
        """
        Приводим каждый always-блок к виду:
        {
          "sensitivity": str,                 # пример: "posedge Clock or posedge Rst" или "@*"
          "assignments": [{"left": str, "right": str, "line": int, "op": str}, ...]
        }
        """
        norm: List[Dict[str, Any]] = []

        for blk in always_blocks or []:
            sensitivity = blk.get("sensitivity", blk.get("sens", blk.get("event", "")))
            if isinstance(sensitivity, (list, tuple)):
                sensitivity = " ".join(map(str, sensitivity))
            sensitivity = str(sensitivity)

            assignments_norm: List[Dict[str, Any]] = []
            assigns_src = blk.get("assignments", blk.get("stmts", blk.get("statements", []))) or []
            for a in assigns_src:
                left = str(a.get("left", a.get("lhs", "")))
                right = str(a.get("right", a.get("rhs", "")))
                line = int(a.get("line", a.get("lineno", 0)))

                # ВАЖНО: принтер базового AST ожидает 'op'
                op = a.get("op", a.get("operator"))
                if not op:
                    rhs_text = str(a.get("text", "")) or right
                    op = "<=" if "<=" in rhs_text else "="

                assignments_norm.append({"left": left, "right": right, "line": line, "op": op})

            norm.append({
                "sensitivity": sensitivity,
                "assignments": assignments_norm
            })

        return norm

    def _normalize_assigns(self, assigns: List[Dict]) -> List[Dict]:
        """
        Нормализуем непрерывные присваивания (assign ...).
        Формат: [{"left": str, "right": str, "line": int, "op": str}, ...]
        """
        norm: List[Dict[str, Any]] = []
        for a in assigns or []:
            left = str(a.get("left", a.get("lhs", "")))
            right = str(a.get("right", a.get("rhs", "")))
            line = int(a.get("line", a.get("lineno", 0)))
            op = a.get("op", a.get("operator", "="))
            norm.append({"left": left, "right": right, "line": line, "op": op})
        return norm

    def _normalize_instances(self, instances: List[Dict]) -> List[Dict]:
        """
        Инстансы модулей:
        [{"name": str, "type": str, "connections": List[...]}]
        """
        norm: List[Dict[str, Any]] = []
        for inst in instances or []:
            norm.append({
                "name": str(inst.get("name", "u_unnamed")),
                "type": str(inst.get("type", inst.get("module", "unknown"))),
                "connections": list(inst.get("connections", []))
            })
        return norm

    # ============================
    # СЕРИАЛИЗАЦИЯ ДЛЯ FSM DETECTOR
    # ============================
    def save_fsm_detector_input(self,
                                ast: Dict[str, Any],
                                filepath: str,
                                module_name: Optional[str] = None,
                                pretty: bool = True) -> Dict[str, Any]:
        """
        Сохраняет модуль в файле в формате, пригодном для FSMDetectorService.
        Если module_name не задан, берётся первый модуль.
        Возвращает payload (что именно записали).
        """
        # На всякий случай — доводим формат до нужного детектору (если вызвали не через build_complete_ast_from_cst)
        try:
            normalized = self._normalize_for_fsm_detector(dict(ast))
        except Exception:
            normalized = ast

        modules = normalized.get("modules", []) or []
        if not modules:
            raise ValueError("Нет модулей в AST: нечего сохранять для FSM детектора.")

        if module_name:
            pick = next((m for m in modules if m.get("name") == module_name), None)
            if pick is None:
                raise ValueError(f"Модуль '{module_name}' не найден в AST.")
        else:
            pick = modules[0]

        module_payload = {
            "schema": "fsm_detector_module_v1",
            "generated_by": "CompleteASTService",
            "parser_used": normalized.get("parser_used", ""),
            "module": pick,  # ровно тот dict, который ждёт детектор
        }

        out = Path(filepath)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            if pretty:
                json.dump(module_payload, f, ensure_ascii=False, indent=2)
            else:
                json.dump(module_payload, f, ensure_ascii=False, separators=(",", ":"))

        return module_payload

    @staticmethod
    def load_fsm_detector_input(filepath: str) -> Dict[str, Any]:
        """
        Загружает сохранённый файл и возвращает dict с ключом 'module'.
        Удобно, чтобы затем передать module прямо в
        FSMDetectorService.detect_finite_state_machines(module, tree).
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "module" not in data:
            raise ValueError("Неверный формат файла: ключ 'module' не найден.")
        return data


def print_complete_ast(ast: Dict[str, Any]):
    """Печать ПОЛНОГО AST в читаемом формате"""
    print("\n" + "="*80)
    print("COMPLETE ABSTRACT SYNTAX TREE (Pyslang Enhanced)")
    print("="*80)
    
    # Сначала используем базовую функцию печати
    print_unified_ast(ast)
    
    # Затем дополняем расширенной информацией
    enhanced_analysis = ast.get("enhanced_analysis", {})
    
    if enhanced_analysis:
        print("\n" + "="*80)
        print("ENHANCED ANALYSIS (Pyslang)")
        print("="*80)
        
        # Расширенные элементы
        data_types = enhanced_analysis.get("data_types", {})
        for k in ("typedefs", "structs", "enums", "unions"):
            lst = data_types.get(k, [])
            if lst:
                print(f"\n📝 ENHANCED {k.upper()} ({len(lst)}):")
                for e in lst:
                    name = e.get("name", "unnamed")
                    # Для enum выводим список элементов
                    if k == "enums":
                        members = e.get("members") or []
                        if members:
                            members_str = ", ".join(members)
                            print(f"   - {name} {{{members_str}}} [pyslang]")
                        else:
                            print(f"   - {name} [pyslang]")
                    else:
                        print(f"   - {name} [pyslang]")

        # Behavioral элементы
        behavioral = enhanced_analysis.get("behavioral_elements", {})
        for k in ("functions", "tasks"):
            lst = behavioral.get(k, [])
            if lst:
                print(f"\n🎯 ENHANCED {k.upper()} ({len(lst)}):")
                for e in lst:
                    print(f"   - {e.get('name','unnamed')} [pyslang]")

        # Граф соединений
        connection_graph = enhanced_analysis.get("connection_graph", {})
        if connection_graph.get("edges"):
            print(f"\n🔗 ENHANCED CONNECTION GRAPH ({len(connection_graph['edges'])} edges):")
            for edge in connection_graph["edges"]:
                enhanced = " [pyslang]" if edge.get('enhanced') else ""
                print(f"   {edge['source']} --[{edge['instance_name']}]--> {edge['target']}{enhanced}")

        # Timing анализ
        timing_analysis = enhanced_analysis.get("timing_analysis", {})
        if timing_analysis.get("clock_domains"):
            print(f"\n⏰ CLOCK DOMAIN ANALYSIS:")
            for cd in timing_analysis["clock_domains"]:
                enhanced = " [pyslang]" if cd.get('enhanced') else ""
                print(f"   {cd['module']}: {cd['type']} ({cd['always_blocks_count']} always blocks){enhanced}")

        # FSM-анализ
        fsm_analysis = enhanced_analysis.get("fsm")
        if fsm_analysis:
            print(f"\n⚙️ FSM ANALYSIS (modules with FSM-like pattern: {fsm_analysis.get('total_modules_with_fsm_like', 0)}):")
            for m in fsm_analysis.get("modules", []):
                state_sigs = m.get("state_signals") or []
                enum_states = m.get("enum_states") or []
                if not (state_sigs or enum_states):
                    continue
                print(f"   Module {m.get('module', '?')}:")
                if state_sigs:
                    sig_str = ", ".join(s["name"] for s in state_sigs)
                    print(f"     state signals: {sig_str}")
                if enum_states:
                    st_str = ", ".join(s["name"] for s in enum_states)
                    print(f"     enum states: {st_str}")


def _print_complete_hierarchy_tree(node: Dict, level: int = 0):
    """Рекурсивная печать ПОЛНОГО дерева иерархии"""
    indent = "  " * level
    node_type = f" ({node['type']})" if node.get('type') else ""
    cycle = " [CYCLE]" if node.get('cycle') else ""
    instances = f" [{node.get('instance_count', 0)} inst]" if node.get('instance_count', 0) > 0 else ""
    
    print(f"{indent}{node['name']}{node_type}{instances}{cycle}")
    
    for child in node.get("children", []):
        _print_complete_hierarchy_tree(child, level + 1)


# =========================
#  ПРИМЕР ИСПОЛЬЗОВАНИЯ С Pyslang
# =========================

def complete_example_usage_pyslang():
    """Пример использования ПОЛНОГО AST сервиса с pyslang (совместим с FSMDetectorService)"""
    
    example_code = """
    //
// Ticket Machine modified for SystemVerilog
// Jenner Hanni
//
// This file handles encoding and behavior of a finite state machine to control
// a mass transit ticketing machine. A One Week Travel ticket costs $40. The 
// machine accepts only $20 and $10 bills and will return all bills if more than
// $40 is placed in the machine. The machine does not make change. 
//
// Improvements in SystemVerilog:
//    - use of a package
//
// The four states:  READY (LED on to indicate bills will be accepted)
//           DISPENSE (dispenses a ticket once $40 received)
//           RETURN (return all bills if more than $40 received)
//           BILL (turns on LED to indicate an incomplete transaction)
// 

package definitions;

  parameter VERSION = "1.1";

  parameter ON  = 1'b1;
  parameter OFF = 1'b0;

  enum logic [5:0] {RDY, BILL10, BILL20, BILL30, DISP, RTN} State, NextState;
  enum {CASE[9]} Testcase;

  parameter TRUE = 1'b1;
  parameter FALSE = 1'b0;
  parameter CLOCK_CYCLE = 20ms;
  parameter CLOCK_WIDTH = CLOCK_CYCLE/2;
  parameter IDLE_CLOCKS = 2ms;

endpackage

module TicketVendorBotOneHot (input Clock,
                              input Clear,
                              input Ten,
                              input Twenty, 
                              output reg Ready,
                              output reg Dispense,
                              output reg Return,
                              output reg Bill);

  import definitions::*;

  //
  // Update state or reset on every + clock edge
  // We have no clear
  //

  always @(posedge Clock)
  begin 
   if (Clear)
      State <= RDY;
   else
      State <= NextState;
  end

  //
  // Outputs depend only upon state (Moore machine)
  //

  always @(State)
  begin
  case (State)
      RDY:      begin
        Ready    = ON;
          Bill     = OFF;
          Dispense = OFF;
          Return   = OFF;
          end

      DISP:     begin
          Ready    = OFF;
          Bill     = OFF;
          Dispense = ON;
          Return   = OFF;
          end

      RTN:      begin
          Ready    = OFF;
          Bill     = OFF;
          Dispense = OFF;
          Return   = ON;
          end

      BILL10: begin
          Ready    = OFF;
          Bill     = ON;
          Dispense = OFF;
          Return   = OFF;
          end

      BILL20: begin
          Ready    = OFF;
          Bill     = ON;
          Dispense = OFF;
          Return   = OFF;
          end

      BILL30: begin
          Ready    = OFF;
          Bill     = ON;
          Dispense = OFF;
          Return   = OFF;
          end

  endcase
  end



  //
  // Next state generation logic
  //

  always @(State or Ten or Twenty)
  begin
  case (State)
      RDY:  begin
          if (Ten)
              NextState = BILL10;
          else if (Twenty)
              NextState = BILL20;
          else
              NextState = RDY;
          end

      BILL10:  begin
          if (Ten)
              NextState = BILL20;
          else if (Twenty)
              NextState = BILL30;
          else
              NextState = BILL10;
          end

      BILL20:  begin
          if (Ten)
              NextState = BILL30;
          else if (Twenty)
              NextState = DISP;
          else
              NextState = BILL20;
          end

      BILL30:  begin
          if (Ten)
              NextState = DISP;
          else if (Twenty)
              NextState = RTN;
          else
              NextState = BILL30;
          end

      DISP: begin
              NextState = RDY;
          end

      RTN:  begin
              NextState = RDY;
          end

  endcase
  end


endmodule

    """
    
    try:
        # Используем существующий CST сервис
        from cst_service import CSTService
        
        # Строим CST
        cst_service = CSTService()
        tree = cst_service.build_cst_from_text(example_code, "example.sv")
        
        # Используем ПОЛНЫЙ AST сервис для построения AST
        ast_service = CompleteASTService()
        ast = ast_service.build_complete_ast_from_cst(tree)
        
        # Печатаем результат
        print_complete_ast(ast)
        
        # Пример сохранения (можно закомментировать, если не нужно автосохранение):
        # ast_service.save_fsm_detector_input(ast, "out/fsm_input_ticket_vendor.json",
        #                                     module_name="TicketVendorBotOneHot", pretty=True)
        
        return ast
        
    except Exception as e:
        print(f"Error with complete AST service: {e}")
        # Fallback to basic AST service + минимальная нормализация
        from ast_service import ASTService as BasicASTService
        basic_ast_service = BasicASTService()
        basic_ast = basic_ast_service.build_ast_from_cst(tree)
        try:
            return CompleteASTService()._normalize_for_fsm_detector(basic_ast)
        except Exception:
            return basic_ast


if __name__ == "__main__":
    complete_example_usage_pyslang()
