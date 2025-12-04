# -*- coding: utf-8 -*-
"""
Генератор SystemVerilog кода из отредактированного FSM графа.
Использует существующие функции без изменений, только генерирует код.
"""

from typing import Dict, Any, Optional
import math


class FSMCodeGenerator:
    """
    Генератор SystemVerilog кода из отредактированного FSM графа.
    """

    def __init__(self, original_code_text: str = ""):
        self.original_code_text = original_code_text

    def generate_code_from_graph(
        self, 
        edited_graph: Dict[str, Any], 
        module_name: Optional[str] = None
    ) -> str:
        """
        Сгенерировать SystemVerilog код из отредактированного графа.

        Args:
            edited_graph: Отредактированный граф FSM
            module_name: Имя модуля для генерации

        Returns:
            Сгенерированный код SystemVerilog
        """
        # Валидация графа
        self._validate_graph(edited_graph)

        # Определить имя модуля
        if not module_name:
            scope = edited_graph.get("scope", "module fsm_example")
            # Извлечь имя модуля из scope (например, "module fsm_example" -> "fsm_example")
            parts = scope.split()
            module_name = parts[-1] if len(parts) > 1 else "fsm_example"

        # Определить стиль FSM из исходного кода или графа
        fsm_style = self._detect_fsm_style(edited_graph)

        # Генерация enum определения
        enum_code = self._generate_enum(edited_graph)

        # Генерация объявлений переменных
        var_declarations = self._generate_variable_declarations(edited_graph)

        # Генерация always_ff блока (регистр состояния)
        always_ff_code = self._generate_always_ff(edited_graph, fsm_style)

        # Генерация always_comb блока (логика переходов)
        always_comb_code = self._generate_always_comb(edited_graph, fsm_style)

        # Объединение всех частей
        full_code = self._assemble_code(
            module_name, enum_code, var_declarations,
            always_ff_code, always_comb_code
        )

        return full_code

    def _validate_graph(self, graph: Dict[str, Any]):
        """Валидация графа перед генерацией."""
        states = graph.get("states", [])
        transitions = graph.get("transitions", [])

        # Проверка, что все состояния уникальны
        if len(states) != len(set(states)):
            raise ValueError("Duplicate states found")

        # Проверка, что все переходы ссылаются на существующие состояния
        for trans in transitions:
            if trans.get("from") not in states:
                raise ValueError(f"Transition from unknown state: {trans.get('from')}")
            if trans.get("to") not in states:
                raise ValueError(f"Transition to unknown state: {trans.get('to')}")

        # Проверка наличия reset-состояния
        reset_state = graph.get("reset_state")
        if reset_state and reset_state not in states:
            raise ValueError(f"Reset state {reset_state} not in states list")

    def _detect_fsm_style(self, graph: Dict[str, Any]) -> str:
        """Определить стиль FSM из графа или исходного кода."""
        next_state_var = graph.get("next_state_var")
        if next_state_var:
            return "two_register"  # Двухвариантный FSM
        else:
            return "single_register"  # Одновариантный FSM

    def _generate_enum(self, graph: Dict[str, Any]) -> str:
        """Генерация enum определения."""
        enum_name = graph.get("enum_name", "state_t")
        states = graph.get("states", [])

        if not states:
            return f"typedef enum logic [1:0] {{}} {enum_name};"

        # Определить ширину enum
        width = self._calculate_enum_width(len(states))

        lines = [f"  typedef enum logic [{width-1}:0] {{"]
        state_lines = [f"    {state}" for state in states]
        lines.append(",\n".join(state_lines))
        lines.append(f"  }} {enum_name};")

        return "\n".join(lines)

    def _calculate_enum_width(self, num_states: int) -> int:
        """Вычислить необходимую ширину enum."""
        if num_states <= 2:
            return 1
        elif num_states <= 4:
            return 2
        elif num_states <= 8:
            return 3
        elif num_states <= 16:
            return 4
        else:
            return math.ceil(math.log2(num_states))

    def _generate_variable_declarations(self, graph: Dict[str, Any]) -> str:
        """Генерация объявлений переменных состояния."""
        enum_name = graph.get("enum_name", "state_t")
        state_var = graph.get("state_var", "state")
        next_state_var = graph.get("next_state_var")

        lines = [f"  {enum_name} {state_var};"]
        if next_state_var:
            lines.append(f"  {enum_name} {next_state_var};")

        return "\n".join(lines)

    def _generate_always_ff(
        self, 
        graph: Dict[str, Any], 
        style: str
    ) -> str:
        """Генерация always_ff блока для регистра состояния."""
        state_var = graph.get("state_var", "state")
        next_state_var = graph.get("next_state_var")
        reset_state = graph.get("reset_state")

        # Определить сигналы сброса и такта из исходного кода или использовать по умолчанию
        clock_signal = self._extract_clock_signal()
        reset_signal = self._extract_reset_signal()
        reset_polarity = self._extract_reset_polarity()

        lines = [
            f"  always_ff @(posedge {clock_signal} or {reset_polarity} {reset_signal}) begin"
        ]

        if reset_state:
            reset_condition = "!" if reset_polarity == "negedge" else ""
            lines.append(f"    if ({reset_condition}{reset_signal})")
            lines.append(f"      {state_var} <= {reset_state};")
            lines.append("    else")

        if next_state_var:
            lines.append(f"      {state_var} <= {next_state_var};")
        else:
            # Для одновариантного FSM - остаемся в текущем состоянии по умолчанию
            lines.append(f"      {state_var} <= {state_var};")

        lines.append("  end")

        return "\n".join(lines)

    def _generate_always_comb(
        self, 
        graph: Dict[str, Any], 
        style: str
    ) -> str:
        """Генерация always_comb блока для логики переходов."""
        state_var = graph.get("state_var", "state")
        next_state_var = graph.get("next_state_var")
        transitions = graph.get("transitions", [])
        states = graph.get("states", [])

        # Группировать переходы по исходному состоянию
        transitions_by_state = {}
        for trans in transitions:
            from_state = trans.get("from")
            if from_state not in transitions_by_state:
                transitions_by_state[from_state] = []
            transitions_by_state[from_state].append(trans)

        lines = ["  always_comb begin"]

        if next_state_var:
            lines.append(f"    {next_state_var} = {state_var};")

        lines.append(f"    unique case ({state_var})")

        # Генерация case-блоков для каждого состояния
        for from_state in states:
            state_transitions = transitions_by_state.get(from_state, [])

            lines.append(f"      {from_state}: begin")

            if not state_transitions:
                # Нет переходов - остаемся в текущем состоянии
                if next_state_var:
                    lines.append(f"        {next_state_var} = {from_state};")
                else:
                    lines.append(f"        {state_var} = {from_state};")
            else:
                # Есть переходы
                for i, trans in enumerate(state_transitions):
                    to_state = trans.get("to")
                    cond = trans.get("cond", "1")

                    if cond == "1" or not cond or cond == "":
                        # Безусловный переход
                        if next_state_var:
                            lines.append(f"        {next_state_var} = {to_state};")
                        else:
                            lines.append(f"        {state_var} = {to_state};")
                    else:
                        # Условный переход
                        if i == 0:
                            lines.append(f"        if ({cond})")
                        else:
                            lines.append(f"        else if ({cond})")

                        if next_state_var:
                            lines.append(f"          {next_state_var} = {to_state};")
                        else:
                            lines.append(f"          {state_var} = {to_state};")

            lines.append("      end")

        # Default case
        lines.append("      default: begin")
        if next_state_var:
            lines.append(f"        {next_state_var} = {state_var};")
        else:
            lines.append(f"        {state_var} = {state_var};")
        lines.append("      end")

        lines.append("    endcase")
        lines.append("  end")

        return "\n".join(lines)

    def _extract_clock_signal(self) -> str:
        """Извлечь имя сигнала такта из исходного кода."""
        import re
        if self.original_code_text:
            match = re.search(
                r'always_ff\s*@\s*\(posedge\s+(\w+)',
                self.original_code_text
            )
            if match:
                return match.group(1)
        return "clk"  # По умолчанию

    def _extract_reset_signal(self) -> str:
        """Извлечь имя сигнала сброса из исходного кода."""
        import re
        if self.original_code_text:
            # Ищем в always_ff @(posedge clk or posedge/negedge rst)
            match = re.search(
                r'always_ff\s*@\s*\([^)]*(?:posedge|negedge)\s+(\w+)',
                self.original_code_text
            )
            if match:
                return match.group(1)
        return "rst"  # По умолчанию

    def _extract_reset_polarity(self) -> str:
        """Извлечь полярность сигнала сброса."""
        if self.original_code_text:
            if "negedge" in self.original_code_text and "rst" in self.original_code_text.lower():
                return "negedge"
        return "posedge"

    def _assemble_code(
        self,
        module_name: str,
        enum_code: str,
        var_declarations: str,
        always_ff_code: str,
        always_comb_code: str
    ) -> str:
        """Собрать полный код модуля."""
        lines = [
            f"module {module_name} (",
            "  input  logic clk,",
            "  input  logic rst,",
            "  // TODO: add other ports as needed",
            ");",
            "",
            enum_code,
            "",
            var_declarations,
            "",
            always_ff_code,
            "",
            always_comb_code,
            "",
            f"endmodule : {module_name}"
        ]
        return "\n".join(lines)

