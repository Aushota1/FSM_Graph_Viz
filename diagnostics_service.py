# -*- coding: utf-8 -*-
# fsm_detector_service.py
"""
Сервис для детектирования конечных автоматов (FSM) в SystemVerilog коде
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

class FSMDetectorService:
    """Сервис для детектирования конечных автоматов"""
    
    def __init__(self):
        self._fsm_patterns = self._init_fsm_patterns()
    
    def _init_fsm_patterns(self) -> Dict[str, Any]:
        """Инициализация паттернов для детектирования FSM"""
        return {
            "state_variables": {
                "state", "current_state", "next_state", "fsm_state", "ctrl_state", 
                "present_state", "future_state", "status", "mode", "st", "fsm",
                "curr_st", "nxt_st", "present_st", "next_st"
            },
            "state_enum_prefixes": {"state_", "st_", "fsm_", "s_", "mode_", "status_"},
            "state_keywords": {
                "IDLE", "READY", "BUSY", "WAIT", "DONE", "ERROR", "INIT", "START", 
                "STOP", "RUN", "PAUSE", "RESET", "WORK", "FINISH", "HALT", "PROCESS",
                "TRANSMIT", "RECEIVE", "CHECK", "VALIDATE", "ACK", "NACK", "SUCCESS",
                "FAIL", "LOAD", "STORE", "FETCH", "DECODE", "EXECUTE", "WRITE", "READ",
                "SEND", "RECV", "HIGH", "LOW", "ON", "OFF", "ENABLE", "DISABLE",
                "ACTIVE", "INACTIVE", "VALID", "INVALID", "OPEN", "CLOSE", "UP", "DOWN"
            },
            "transition_keywords": {"case", "if", "else if", "else", "when", "default"},
            "state_assignment_operators": {"<=", "=", "=="},
            "reset_patterns": ["rst", "reset", "rst_n", "rstn", "reset_n"],
            "clock_patterns": ["clk", "clock", "aclk", "pclk"],
            "fsm_keywords": {"finite", "state", "machine", "fsm", "state_machine"},
            "always_keywords": {"always", "always_ff", "always_comb", "always_latch"},
            "case_keywords": {"case", "casex", "casez", "endcase"}
        }
    
    def detect_finite_state_machines(self, module: Dict[str, Any], tree=None) -> Dict[str, Any]:
        """Детектирование конечных автоматов в модуле"""
        fsm_info = {
            "detected": False,
            "type": "unknown",
            "states": [],
            "transitions": [],
            "state_variables": [],
            "reset_condition": "",
            "clock_signal": "",
            "always_blocks": [],
            "state_registers": [],
            "next_state_logic": [],
            "output_logic": [],
            "complexity_score": 0,
            "fsm_structure": {}
        }

        try:
            # Расширенный поиск переменных состояний
            state_vars, state_registers = self._find_state_variables_extended(module)
            
            if not state_vars and not state_registers:
                return fsm_info

            fsm_info["detected"] = True
            fsm_info["state_variables"] = state_vars
            fsm_info["state_registers"] = state_registers

            # Анализ always блоков
            always_blocks = module.get("always_blocks", [])
            fsm_info["always_blocks"] = always_blocks

            # Расширенный анализ FSM
            fsm_analysis = self._analyze_fsm_structure(module, always_blocks, state_vars, state_registers)
            
            fsm_info.update(fsm_analysis)
            
            # Расчет сложности FSM
            complexity = self._calculate_fsm_complexity(fsm_info)
            fsm_info["complexity_score"] = complexity
            
            # Определение структуры FSM
            fsm_structure = self._determine_fsm_structure(fsm_info)
            fsm_info["fsm_structure"] = fsm_structure

        except Exception as e:
            fsm_info["error"] = str(e)
            
        return fsm_info

    def _find_state_variables_extended(self, module: Dict[str, Any]) -> Tuple[List[Dict], List[Dict]]:
        """Расширенный поиск переменных состояний и регистров"""
        state_vars = []
        state_registers = []
        
        # Поиск в сигналах
        for signal in module.get("signals", []):
            signal_name = signal.get("name", "").lower()
            signal_type = signal.get("type", "").lower()
            
            # Проверка по паттернам имен
            for pattern in self._fsm_patterns["state_variables"]:
                if pattern in signal_name:
                    var_info = {
                        "name": signal["name"],
                        "type": signal_type,
                        "width": signal.get("width", ""),
                        "pattern_match": pattern,
                        "is_register": "reg" in signal_type
                    }
                    
                    if var_info["is_register"]:
                        state_registers.append(var_info)
                    else:
                        state_vars.append(var_info)
                    break
            
            # Проверка по префиксам
            for prefix in self._fsm_patterns["state_enum_prefixes"]:
                if signal_name.startswith(prefix):
                    var_info = {
                        "name": signal["name"],
                        "type": signal_type,
                        "width": signal.get("width", ""),
                        "pattern_match": f"prefix_{prefix}",
                        "is_register": "reg" in signal_type
                    }
                    
                    if var_info["is_register"]:
                        state_registers.append(var_info)
                    else:
                        state_vars.append(var_info)
                    break
        
        # Поиск typedef/enum переменных
        for typedef in module.get("typedefs", []):
            typedef_name = typedef.get("name", "").lower()
            if any(pattern in typedef_name for pattern in self._fsm_patterns["state_variables"]):
                state_vars.append({
                    "name": typedef["name"],
                    "type": "typedef",
                    "definition": typedef.get("definition", ""),
                    "is_register": False
                })
        
        # Поиск в параметрах
        for param in module.get("parameters", []):
            param_name = param.get("name", "").upper()
            if any(keyword in param_name for keyword in self._fsm_patterns["state_keywords"]):
                state_vars.append({
                    "name": param["name"],
                    "type": "parameter",
                    "value": param.get("value", ""),
                    "is_register": False
                })
        
        # Эвристический анализ по использованию в коде
        code_analysis_vars = self._heuristic_state_analysis(module)
        state_vars.extend(code_analysis_vars)
        
        return state_vars, state_registers

    def _heuristic_state_analysis(self, module: Dict[str, Any]) -> List[Dict]:
        """Эвристический анализ для поиска переменных состояний"""
        found_vars = []
        code_text = self._get_module_code_text(module)
        
        # Поиск case statements с подозрительными переменными
        case_patterns = [
            r'case\s*\(\s*(\w+)\s*\)',
            r'casex\s*\(\s*(\w+)\s*\)',
            r'casez\s*\(\s*(\w+)\s*\)'
        ]
        
        for pattern in case_patterns:
            matches = re.finditer(pattern, code_text, re.IGNORECASE)
            for match in matches:
                var_name = match.group(1)
                # Проверяем, используется ли эта переменная в state-like контексте
                if self._is_state_like_variable(var_name, code_text):
                    found_vars.append({
                        "name": var_name,
                        "type": "heuristic_case",
                        "pattern_match": "case_statement",
                        "is_register": self._is_register_variable(var_name, module)
                    })
        
        # Поиск в always блоках
        for block in module.get("always_blocks", []):
            sensitivity = block.get("sensitivity", "").lower()
            
            # Ищем переменные, которые обновляются по тактовому сигналу
            if any(clock in sensitivity for clock in self._fsm_patterns["clock_patterns"]):
                for assign in block.get("assignments", []):
                    left_var = assign.get("left", "")
                    if self._is_state_like_variable(left_var, code_text):
                        found_vars.append({
                            "name": left_var,
                            "type": "heuristic_sequential",
                            "pattern_match": "clocked_assignment",
                            "is_register": True
                        })
        
        return found_vars

    def _is_state_like_variable(self, var_name: str, code_text: str) -> bool:
        """Проверка, является ли переменная похожей на состояние"""
        var_lower = var_name.lower()
        
        # Проверка по имени
        if any(pattern in var_lower for pattern in self._fsm_patterns["state_variables"]):
            return True
        
        # Проверка по использованию в case statements с state keywords
        case_context = self._get_variable_case_context(var_name, code_text)
        if any(keyword in case_context.upper() for keyword in self._fsm_patterns["state_keywords"]):
            return True
            
        return False

    def _get_variable_case_context(self, var_name: str, code_text: str) -> str:
        """Получение контекста использования переменной в case statements"""
        # Ищем case блоки с этой переменной
        pattern = rf'case\s*\(\s*{var_name}\s*\)(.*?)endcase'
        matches = re.findall(pattern, code_text, re.IGNORECASE | re.DOTALL)
        return " ".join(matches)

    def _is_register_variable(self, var_name: str, module: Dict[str, Any]) -> bool:
        """Проверка, является ли переменная регистром"""
        for signal in module.get("signals", []):
            if signal.get("name") == var_name and "reg" in signal.get("type", "").lower():
                return True
        return False

    def _analyze_fsm_structure(self, module: Dict[str, Any], always_blocks: List[Dict], 
                             state_vars: List[Dict], state_registers: List[Dict]) -> Dict[str, Any]:
        """Расширенный анализ структуры FSM"""
        analysis = {
            "type": "unknown",
            "states": [],
            "transitions": [],
            "reset_condition": "",
            "clock_signal": "",
            "next_state_logic": [],
            "output_logic": []
        }
        
        # Извлечение состояний
        states = self._extract_states_extended(module)
        analysis["states"] = states
        
        # Извлечение переходов
        transitions = self._extract_transitions_extended(always_blocks, state_vars, state_registers, states)
        analysis["transitions"] = transitions
        
        # Определение типа FSM
        fsm_type = self._determine_fsm_type_extended(always_blocks, state_vars, state_registers, transitions)
        analysis["type"] = fsm_type
        
        # Поиск сигналов
        reset_cond, clock_signal = self._find_reset_and_clock_extended(always_blocks, module)
        analysis["reset_condition"] = reset_cond
        analysis["clock_signal"] = clock_signal
        
        # Анализ логики следующего состояния и выходов
        next_state_logic, output_logic = self._analyze_state_and_output_logic(always_blocks, state_vars, state_registers)
        analysis["next_state_logic"] = next_state_logic
        analysis["output_logic"] = output_logic
        
        return analysis

    def _extract_states_extended(self, module: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Расширенное извлечение состояний"""
        states = []
        
        # Из параметров
        for param in module.get("parameters", []):
            param_name = param.get("name", "")
            if any(keyword in param_name.upper() for keyword in self._fsm_patterns["state_keywords"]):
                states.append({
                    "name": param_name,
                    "type": "parameter",
                    "value": param.get("value", ""),
                    "source": "parameter"
                })
        
        # Из локальных параметров
        for localparam in module.get("localparams", []):
            param_name = localparam.get("name", "")
            if any(keyword in param_name.upper() for keyword in self._fsm_patterns["state_keywords"]):
                states.append({
                    "name": param_name,
                    "type": "localparam",
                    "value": localparam.get("value", ""),
                    "source": "localparam"
                })
        
        # Из enum определений
        for typedef in module.get("typedefs", []):
            if "enum" in typedef.get("definition", "").lower():
                # Парсим enum значения
                enum_values = self._parse_enum_values(typedef.get("definition", ""))
                for value in enum_values:
                    states.append({
                        "name": value,
                        "type": "enum",
                        "enum_type": typedef.get("name", ""),
                        "source": "typedef_enum"
                    })
        
        # Из case statements
        states.extend(self._extract_states_from_case_statements_extended(module))
        
        # Из присваиваний
        states.extend(self._extract_states_from_assignments_extended(module))
        
        # Эвристический поиск
        states.extend(self._heuristic_state_search(module))
        
        # Удаление дубликатов
        return self._remove_duplicate_states(states)

    def _parse_enum_values(self, enum_definition: str) -> List[str]:
        """Парсинг значений из enum определения"""
        values = []
        # Простой парсинг enum {VALUE1, VALUE2, VALUE3}
        matches = re.findall(r'(\w+)(?:\s*=.*?)?(?:\s*,|\s*})', enum_definition)
        for match in matches:
            if match and match not in ['enum', 'typedef']:
                values.append(match)
        return values

    def _extract_states_from_case_statements_extended(self, module: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Расширенное извлечение состояний из case statements"""
        states = []
        code_text = self._get_module_code_text(module)
        
        # Поиск case items
        case_patterns = [
            r"(\w+)\s*:",
            r"'(\w+)",
            r"(\w+)\s*="
        ]
        
        for pattern in case_patterns:
            matches = re.finditer(pattern, code_text)
            for match in matches:
                state_name = match.group(1)
                if any(keyword in state_name.upper() for keyword in self._fsm_patterns["state_keywords"]):
                    states.append({
                        "name": state_name,
                        "type": "case_branch",
                        "source": "case_statement"
                    })
        
        return states

    def _extract_states_from_assignments_extended(self, module: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Расширенное извлечение состояний из присваиваний"""
        states = []
        
        for block in module.get("always_blocks", []):
            for assign in block.get("assignments", []):
                right_side = assign.get("right", "")
                
                # Ищем состояния в правой части
                for keyword in self._fsm_patterns["state_keywords"]:
                    if keyword.upper() in right_side.upper():
                        states.append({
                            "name": keyword,
                            "type": "inferred",
                            "source": f"assignment: {assign.get('left', '?')}",
                            "context": right_side
                        })
                
                # Ищем параметры состояний
                for param in module.get("parameters", []):
                    if param["name"] in right_side:
                        states.append({
                            "name": param["name"],
                            "type": "parameter_ref",
                            "source": f"assignment_ref: {assign.get('left', '?')}",
                            "context": right_side
                        })
        
        return states

    def _heuristic_state_search(self, module: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Эвристический поиск состояний"""
        states = []
        code_text = self._get_module_code_text(module).upper()
        
        # Поиск по ключевым словам в контексте FSM
        for keyword in self._fsm_patterns["state_keywords"]:
            if keyword in code_text:
                # Проверяем контекст использования
                context_patterns = [
                    rf'\b{keyword}\b',
                    rf"'{keyword}",
                    rf'"{keyword}'
                ]
                
                for pattern in context_patterns:
                    if re.search(pattern, code_text, re.IGNORECASE):
                        states.append({
                            "name": keyword,
                            "type": "heuristic",
                            "source": "heuristic_search"
                        })
                        break
        
        return states

    def _remove_duplicate_states(self, states: List[Dict]) -> List[Dict]:
        """Удаление дубликатов состояний"""
        seen = set()
        unique_states = []
        
        for state in states:
            state_id = (state["name"], state["type"])
            if state_id not in seen:
                seen.add(state_id)
                unique_states.append(state)
                
        return unique_states

    def _extract_transitions_extended(self, always_blocks: List[Dict], state_vars: List[Dict], 
                                    state_registers: List[Dict], states: List[Dict]) -> List[Dict[str, Any]]:
        """Расширенное извлечение переходов"""
        transitions = []
        
        for block in always_blocks:
            sensitivity = block.get("sensitivity", "").lower()
            assignments = block.get("assignments", [])
            conditions = block.get("conditions", [])
            
            # Анализ присваиваний состояний
            for assign in assignments:
                left_var = assign.get("left", "")
                right_expr = assign.get("right", "")
                
                # Проверяем присваивание переменной состояния
                if self._is_state_assignment(left_var, state_vars, state_registers):
                    transition = self._analyze_state_transition(assign, block, states, conditions)
                    if transition:
                        transitions.append(transition)
            
            # Анализ условий перехода
            for condition in conditions:
                transition = self._analyze_conditional_transition(condition, block, states, state_vars)
                if transition:
                    transitions.append(transition)
        
        return transitions

    def _is_state_assignment(self, left_var: str, state_vars: List[Dict], state_registers: List[Dict]) -> bool:
        """Проверка, является ли присваивание присваиванием состояния"""
        left_lower = left_var.lower()
        
        # Проверка по переменным состояний
        for state_var in state_vars + state_registers:
            if state_var["name"].lower() in left_lower:
                return True
                
        return False

    def _analyze_state_transition(self, assignment: Dict, always_block: Dict, 
                                states: List[Dict], conditions: List[Dict]) -> Optional[Dict]:
        """Анализ перехода состояния"""
        left_var = assignment.get("left", "")
        right_expr = assignment.get("right", "")
        sensitivity = always_block.get("sensitivity", "").lower()
        
        from_state = self._infer_from_state_extended(always_block, conditions)
        to_state = self._extract_state_from_expression_extended(right_expr, states)
        condition = self._extract_transition_condition_extended(always_block, conditions)
        
        if to_state != "unknown_state":
            return {
                "from_state": from_state,
                "to_state": to_state,
                "condition": condition,
                "type": "clocked" if any(p in sensitivity for p in self._fsm_patterns["clock_patterns"]) else "combinational",
                "sensitivity": sensitivity,
                "assignment": f"{left_var} = {right_expr}",
                "line": assignment.get("line", "")
            }
        
        return None

    def _infer_from_state_extended(self, always_block: Dict, conditions: List[Dict]) -> str:
        """Расширенный вывод исходного состояния"""
        sensitivity = always_block.get("sensitivity", "")
        
        # Анализ условий для определения исходного состояния
        for condition in conditions:
            cond_text = condition.get("text", "").lower()
            # Ищем упоминания текущего состояния в условиях
            for pattern in self._fsm_patterns["state_variables"]:
                if pattern in cond_text:
                    return "current_state"
        
        # Эвристика по типу блока
        if "posedge" in sensitivity or "negedge" in sensitivity:
            return "current_state"
        elif "@*" in sensitivity or "always_comb" in sensitivity:
            return "current_state"
            
        return "any_state"

    def _extract_state_from_expression_extended(self, expression: str, states: List[Dict]) -> str:
        """Расширенное извлечение состояния из выражения"""
        expr_upper = expression.upper()
        
        # Точные совпадения
        for state in states:
            state_name_upper = state["name"].upper()
            # Ищем как отдельный идентификатор
            patterns = [
                rf'\b{state_name_upper}\b',
                rf"'{state_name_upper}",
                rf'"{state_name_upper}'
            ]
            
            for pattern in patterns:
                if re.search(pattern, expr_upper):
                    return state["name"]
        
        # Поиск в параметрах
        param_matches = re.findall(r'(\w+)\s*\'', expr_upper)
        for param in param_matches:
            for state in states:
                if state["name"].upper() == param:
                    return state["name"]
        
        # Специальные случаи
        if "DEFAULT" in expr_upper:
            return "default"
        elif "X" in expr_upper or "DONTCARE" in expr_upper:
            return "dont_care"
            
        return "unknown_state"

    def _extract_transition_condition_extended(self, always_block: Dict, conditions: List[Dict]) -> str:
        """Расширенное извлечение условия перехода"""
        sensitivity = always_block.get("sensitivity", "").lower()
        
        # Анализ чувствительности
        if any(pattern in sensitivity for pattern in self._fsm_patterns["reset_patterns"]):
            return "reset"
        elif any(pattern in sensitivity for pattern in self._fsm_patterns["clock_patterns"]):
            return "clock_edge"
        elif sensitivity == "@*" or "always_comb" in sensitivity:
            return "combinational"
        
        # Анализ условий
        if conditions:
            return " | ".join([cond.get("text", "") for cond in conditions])
        
        return "unknown_condition"

    def _analyze_conditional_transition(self, condition: Dict, always_block: Dict, 
                                      states: List[Dict], state_vars: List[Dict]) -> Optional[Dict]:
        """Анализ условного перехода"""
        # Этот метод можно расширить для анализа сложных условий
        return None

    def _determine_fsm_type_extended(self, always_blocks: List[Dict], state_vars: List[Dict], 
                                   state_registers: List[Dict], transitions: List[Dict]) -> str:
        """Расширенное определение типа FSM"""
        if not always_blocks:
            return "unknown"
        
        state_reg_blocks = 0
        comb_blocks = 0
        output_in_comb = 0
        output_in_seq = 0
        
        for block in always_blocks:
            sensitivity = block.get("sensitivity", "").lower()
            assignments = block.get("assignments", [])
            
            # Проверка на регистр состояний
            is_clocked = any(pattern in sensitivity for pattern in self._fsm_patterns["clock_patterns"])
            
            if is_clocked:
                # Считаем блоки регистров состояний
                for assign in assignments:
                    if self._is_state_assignment(assign.get("left", ""), state_vars, state_registers):
                        state_reg_blocks += 1
                        break
                
                # Проверяем выходы в последовательных блоках
                for assign in assignments:
                    if not self._is_state_assignment(assign.get("left", ""), state_vars, state_registers):
                        output_in_seq += 1
                        break
            else:
                # Комбинационные блоки
                comb_blocks += 1
                
                # Проверяем выходы в комбинационных блоках
                for assign in assignments:
                    if not self._is_state_assignment(assign.get("left", ""), state_vars, state_registers):
                        output_in_comb += 1
                        break
        
        # Улучшенная классификация
        if state_reg_blocks > 0 and comb_blocks > 0:
            if output_in_comb > 0:
                return "mealy"
            else:
                return "moore"
        elif state_reg_blocks > 0:
            return "registered"
        elif comb_blocks > 0:
            return "combinational"
        else:
            return "unknown"

    def _find_reset_and_clock_extended(self, always_blocks: List[Dict], module: Dict[str, Any]) -> Tuple[str, str]:
        """Расширенный поиск сброса и тактового сигнала"""
        reset_condition = "unknown"
        clock_signal = "unknown"
        
        # Поиск в always блоках
        for block in always_blocks:
            sensitivity = block.get("sensitivity", "").lower()
            
            # Поиск сброса
            for pattern in self._fsm_patterns["reset_patterns"]:
                if pattern in sensitivity:
                    reset_condition = pattern
                    # Извлекаем полное условие сброса
                    reset_match = re.search(rf'({"|".join(self._fsm_patterns["reset_patterns"])})\s*\w*', sensitivity)
                    if reset_match:
                        reset_condition = reset_match.group(0)
                    break
            
            # Поиск тактового сигнала
            for pattern in self._fsm_patterns["clock_patterns"]:
                if pattern in sensitivity:
                    # Извлекаем имя сигнала
                    clock_match = re.search(rf'(posedge|negedge)\s*(\w+)', sensitivity)
                    if clock_match:
                        clock_signal = clock_match.group(2)
                    else:
                        clock_signal = pattern
                    break
        
        # Поиск в портах модуля
        if clock_signal == "unknown" or reset_condition == "unknown":
            for port in module.get("ports", []):
                port_name = port.get("name", "").lower()
                if any(pattern in port_name for pattern in self._fsm_patterns["clock_patterns"]):
                    clock_signal = port_name
                if any(pattern in port_name for pattern in self._fsm_patterns["reset_patterns"]):
                    reset_condition = port_name
        
        return reset_condition, clock_signal

    def _analyze_state_and_output_logic(self, always_blocks: List[Dict], state_vars: List[Dict], 
                                      state_registers: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Анализ логики следующего состояния и выходов"""
        next_state_logic = []
        output_logic = []
        
        for block in always_blocks:
            sensitivity = block.get("sensitivity", "").lower()
            assignments = block.get("assignments", [])
            
            for assign in assignments:
                left_var = assign.get("left", "")
                right_expr = assign.get("right", "")
                
                if self._is_state_assignment(left_var, state_vars, state_registers):
                    # Логика следующего состояния
                    next_state_logic.append({
                        "variable": left_var,
                        "expression": right_expr,
                        "sensitivity": sensitivity,
                        "type": "next_state"
                    })
                else:
                    # Выходная логика
                    output_logic.append({
                        "variable": left_var,
                        "expression": right_expr,
                        "sensitivity": sensitivity,
                        "type": "output"
                    })
        
        return next_state_logic, output_logic

    def _calculate_fsm_complexity(self, fsm_info: Dict[str, Any]) -> int:
        """Расчет сложности FSM"""
        complexity = 0
        
        # Базовая сложность
        if fsm_info["detected"]:
            complexity += 10
        
        # Сложность по количеству состояний
        complexity += len(fsm_info["states"]) * 2
        
        # Сложность по количеству переходов
        complexity += len(fsm_info["transitions"])
        
        # Сложность по типу FSM
        type_weights = {
            "mealy": 5,
            "moore": 3,
            "registered": 2,
            "combinational": 1,
            "unknown": 0
        }
        complexity += type_weights.get(fsm_info["type"], 0)
        
        return complexity

    def _determine_fsm_structure(self, fsm_info: Dict[str, Any]) -> Dict[str, Any]:
        """Определение структуры FSM"""
        structure = {
            "has_sequential_block": False,
            "has_combinational_block": False,
            "has_output_logic": False,
            "state_encoding": "unknown",
            "reset_type": "unknown"
        }
        
        # Проверка блоков
        for block in fsm_info["always_blocks"]:
            sensitivity = block.get("sensitivity", "").lower()
            
            if any(pattern in sensitivity for pattern in self._fsm_patterns["clock_patterns"]):
                structure["has_sequential_block"] = True
            elif "@*" in sensitivity or "always_comb" in sensitivity:
                structure["has_combinational_block"] = True
        
        # Проверка выходной логики
        if fsm_info["output_logic"]:
            structure["has_output_logic"] = True
        
        # Определение кодирования состояний
        state_count = len(fsm_info["states"])
        if state_count <= 2:
            structure["state_encoding"] = "binary"
        elif state_count <= 16:
            structure["state_encoding"] = "one_hot"
        else:
            structure["state_encoding"] = "gray"
        
        # Тип сброса
        reset_cond = fsm_info["reset_condition"]
        if "rst_n" in reset_cond or "reset_n" in reset_cond:
            structure["reset_type"] = "active_low"
        elif "rst" in reset_cond or "reset" in reset_cond:
            structure["reset_type"] = "active_high"
        
        return structure

    def _get_module_code_text(self, module: Dict[str, Any]) -> str:
        """Получение текстового представления кода модуля"""
        # В реальной реализации здесь должен быть доступ к исходному коду
        # Для демонстрации возвращаем пустую строку
        return module.get("code", "")

    def _get_module_text(self, module: Dict[str, Any], tree) -> str:
        """Получить текстовое представление модуля"""
        # Заглушка для совместимости
        return self._get_module_code_text(module)