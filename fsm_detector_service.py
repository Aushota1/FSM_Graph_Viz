# -*- coding: utf-8 -*-
# fsm_detector_service.py
"""
Сервис для детектирования конечных автоматов (FSM) в SystemVerilog коде.

Ожидаемый формат модуля (минимальный), который даёт CompleteASTService:

module: Dict с ключами:
  - "name": str
  - "signals": [{"name", "type", "width", ...}, ...]
  - "parameters": [{"name", "value"}, ...]
  - "always_blocks": [
      {
        "sensitivity": str,
        "assignments": [{"left", "right", "line", "op"}, ...]
      }, ...
    ]
  - (опционально) "enums": [
      {
        "name": str,
        "members": [str, ...],
        ...
      }, ...
    ]
  - (опционально) "fsm_states": [
      {"name": str, "enum": str, "type": "enum_member", "source": "enum"}, ...
    ]
"""

from typing import Any, Dict, List, Optional, Tuple
import string


class FSMDetectorService:
    """Сервис для детектирования конечных автоматов"""
    
    def __init__(self):
        self._fsm_patterns = self._init_fsm_patterns()
    
    def _init_fsm_patterns(self) -> Dict[str, Any]:
        """Инициализация паттернов для детектирования FSM"""
        return {
            "state_variables": {
                "state",
                "current_state",
                "next_state",
                "new_state",
                "fsm_state",
                "ctrl_state",
                "present_state",
                "future_state",
            },
            "state_enum_prefixes": {"state_", "st_", "fsm_", "s_"},
            "state_keywords": {
                "IDLE",
                "READY",
                "BUSY",
                "WAIT",
                "DONE",
                "ERROR",
                "INIT",
                "START",
                "STOP",
                "RUN",
                "PAUSE",
                "RESET",
                "WORK",
                "FINISH",
            },
            "transition_keywords": {"case", "if", "else if"},
            "state_assignment_operators": {"<=", "="},
            "reset_patterns": ["rst", "reset", "rst_n"],
            "clock_patterns": ["clk", "clock"],
        }
    
    # ======================================================================
    # ПУБЛИЧНЫЙ МЕТОД
    # ======================================================================

    def detect_finite_state_machines(self, module: Dict[str, Any], tree) -> Dict[str, Any]:
        """Детектирование конечных автоматов в модуле"""
        fsm_info: Dict[str, Any] = {
            "detected": False,
            "type": "unknown",
            "states": [],
            "transitions": [],
            "state_variables": [],
            "reset_condition": "",
            "clock_signal": "",
            "always_blocks": module.get("always_blocks", []),
        }

        # 1. Поиск переменных состояния
        state_vars = self._find_state_variables(module)
        if not state_vars:
            return fsm_info

        fsm_info["detected"] = True
        fsm_info["state_variables"] = state_vars

        always_blocks = module.get("always_blocks", [])

        # 2. Определение типа FSM
        fsm_type = self._determine_fsm_type(always_blocks, state_vars)
        fsm_info["type"] = fsm_type

        # 3. Извлечение состояний
        states = self._extract_states(module, tree, state_vars)
        fsm_info["states"] = states

        # 4. Извлечение переходов
        transitions = self._extract_transitions(always_blocks, state_vars, states)
        fsm_info["transitions"] = transitions

        # 5. Поиск reset/clock
        reset_cond, clock_signal = self._find_reset_and_clock(always_blocks)
        fsm_info["reset_condition"] = reset_cond
        fsm_info["clock_signal"] = clock_signal

        return fsm_info

    # ======================================================================
    # ПОИСК ПЕРЕМЕННЫХ СОСТОЯНИЙ
    # ======================================================================

    def _find_state_variables(self, module: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Поиск переменных состояний с улучшенной эвристикой"""
        state_vars: List[Dict[str, Any]] = []
        
        # Поиск в сигналах
        for signal in module.get("signals", []) or []:
            if not isinstance(signal, dict):
                continue
            name_raw = signal.get("name", "")
            signal_name = name_raw.lower()

            matched_pattern = None
            for pattern in self._fsm_patterns["state_variables"]:
                if pattern in signal_name:
                    matched_pattern = pattern
                    break
            
            matched_prefix = None
            if not matched_pattern:
                for prefix in self._fsm_patterns["state_enum_prefixes"]:
                    if signal_name.startswith(prefix):
                        matched_prefix = prefix
                        break
            
            if matched_pattern or matched_prefix:
                state_vars.append(
                    {
                        "name": name_raw,
                        "type": "signal",
                        "width": signal.get("width", ""),
                        "pattern_match": matched_pattern or f"prefix_{matched_prefix}",
                    }
                )

        # Поиск typedef/enum переменных
        for typedef in module.get("typedefs", []) or []:
            if not isinstance(typedef, dict):
                continue
            typedef_name = typedef.get("name", "").lower()
            if any(pat in typedef_name for pat in self._fsm_patterns["state_variables"]):
                state_vars.append(
                    {
                        "name": typedef.get("name", ""),
                        "type": "typedef",
                        "definition": typedef.get("definition", ""),
                    }
                )
        
        return state_vars

    # ======================================================================
    # ОПРЕДЕЛЕНИЕ ТИПА FSM
    # ======================================================================

    def _determine_fsm_type(self, always_blocks: List[Dict], state_vars: List[Dict]) -> str:
        """Определение типа FSM (Moore/Mealy/Hybrid)"""
        if not always_blocks:
            return "unknown"
        
        state_reg_blocks = 0
        comb_blocks = 0
        output_blocks = 0
        
        for block in always_blocks:
            if not isinstance(block, dict):
                continue
            sensitivity = str(block.get("sensitivity", "")).lower()
            assignments = block.get("assignments", []) or []
            
            is_clocked = any(pattern in sensitivity for pattern in self._fsm_patterns["clock_patterns"])
            
            if is_clocked:
                for assign in assignments:
                    left_var = str(assign.get("left", "")).lower()
                    if any(sv["name"].lower() in left_var for sv in state_vars):
                        state_reg_blocks += 1
                        break
            
            if sensitivity == "@*" or "always_comb" in sensitivity:
                comb_blocks += 1
                for assign in assignments:
                    right_expr = str(assign.get("right", "")).lower()
                    if any(sv["name"].lower() in right_expr for sv in state_vars):
                        output_blocks += 1
                        break
        
        if state_reg_blocks > 0 and comb_blocks > 0:
            return "mealy"
        elif state_reg_blocks > 0 and output_blocks > 0:
            return "moore"
        elif state_reg_blocks > 0:
            return "registered"
        else:
            return "combinational"

    # ======================================================================
    # ИЗВЛЕЧЕНИЕ СОСТОЯНИЙ
    # ======================================================================

    def _extract_states(
        self,
        module: Dict[str, Any],
        tree,
        state_vars: List[Dict],
    ) -> List[Dict[str, Any]]:
        """
        Извлечение состояний FSM.

        Приоритет:
          1) module["fsm_states"] (заполняется CompleteASTService из enum'ов)
          2) module["enums"] (если есть members)
          3) параметры с "говорящими" именами (IDLE/RUN/...),
          4) эвристики по присваиваниям и case,
          5) сигналы того же разряда, что state/new_state (наш случай).
        """
        states: List[Dict[str, Any]] = []

        # 1) fsm_states от CompleteASTService
        fsm_states = module.get("fsm_states") or []
        for st in fsm_states:
            if not isinstance(st, dict):
                continue
            name = st.get("name")
            if not name:
                continue
            states.append(
                {
                    "name": name,
                    "type": "enum_member",
                    "enum": st.get("enum", ""),
                    "source": st.get("source", "enum"),
                }
            )

        # 2) enums, прикреплённые к модулю
        enums = module.get("enums") or []
        for en in enums:
            if not isinstance(en, dict):
                continue
            enum_name = en.get("name", "anonymous_enum")
            members = en.get("members") or []
            for mem in members:
                states.append(
                    {
                        "name": mem,
                        "type": "enum_member",
                        "enum": enum_name,
                        "source": "enum",
                    }
                )

        # 3) параметры с именами, похожими на состояния
        for param in module.get("parameters", []) or []:
            if not isinstance(param, dict):
                continue
            param_name = param.get("name", "")
            param_value = param.get("value", "")
            if any(kw in param_name.upper() for kw in self._fsm_patterns["state_keywords"]):
                states.append(
                    {
                        "name": param_name,
                        "type": "parameter",
                        "value": param_value,
                        "source": "parameter",
                    }
                )

        # 4) из присваиваний/кейсов по старым эвристикам
        states.extend(self._extract_states_from_assignments(module))
        states.extend(self._extract_states_from_case_statements(module, tree))

        # 5) дополнительные состояния по сигналам того же разряда, что state-переменные
        states.extend(self._discover_states_from_signals(module, tree, state_vars))

        # Дедуп по имени
        dedup: Dict[str, Dict[str, Any]] = {}
        for st in states:
            name = st.get("name")
            if not name:
                continue
            if name not in dedup:
                dedup[name] = st
        return list(dedup.values())

    def _discover_states_from_signals(
        self,
        module: Dict[str, Any],
        tree,
        state_vars: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Важно для твоего примера: в AST enum-константы попали как сигналы:
        IDLE, F1, F0, S1, S0, state, new_state.

        Логика:
          - берём ширину state/new_state,
          - среди signals выбираем те, у кого такая же ширина,
          - отбрасываем сами state/new_state,
          - оставляем имена, похожие на константы (буквы+цифры+_ и есть хотя бы одна буква),
          - проверяем, что имя реально используется в тексте модуля,
          - считаем их состояниями.
        """
        discovered: List[Dict[str, Any]] = []

        # ширины state-переменных
        state_widths = set()
        state_names_lower = set()
        for sv in state_vars:
            if sv.get("type") != "signal":
                continue
            state_widths.add(sv.get("width", ""))
            state_names_lower.add(sv.get("name", "").lower())

        if not state_widths:
            return discovered

        module_text_up = self._get_module_text(module, tree).upper()

        valid_chars = set(string.ascii_letters + string.digits + "_")

        for sig in module.get("signals", []) or []:
            if not isinstance(sig, dict):
                continue
            name = sig.get("name", "")
            if not name:
                continue
            name_low = name.lower()
            if name_low in state_names_lower:
                # это сами state/new_state
                continue

            width = sig.get("width", "")
            if width not in state_widths:
                # другой разряд — маловероятно, что это код состояния
                continue

            # имя должно состоять из допустимых символов и содержать хотя бы одну букву
            if not all(ch in valid_chars for ch in name):
                continue
            if not any(ch.isalpha() for ch in name):
                continue

            # должно реально использоваться в модуле
            if name.upper() not in module_text_up:
                continue

            discovered.append(
                {
                    "name": name,
                    "type": "inferred_signal",
                    "width": width,
                    "source": "signal_usage",
                }
            )

        return discovered

    def _find_module_enums(self, module: Dict[str, Any], tree) -> List[List[Dict]]:
        """
        Старый путь извлечения enum'ов по CST.
        Сейчас основной источник enum-состояний — module["fsm_states"]/module["enums"],
        но оставляем как fallback.
        """
        enums: List[List[Dict]] = []

        # 1) если enums уже прикреплены к модулю
        module_enums = module.get("enums") or []
        if module_enums:
            for en in module_enums:
                if not isinstance(en, dict):
                    continue
                enum_name = en.get("name", "anonymous_enum")
                members = en.get("members") or []
                enum_states: List[Dict] = []
                for mem in members:
                    enum_states.append(
                        {
                            "name": mem,
                            "type": "enum_member",
                            "enum_type": enum_name,
                            "source": "enum",
                        }
                    )
                if enum_states:
                    enums.append(enum_states)
            return enums

        # 2) fallback через cst_service
        try:
            from cst_service import find_all, first_identifier_text
        except ImportError:
            return enums
        
        root = tree.root
        module_text = self._get_module_text(module, tree)

        for enum_node in find_all(root, "EnumType"):
            enum_name = first_identifier_text(enum_node) or "anonymous"
            if enum_name and enum_name not in module_text:
                continue

            enum_states: List[Dict] = []
            for enumerator in find_all(enum_node, "Enumerator"):
                state_name = first_identifier_text(enumerator)
                if state_name:
                    enum_states.append(
                        {
                            "name": state_name,
                            "type": "enum_member",
                            "enum_type": enum_name,
                            "source": "typedef_enum",
                        }
                    )
            if enum_states:
                enums.append(enum_states)
        
        return enums

    def _get_module_text(self, module: Dict[str, Any], tree) -> str:
        """Получить текстовое представление модуля (простая эвристика)"""
        try:
            from cst_service import find_all, first_identifier_text, collect_identifiers_inline
        except ImportError:
            return ""
        
        module_name = module.get("name", "")
        root = tree.root
        for node in find_all(root, "ModuleDeclaration"):
            if first_identifier_text(node) == module_name:
                return collect_identifiers_inline(node) or ""
        return ""

    def _extract_states_from_assignments(self, module: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Извлечение состояний из присваиваний по ключевым словам (IDLE/READY/...)"""
        states: List[Dict[str, Any]] = []
        
        for block in module.get("always_blocks", []) or []:
            if not isinstance(block, dict):
                continue
            for assign in block.get("assignments", []) or []:
                right_side = str(assign.get("right", ""))
                for keyword in self._fsm_patterns["state_keywords"]:
                    if keyword.upper() in right_side.upper():
                        states.append(
                            {
                                "name": keyword,
                                "type": "inferred",
                                "source": f"assignment: {assign.get('left', '?')}",
                                "context": right_side,
                            }
                        )
        
        return states

    def _extract_states_from_case_statements(self, module: Dict[str, Any], tree) -> List[Dict[str, Any]]:
        """Извлечение состояний из case по ключевым словам (fallback)"""
        states: List[Dict[str, Any]] = []
        module_text = self._get_module_text(module, tree).upper()
        
        if not module_text:
            return states
        
        for keyword in self._fsm_patterns["state_keywords"]:
            kw = keyword.upper()
            if kw in module_text and f"CASE {kw}" in module_text:
                states.append(
                    {
                        "name": keyword,
                        "type": "case_branch",
                        "source": "case_statement",
                    }
                )
        
        return states

    # ======================================================================
    # ИЗВЛЕЧЕНИЕ ПЕРЕХОДОВ
    # ======================================================================

    def _extract_transitions(
        self,
        always_blocks: List[Dict],
        state_vars: List[Dict],
        states: List[Dict],
    ) -> List[Dict[str, Any]]:
        """Извлечение переходов между состояниями (пока упрощённо)"""
        transitions: List[Dict[str, Any]] = []
        state_names = {st["name"] for st in states if "name" in st}

        for block in always_blocks or []:
            if not isinstance(block, dict):
                continue

            sensitivity = str(block.get("sensitivity", "")).lower()
            assignments = block.get("assignments", []) or []

            is_clocked = any(p in sensitivity for p in self._fsm_patterns["clock_patterns"])

            for assign in assignments:
                if not isinstance(assign, dict):
                    continue
                left_var = str(assign.get("left", ""))
                right_expr = str(assign.get("right", ""))

                # Присваиваем ли мы переменную состояния?
                if not any(sv["name"].lower() in left_var.lower() for sv in state_vars):
                    continue

                from_state = self._infer_from_state(block, state_vars)
                to_state = self._extract_state_from_expression(right_expr, states, state_names)

                # ВАЖНО: игнорируем переходы в unknown_state (например state <= new_state;)
                if to_state == "unknown_state":
                    continue

                condition = self._extract_transition_condition(block, state_vars)

                transitions.append(
                    {
                        "from_state": from_state,
                        "to_state": to_state,
                        "condition": condition,
                        "type": "clocked" if is_clocked else "combinational",
                        "sensitivity": sensitivity,
                        "assignment": f"{left_var} = {right_expr}",
                    }
                )
        
        return transitions

    def _infer_from_state(self, always_block: Dict, state_vars: List[Dict]) -> str:
        """Вывод исходного состояния из контекста (очень упрощённо)"""
        sensitivity = str(always_block.get("sensitivity", ""))
        if "posedge" in sensitivity or "negedge" in sensitivity:
            return "current_state"
        return "any_state"

    def _extract_state_from_expression(
        self,
        expression: str,
        states: List[Dict],
        state_names: Optional[set] = None,
    ) -> str:
        """Извлечение идентификатора состояния из выражения"""
        expr_up = expression.upper()

        # Сначала ищем среди известных состояний
        for st in states:
            name = st.get("name")
            if not name:
                continue
            name_up = name.upper()
            if f" {name_up} " in f" {expr_up} ":
                return name
            if expr_up.endswith(name_up) or expr_up.startswith(name_up):
                if name_up in expr_up:
                    return name

        # Затем просто по имени
        if state_names:
            for nm in state_names:
                if nm and nm.upper() in expr_up:
                    return nm

        if "DEFAULT" in expr_up:
            return "default"
        
        return "unknown_state"

    def _extract_transition_condition(self, always_block: Dict, state_vars: List[Dict]) -> str:
        """Извлечение условия перехода (пока только по чувствительности)"""
        sensitivity = str(always_block.get("sensitivity", "")).lower()
        
        if any(pattern in sensitivity for pattern in self._fsm_patterns["reset_patterns"]):
            return "reset"
        if any(pattern in sensitivity for pattern in self._fsm_patterns["clock_patterns"]):
            return "clock_edge"
        if sensitivity == "@*":
            return "combinational"
        
        return "unknown_condition"

    # ======================================================================
    # ПОИСК RESET И CLOCK
    # ======================================================================

    def _find_reset_and_clock(self, always_blocks: List[Dict]) -> Tuple[str, str]:
        """Поиск условия сброса и тактового сигнала"""
        reset_condition = "unknown"
        clock_signal = "unknown"
        
        for block in always_blocks or []:
            if not isinstance(block, dict):
                continue
            sensitivity = str(block.get("sensitivity", "")).lower()
            parts = sensitivity.replace("(", " ").replace(")", " ").split()

            # reset
            for pattern in self._fsm_patterns["reset_patterns"]:
                if pattern in sensitivity:
                    reset_condition = pattern
                    break

            # clock
            for pattern in self._fsm_patterns["clock_patterns"]:
                if pattern in sensitivity:
                    for i, p in enumerate(parts):
                        if "posedge" in p or "negedge" in p:
                            if i + 1 < len(parts):
                                clock_signal = parts[i + 1]
                                break
                    if clock_signal == "unknown":
                        clock_signal = pattern

        return reset_condition, clock_signal


# Создание сервиса (если кому-то нужен как синглтон)
fsm_detector = FSMDetectorService()
