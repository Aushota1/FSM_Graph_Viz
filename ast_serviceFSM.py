# -*- coding: utf-8 -*-
# ast_service_improved.py
"""
Улучшенный сервис для построения Abstract Syntax Tree (AST) из CST
С улучшенным детектированием конечных автоматов
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from cst_service import CSTService, find_first, find_all, first_identifier_text, collect_identifiers_inline, range_width_text, kind, children, text_of

class ASTService:
    """Сервис для построения Abstract Syntax Tree"""
    
    def __init__(self):
        self._fsm_patterns = self._init_fsm_patterns()
    
    def _init_fsm_patterns(self) -> Dict[str, Any]:
        """Инициализация паттернов для детектирования FSM"""
        return {
            "state_variables": {"state", "current_state", "next_state", "fsm_state", "ctrl_state", "present_state", "future_state"},
            "state_enum_prefixes": {"state_", "st_", "fsm_", "s_"},
            "state_keywords": {"IDLE", "READY", "BUSY", "WAIT", "DONE", "ERROR", "INIT", "START", "STOP", "RUN", "PAUSE", "RESET", "WORK", "FINISH"},
            "transition_keywords": {"case", "if", "else if"},
            "state_assignment_operators": {"<=", "="},
            "reset_patterns": ["rst", "reset", "rst_n"],
            "clock_patterns": ["clk", "clock"]
        }
    
    def build_ast_from_cst(self, tree) -> Dict[str, Any]:
        """Построить AST из CST"""
        root = tree.root
        modules = [self._parse_module(md) for md in find_all(root, "ModuleDeclaration")]
        interfaces = [self._parse_interface(x) for x in find_all(root, "InterfaceDeclaration")]
        packages = [self._parse_package(x) for x in find_all(root, "PackageDeclaration")]
        classes = [self._parse_class(x) for x in find_all(root, "ClassDeclaration")]
        typedefs, structs, enums = self._collect_types(root)

        # Детектирование FSM и построение соединений
        connections = []
        module_fsms = {}
        
        for m in modules:
            # Детектирование FSM для каждого модуля
            fsm_info = self._detect_finite_state_machines(m, tree)
            if fsm_info["detected"]:
                module_fsms[m["name"]] = fsm_info
            
            # Построение соединений для экземпляров модулей
            for inst in m.get("instances", []):
                connections.append({
                    "type": "instance",
                    "from": m["name"],
                    "to": inst.get("type", "?"),
                    "instance_name": inst.get("name", "?"),
                    "connections": inst.get("connections", [])
                })

        # Построение полного графа соединений
        connection_graph = self._build_connection_graph(modules, connections)

        return {
            "type": "UnifiedAST",
            "parser_used": "pyslang_cst",
            "modules": modules,
            "systemverilog_elements": {
                "interfaces": interfaces,
                "packages": packages,
                "classes": classes,
                "typedefs": typedefs,
                "structs": structs,
                "enums": enums,
            },
            "connections": connections,
            "connection_graph": connection_graph,
            "finite_state_machines": module_fsms,
            "metadata": {
                "total_modules": len(modules),
                "interfaces_count": len(interfaces),
                "packages_count": len(packages),
                "classes_count": len(classes),
                "typedefs_count": len(typedefs),
                "fsm_count": len(module_fsms),
                "total_connections": len(connections),
            }
        }

    def _detect_finite_state_machines(self, module: Dict[str, Any], tree) -> Dict[str, Any]:
        """Детектирование конечных автоматов в модуле"""
        fsm_info = {
            "detected": False,
            "type": "unknown",
            "states": [],
            "transitions": [],
            "state_variables": [],
            "reset_condition": "",
            "clock_signal": "",
            "always_blocks": []
        }

        # Поиск переменных состояний
        state_vars = self._find_state_variables(module)
        if not state_vars:
            return fsm_info

        fsm_info["detected"] = True
        fsm_info["state_variables"] = state_vars

        # Анализ always блоков для определения типа FSM
        always_blocks = module.get("always_blocks", [])
        fsm_info["always_blocks"] = always_blocks

        # Определение типа FSM
        fsm_type = self._determine_fsm_type(always_blocks, state_vars)
        fsm_info["type"] = fsm_type

        # Извлечение состояний
        states = self._extract_states(module, tree, state_vars)
        fsm_info["states"] = states

        # Извлечение переходов
        transitions = self._extract_transitions(always_blocks, state_vars, states)
        fsm_info["transitions"] = transitions

        # Поиск условия сброса и тактового сигнала
        reset_cond, clock_signal = self._find_reset_and_clock(always_blocks)
        fsm_info["reset_condition"] = reset_cond
        fsm_info["clock_signal"] = clock_signal

        return fsm_info

    def _find_state_variables(self, module: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Поиск переменных состояний с улучшенной эвристикой"""
        state_vars = []
        
        # Поиск в сигналах
        for signal in module.get("signals", []):
            signal_name = signal.get("name", "").lower()
            
            # Проверка по паттернам имен
            for pattern in self._fsm_patterns["state_variables"]:
                if pattern in signal_name:
                    state_vars.append({
                        "name": signal["name"],
                        "type": "signal",
                        "width": signal.get("width", ""),
                        "pattern_match": pattern
                    })
                    break
            
            # Проверка по префиксам
            for prefix in self._fsm_patterns["state_enum_prefixes"]:
                if signal_name.startswith(prefix):
                    state_vars.append({
                        "name": signal["name"],
                        "type": "signal",
                        "width": signal.get("width", ""),
                        "pattern_match": f"prefix_{prefix}"
                    })
                    break
        
        # Поиск typedef/enum переменных
        for typedef in module.get("typedefs", []):
            typedef_name = typedef.get("name", "").lower()
            if any(pattern in typedef_name for pattern in self._fsm_patterns["state_variables"]):
                state_vars.append({
                    "name": typedef["name"],
                    "type": "typedef",
                    "definition": typedef.get("definition", "")
                })
        
        return state_vars

    def _determine_fsm_type(self, always_blocks: List[Dict], state_vars: List[Dict]) -> str:
        """Определение типа FSM (Moore/Mealy/Hybrid) с улучшенной логикой"""
        if not always_blocks:
            return "unknown"
        
        state_reg_blocks = 0
        comb_blocks = 0
        output_blocks = 0
        
        for block in always_blocks:
            sensitivity = block.get("sensitivity", "").lower()
            assignments = block.get("assignments", [])
            
            # Проверка на регистр состояний (clocked always block)
            is_clocked = any(pattern in sensitivity for pattern in self._fsm_patterns["clock_patterns"])
            has_reset = any(pattern in sensitivity for pattern in self._fsm_patterns["reset_patterns"])
            
            if is_clocked:
                # Проверяем присваивания переменных состояния
                for assign in assignments:
                    left_var = assign.get("left", "").lower()
                    if any(state_var["name"].lower() in left_var for state_var in state_vars):
                        state_reg_blocks += 1
                        break
            
            # Проверка на комбинационную логику
            if sensitivity == "@*" or "always_comb" in sensitivity:
                comb_blocks += 1
                # Проверяем присваивания выходов на основе состояний
                for assign in assignments:
                    right_expr = assign.get("right", "").lower()
                    if any(state_var["name"].lower() in right_expr for state_var in state_vars):
                        output_blocks += 1
                        break
        
        # Логика классификации
        if state_reg_blocks > 0 and comb_blocks > 0:
            return "mealy"
        elif state_reg_blocks > 0 and output_blocks > 0:
            return "moore"
        elif state_reg_blocks > 0:
            return "registered"
        else:
            return "combinational"

    def _extract_states(self, module: Dict[str, Any], tree, state_vars: List[Dict]) -> List[Dict[str, Any]]:
        """Извлечение состояний FSM с улучшенным анализом"""
        states = []
        
        # Поиск enum определений в модуле
        for enum_def in self._find_module_enums(module, tree):
            states.extend(enum_def)
        
        # Поиск параметров состояний
        for param in module.get("parameters", []):
            param_name = param.get("name", "")
            param_value = param.get("value", "")
            
            # Эвристика: параметры с именами состояний
            if any(keyword in param_name.upper() for keyword in self._fsm_patterns["state_keywords"]):
                states.append({
                    "name": param_name,
                    "type": "parameter",
                    "value": param_value,
                    "source": "parameter"
                })
        
        # Поиск в присваиваниях always блоков
        states.extend(self._extract_states_from_assignments(module))
        
        # Поиск в case statements
        states.extend(self._extract_states_from_case_statements(module, tree))
        
        return states

    def _find_module_enums(self, module: Dict[str, Any], tree) -> List[List[Dict]]:
        """Поиск enum определений, связанных с модулем"""
        enums = []
        root = tree.root
        
        # Поиск typedef enum в модуле
        module_text = self._get_module_text(module, tree)
        
        for enum_node in find_all(root, "EnumType"):
            enum_name = first_identifier_text(enum_node) or "anonymous"
            
            # Проверяем, используется ли этот enum в модуле
            if enum_name in module_text:
                enum_states = []
                for enumerator in find_all(enum_node, "Enumerator"):
                    state_name = first_identifier_text(enumerator)
                    if state_name:
                        enum_states.append({
                            "name": state_name,
                            "type": "enum",
                            "enum_type": enum_name,
                            "source": "typedef_enum"
                        })
                if enum_states:
                    enums.append(enum_states)
        
        return enums

    def _get_module_text(self, module: Dict[str, Any], tree) -> str:
        """Получить текстовое представление модуля"""
        # Упрощенная реализация - можно улучшить
        module_name = module.get("name", "")
        for node in find_all(tree.root, "ModuleDeclaration"):
            if first_identifier_text(node) == module_name:
                return collect_identifiers_inline(node) or ""
        return ""

    def _extract_states_from_assignments(self, module: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Извлечение состояний из присваиваний"""
        states = []
        
        for block in module.get("always_blocks", []):
            for assign in block.get("assignments", []):
                right_side = assign.get("right", "")
                
                # Ищем состояния в правой части присваивания
                for keyword in self._fsm_patterns["state_keywords"]:
                    if keyword.upper() in right_side.upper():
                        states.append({
                            "name": keyword,
                            "type": "inferred",
                            "source": f"assignment: {assign.get('left', '?')}",
                            "context": right_side
                        })
        
        return states

    def _extract_states_from_case_statements(self, module: Dict[str, Any], tree) -> List[Dict[str, Any]]:
        """Извлечение состояний из case statements"""
        states = []
        
        # Упрощенная реализация - поиск по тексту модуля
        module_text = self._get_module_text(module, tree).upper()
        
        for keyword in self._fsm_patterns["state_keywords"]:
            if keyword in module_text:
                # Проверяем контекст - должен быть в case или присваивании
                if f"CASE {keyword}" in module_text or f"'{keyword}" in module_text:
                    states.append({
                        "name": keyword,
                        "type": "case_branch",
                        "source": "case_statement"
                    })
        
        return states

    def _extract_transitions(self, always_blocks: List[Dict], state_vars: List[Dict], states: List[Dict]) -> List[Dict[str, Any]]:
        """Извлечение переходов между состояниями с улучшенным анализом"""
        transitions = []
        
        for block in always_blocks:
            sensitivity = block.get("sensitivity", "").lower()
            assignments = block.get("assignments", [])
            
            # Анализируем только блоки с присваиваниями состояний
            for assign in assignments:
                left_var = assign.get("left", "")
                right_expr = assign.get("right", "")
                
                # Проверяем, является ли присваивание переменной состояния
                if any(state_var["name"].lower() in left_var.lower() for state_var in state_vars):
                    from_state = self._infer_from_state(block, state_vars)
                    to_state = self._extract_state_from_expression(right_expr, states)
                    condition = self._extract_transition_condition(block, state_vars)
                    
                    transition = {
                        "from_state": from_state,
                        "to_state": to_state,
                        "condition": condition,
                        "type": "clocked" if any(p in sensitivity for p in self._fsm_patterns["clock_patterns"]) else "combinational",
                        "sensitivity": sensitivity,
                        "assignment": f"{left_var} = {right_expr}"
                    }
                    transitions.append(transition)
        
        return transitions

    def _infer_from_state(self, always_block: Dict, state_vars: List[Dict]) -> str:
        """Вывод исходного состояния из контекста"""
        # Упрощенная реализация - можно улучшить анализом case/if statements
        sensitivity = always_block.get("sensitivity", "")
        if "posedge" in sensitivity or "negedge" in sensitivity:
            return "current_state"
        return "any_state"

    def _extract_state_from_expression(self, expression: str, states: List[Dict]) -> str:
        """Извлечение состояния из выражения с улучшенной логикой"""
        expr_upper = expression.upper()
        
        # Сначала ищем точные совпадения
        for state in states:
            state_name_upper = state["name"].upper()
            # Ищем состояние как отдельный идентификатор
            if f" {state_name_upper} " in f" {expr_upper} ":
                return state["name"]
        
        # Затем ищем частичные совпадения
        for state in states:
            if state["name"].upper() in expr_upper:
                return state["name"]
        
        # Если не нашли, анализируем выражение
        if "DEFAULT" in expr_upper or "'DEFAULT" in expr_upper:
            return "default"
        
        return "unknown_state"

    def _extract_transition_condition(self, always_block: Dict, state_vars: List[Dict]) -> str:
        """Извлечение условия перехода"""
        sensitivity = always_block.get("sensitivity", "")
        
        # Анализ чувствительности
        if any(pattern in sensitivity for pattern in self._fsm_patterns["reset_patterns"]):
            return "reset"
        elif any(pattern in sensitivity for pattern in self._fsm_patterns["clock_patterns"]):
            return "clock_edge"
        elif sensitivity == "@*":
            return "combinational"
        
        return "unknown_condition"

    def _find_reset_and_clock(self, always_blocks: List[Dict]) -> Tuple[str, str]:
        """Поиск условия сброса и тактового сигнала"""
        reset_condition = "unknown"
        clock_signal = "unknown"
        
        for block in always_blocks:
            sensitivity = block.get("sensitivity", "").lower()
            
            # Поиск сброса
            for pattern in self._fsm_patterns["reset_patterns"]:
                if pattern in sensitivity:
                    reset_condition = pattern
                    break
            
            # Поиск тактового сигнала
            for pattern in self._fsm_patterns["clock_patterns"]:
                if pattern in sensitivity:
                    # Извлекаем имя сигнала
                    parts = sensitivity.split()
                    for i, part in enumerate(parts):
                        if pattern in part and i + 1 < len(parts):
                            clock_signal = parts[i + 1]
                            break
                    if clock_signal == "unknown":
                        clock_signal = pattern
        
        return reset_condition, clock_signal

    # Остальные методы остаются без изменений
    def _build_connection_graph(self, modules: List[Dict], connections: List[Dict]) -> Dict[str, Any]:
        """Построение графа соединений между модулями"""
        graph = {
            "nodes": [],
            "edges": [],
            "hierarchies": []
        }
        
        # Создание узлов для модулей
        module_nodes = {}
        for module in modules:
            node_id = module["name"]
            module_nodes[node_id] = {
                "id": node_id,
                "type": "module",
                "ports": module.get("ports", []),
                "instances": module.get("instances", []),
                "signals": module.get("signals", [])
            }
            graph["nodes"].append(module_nodes[node_id])
        
        # Создание ребер для соединений
        for conn in connections:
            source_module = conn["from"]
            target_module = conn["to"]
            
            if source_module in module_nodes and target_module in module_nodes:
                edge = {
                    "source": source_module,
                    "target": target_module,
                    "type": "instance",
                    "instance_name": conn["instance_name"],
                    "connections": conn.get("connections", []),
                    "port_count": len(conn.get("connections", []))
                }
                graph["edges"].append(edge)
        
        # Построение иерархий
        graph["hierarchies"] = self._build_module_hierarchies(modules, connections)
        
        return graph

    def _build_module_hierarchies(self, modules: List[Dict], connections: List[Dict]) -> List[Dict]:
        """Построение иерархии модулей"""
        hierarchies = []
        module_instances = {}
        
        # Собираем информацию об инстансах для каждого модуля
        for module in modules:
            module_name = module["name"]
            instances = module.get("instances", [])
            module_instances[module_name] = instances
        
        # Строим иерархию от корневых модулей
        root_modules = self._find_root_modules(modules, connections)
        
        for root in root_modules:
            hierarchy = self._build_hierarchy_tree(root, module_instances, set())
            hierarchies.append(hierarchy)
        
        return hierarchies

    def _find_root_modules(self, modules: List[Dict], connections: List[Dict]) -> List[str]:
        """Поиск корневых модулей (тех, которые нигде не инстанциируются)"""
        all_modules = {module["name"] for module in modules}
        instantiated_modules = {conn["to"] for conn in connections}
        
        root_modules = all_modules - instantiated_modules
        
        # Если нет явных корней, берем все модули
        if not root_modules:
            root_modules = all_modules
        
        return list(root_modules)

    def _build_hierarchy_tree(self, module_name: str, module_instances: Dict, visited: Set) -> Dict:
        """Рекурсивное построение дерева иерархии"""
        if module_name in visited:
            return {"name": module_name, "type": "module", "children": [], "cycle": True}
        
        visited.add(module_name)
        
        node = {
            "name": module_name,
            "type": "module",
            "children": []
        }
        
        instances = module_instances.get(module_name, [])
        for instance in instances:
            child_module = instance.get("type", "unknown")
            child_node = self._build_hierarchy_tree(child_module, module_instances, visited.copy())
            child_node["instance_name"] = instance.get("name", "unknown")
            node["children"].append(child_node)
        
        return node

    # Существующие методы парсинга модулей (без изменений)
    def _parse_module(self, mod_decl) -> Dict[str, Any]:
        """Разбор объявления модуля"""
        mod = {"name": "", "type": "Module", "parameters": [], "type_parameters": [], "ports": [],
               "signals": [], "nets": [], "instances": [], "always_blocks": [], "initial_blocks": [],
               "assigns": [], "generate": []}

        header = find_first(mod_decl, "ModuleHeader")
        if header:
            name = first_identifier_text(header)
            if name:
                mod["name"] = name
            self._parse_parameter_port_list(header, mod)
            self._parse_ports(header, mod)

        self._parse_data_declarations(mod_decl, mod)
        self._parse_instantiations(mod_decl, mod)
        self._parse_assigns(mod_decl, mod)
        self._parse_always(mod_decl, mod)
        self._parse_initial(mod_decl, mod)
        self._parse_generate(mod_decl, mod)
        return mod

    def _parse_interface(self, node) -> Dict[str, Any]:
        """Разбор интерфейса"""
        name = first_identifier_text(node) or "unnamed_interface"
        return {"name": name, "type": "Interface", "body_preview": self._body_preview(node)}

    def _parse_package(self, node) -> Dict[str, Any]:
        """Разбор пакета"""
        name = first_identifier_text(node) or "unnamed_package"
        return {"name": name, "type": "Package", "body_preview": self._body_preview(node)}

    def _parse_class(self, node) -> Dict[str, Any]:
        """Разбор класса"""
        name = first_identifier_text(node) or "unnamed_class"
        return {"name": name, "type": "Class", "body_preview": self._body_preview(node)}

    def _body_preview(self, node, limit: int = 160) -> str:
        """Превью тела элемента"""
        t = (collect_identifiers_inline(node) or "").strip()
        return t[:limit] + ("..." if len(t) > limit else "")

    def _collect_types(self, root):
        """Сбор информации о типах"""
        typedefs: List[Dict] = []
        structs: List[Dict] = []
        enums: List[Dict] = []

        for td in find_all(root, "TypedefDeclaration"):
            name = first_identifier_text(td) or "unnamed_typedef"
            typedefs.append({"name": name, "definition": self._body_preview(td), "type": "Typedef"})

        for st in find_all(root, "StructUnionType"):
            name = ""
            decl = find_first(st, "Declarator")
            if decl:
                name = first_identifier_text(decl) or name
            if not name:
                name = "anonymous_struct"
            structs.append({"name": name, "type": "StructUnion", "packed": bool(find_first(st, "PackedKeyword")),
                            "body": self._body_preview(st)})

        for en in find_all(root, "EnumType"):
            name = ""
            decl = find_first(en, "Declarator")
            if decl:
                name = first_identifier_text(decl) or name
            if not name:
                ident = find_first(en, "Identifier")
                if ident:
                    name = collect_identifiers_inline(ident)
            if not name:
                name = "anonymous_enum"
            enums.append({"name": name, "type": "Enum", "values": self._enum_values(en)})
        return typedefs, structs, enums

    def _enum_values(self, en_node) -> str:
        """Извлечение значений перечисления"""
        names = []
        for n in find_all(en_node, "Enumerator"):
            nm = first_identifier_text(n)
            if nm:
                names.append(nm)
        return ", ".join(names)

    def _parse_parameter_port_list(self, header, mod):
        """Разбор списка параметров"""
        ppl = find_first(header, "ParameterPortList")
        if not ppl:
            return
        for pdecl in find_all(ppl, "ParameterDeclaration") + find_all(ppl, "LocalParameterDeclaration"):
            pname = first_identifier_text(pdecl) or "?"
            eq = find_first(pdecl, "EqualsValueClause")
            pval = "?"
            if eq:
                txt = collect_identifiers_inline(eq)
                pval = txt.split("=",1)[-1].strip() if "=" in txt else txt
            mod["parameters"].append({"name": pname, "value": pval})
        for tpd in find_all(ppl, "TypeParameterDeclaration"):
            tname = first_identifier_text(tpd) or "?"
            mod["type_parameters"].append({"name": tname})

    def _parse_ports(self, header, mod):
        """Разбор портов"""
        apl = find_first(header, "AnsiPortList")
        if not apl:
            return
        ports = []
        port_nodes = find_all(apl, "ImplicitAnsiPort") + find_all(apl, "ExplicitAnsiPort")
        for port in port_nodes:
            dir_node = (find_first(port, "InputKeyword") or find_first(port, "OutputKeyword") or
                        find_first(port, "InOutKeyword") or find_first(port, "RefKeyword"))
            direction = (collect_identifiers_inline(dir_node) or "unknown").lower()

            decl = find_first(port, "Declarator")
            pname = first_identifier_text(decl) if decl else None

            width = ""
            logic_type = (find_first(port, "LogicType") or find_first(port, "BitType") or
                          find_first(port, "RegType"))
            if logic_type:
                vdim = find_first(logic_type, "VariableDimension")
                if vdim:
                    width = range_width_text(vdim)

            if pname:
                ports.append({"type":"Port","direction":direction,"name":pname,"width":width})
        mod["ports"] = ports

    def _parse_data_declarations(self, mod_decl, mod):
        """Разбор объявлений данных"""
        for dd in find_all(mod_decl, "DataDeclaration"):
            width = ""
            logic_type = (find_first(dd, "LogicType") or find_first(dd, "BitType") or find_first(dd, "RegType"))
            if logic_type:
                vdim = find_first(logic_type, "VariableDimension")
                if vdim:
                    width = range_width_text(vdim)
            for decl in find_all(dd, "Declarator"):
                sname = first_identifier_text(decl)
                if sname:
                    mod["signals"].append({"name": sname, "kind": "var", "width": width})

        for nd in find_all(mod_decl, "NetDeclaration"):
            width = ""
            vdim = find_first(nd, "VariableDimension")
            if vdim:
                width = range_width_text(vdim)
            for decl in find_all(nd, "Declarator"):
                nname = first_identifier_text(decl)
                if nname:
                    netkw = find_first(nd, "NetType")
                    nkind = collect_identifiers_inline(netkw) or "net"
                    mod["nets"].append({"name": nname, "kind": nkind, "width": width})

    def _parse_instantiations(self, mod_decl, mod):
        """Разбор инстансов модулей"""
        for hi in find_all(mod_decl, "HierarchyInstantiation"):
            type_name = first_identifier_text(hi) or "?"
            for inst in find_all(hi, "HierarchicalInstance"):
                iname = first_identifier_text(inst) or "?"
                conns = self._parse_port_connections(inst)
                mod["instances"].append({"type": type_name, "name": iname, "connections": conns})

        for mi in find_all(mod_decl, "ModuleInstantiation"):
            type_name = first_identifier_text(mi) or "?"
            for inst in find_all(mi, "HierarchicalInstance"):
                iname = first_identifier_text(inst) or "?"
                conns = self._parse_port_connections(inst)
                mod["instances"].append({"type": type_name, "name": iname, "connections": conns})

    def _parse_port_connections(self, inst_node) -> List[Dict[str, str]]:
        """Разбор подключений портов"""
        conns = []
        pl = find_first(inst_node, "PortConnectionList")
        if not pl:
            return conns
        for npc in find_all(pl, "NamedPortConnection"):
            pname = first_identifier_text(npc) or "?"
            expr = collect_identifiers_inline(npc)
            if "(" in expr:
                expr = expr.split("(",1)[-1].rstrip(")")
            conns.append({"port": pname, "arg": expr})
        if not conns:
            idx = 0
            for opc in find_all(pl, "OrderedPortConnection"):
                expr = collect_identifiers_inline(opc)
                conns.append({"port": f"${idx}", "arg": expr})
                idx += 1
        return conns

    def _parse_assigns(self, mod_decl, mod):
        """Разбор присваиваний"""
        for ca in find_all(mod_decl, "ContinuousAssign"):
            for ae in find_all(ca, "AssignmentExpression"):
                lhs = first_identifier_text(ae)
                txt = collect_identifiers_inline(ae)
                rhs = txt.split("=",1)[1].strip() if "=" in txt else "?"
                mod["assigns"].append({"left": lhs, "right": rhs, "op": "="})

    def _parse_always(self, mod_decl, mod):
        """Разбор always блоков"""
        blocks = []
        for ab in (find_all(mod_decl, "AlwaysFFBlock") + find_all(mod_decl, "AlwaysCombBlock") +
                   find_all(mod_decl, "AlwaysLatchBlock") + find_all(mod_decl, "AlwaysBlock")):
            sens = self._sensitivity(ab)
            assigns = self._extract_assignments_in_stmt(ab)
            blocks.append({"sensitivity": sens, "assignments": assigns})
        mod["always_blocks"] = blocks

    def _sensitivity(self, always_node) -> str:
        """Извлечение списка чувствительности"""
        ev = find_first(always_node, "EventControlWithExpression") or find_first(always_node, "EventControl")
        if not ev:
            if find_first(always_node, "AlwaysCombKeyword") or kind(always_node) == "AlwaysCombBlock":
                return "@*"
            return ""
        edge = "posedge" if find_first(ev, "PosEdgeKeyword") else ("negedge" if find_first(ev, "NegEdgeKeyword") else "")
        sig = first_identifier_text(ev) or ""
        return f"{edge} {sig}".strip()

    def _extract_assignments_in_stmt(self, node) -> List[Dict[str,str]]:
        """Извлечение присваиваний из операторов"""
        out = []
        for nbe in find_all(node, "NonblockingAssignmentExpression"):
            txt = collect_identifiers_inline(nbe)
            if "<=" in txt:
                lhs, rhs = txt.split("<=",1)
                out.append({"kind":"nonblocking","op":"<=","left":lhs.strip(),"right":rhs.strip()})
        for be in find_all(node, "BlockingAssignmentExpression"):
            txt = collect_identifiers_inline(be)
            if "=" in txt:
                lhs, rhs = txt.split("=",1)
                out.append({"kind":"blocking","op":"=","left":lhs.strip(),"right":rhs.strip()})
        return out

    def _parse_initial(self, mod_decl, mod):
        """Разбор initial блоков"""
        inits = []
        for ib in find_all(mod_decl, "InitialBlock"):
            assigns = self._extract_assignments_in_stmt(ib)
            inits.append({"assignments": assigns})
        mod["initial_blocks"] = inits

    def _parse_generate(self, mod_decl, mod):
        """Разбор generate блоков"""
        gens = []
        for gr in find_all(mod_decl, "GenerateRegion"):
            gens.append({"kind":"region","body_preview": self._body_preview(gr)})
        for ig in find_all(mod_decl, "IfGenerateConstruct"):
            cond = self._condition_preview(ig)
            gens.append({"kind":"if","cond":cond,"body_preview": self._body_preview(ig)})
        for cg in find_all(mod_decl, "CaseGenerateConstruct"):
            expr = self._condition_preview(cg)
            gens.append({"kind":"case","expr":expr,"body_preview": self._body_preview(cg)})
        for lg in find_all(mod_decl, "LoopGenerateConstruct"):
            gens.append({"kind":"for","body_preview": self._body_preview(lg)})
        mod["generate"] = gens

    def _condition_preview(self, node) -> str:
        """Превью условия"""
        paren = find_first(node, "ParenthesizedExpression")
        if paren:
            return collect_identifiers_inline(paren)
        return self._body_preview(node, limit=60)
    
def print_unified_ast(ast: Dict[str, Any]):
    """Печать AST в читаемом формате с FSM и соединениями"""
    print("\n=== UNIFIED AST ===")
    print(f"parser_used: {ast.get('parser_used')}  |  modules: {len(ast.get('modules',[]))}")
    
    # Печать метаданных
    metadata = ast.get("metadata", {})
    print(f"FSM count: {metadata.get('fsm_count', 0)} | Connections: {metadata.get('total_connections', 0)}")
    
    for m in ast.get("modules", []):
        print(f"\nMODULE {m['name']}")
        
        # Базовая информация о модуле
        if m["type_parameters"]:
            print("  TYPE PARAMETERS:")
            for p in m["type_parameters"]:
                print(f"    type {p['name']}")
        if m["parameters"]:
            print("  PARAMETERS:")
            for p in m["parameters"]:
                print(f"    {p['name']} = {p['value']}")
        if m["ports"]:
            print("  PORTS:")
            for p in m["ports"]:
                w = f" {p['width']}" if p['width'] else ""
                print(f"    {p['direction']:7s} {p['name']}{w}")
        if m["signals"]:
            print("  SIGNALS:")
            for s in m["signals"]:
                w = f" {s['width']}" if s['width'] else ""
                print(f"    {s['name']}{w} ({s['kind']})")
        
        # Информация о FSM
        fsm_info = ast.get("finite_state_machines", {}).get(m["name"])
        if fsm_info and fsm_info["detected"]:
            print("  FINITE STATE MACHINE:")
            print(f"    Type: {fsm_info['type']}")
            print(f"    State variables: {[v['name'] for v in fsm_info.get('state_variables', [])]}")
            print(f"    States: {[s['name'] for s in fsm_info.get('states', [])]}")
            print(f"    Reset condition: {fsm_info.get('reset_condition', 'unknown')}")
            print(f"    Clock signal: {fsm_info.get('clock_signal', 'unknown')}")
            print(f"    Transitions: {len(fsm_info.get('transitions', []))}")
        
        if m["assigns"]:
            print("  ASSIGNS:")
            for a in m["assigns"]:
                print(f"    {a['left']} = {a['right']}")
        if m["always_blocks"]:
            print("  ALWAYS:")
            for ab in m["always_blocks"]:
                print(f"    ({ab['sensitivity']})")
                for asg in ab["assignments"]:
                    print(f"      {asg['left']} {asg['op']} {asg['right']}")
        if m["instances"]:
            print("  INSTANCES:")
            for inst in m["instances"]:
                print(f"    {inst['name']} : {inst['type']}")
                for c in inst.get("connections", []):
                    print(f"      .{c['port']}({c['arg']})")

    # Печать информации о FSM
    fsms = ast.get("finite_state_machines", {})
    if fsms:
        print(f"\nFINITE STATE MACHINES ({len(fsms)}):")
        for module_name, fsm in fsms.items():
            if fsm["detected"]:
                print(f"  {module_name}: {fsm['type']} FSM with {len(fsm.get('states', []))} states")

    # Печать графа соединений
    connection_graph = ast.get("connection_graph", {})
    if connection_graph.get("edges"):
        print(f"\nCONNECTION GRAPH ({len(connection_graph['edges'])} edges):")
        for edge in connection_graph["edges"]:
            print(f"  {edge['source']} --[{edge['instance_name']}]--> {edge['target']}")

    # Печать иерархий
    hierarchies = connection_graph.get("hierarchies", [])
    if hierarchies:
        print(f"\nMODULE HIERARCHIES:")
        for hierarchy in hierarchies:
            _print_hierarchy_tree(hierarchy)

    sve = ast.get("systemverilog_elements", {})
    for k in ("interfaces","packages","classes","typedefs","structs","enums"):
        lst = sve.get(k, [])
        if lst:
            print(f"\n{k.upper()} ({len(lst)}):")
            for e in lst:
                print(f"  - {e.get('name','unnamed')}")

def _print_hierarchy_tree(node: Dict, level: int = 0):
    """Рекурсивная печать дерева иерархии"""
    indent = "  " * level
    node_type = f" ({node['type']})" if node.get('type') else ""
    cycle = " [CYCLE]" if node.get('cycle') else ""
    print(f"{indent}{node['name']}{node_type}{cycle}")
    
    for child in node.get("children", []):
        _print_hierarchy_tree(child, level + 1) 