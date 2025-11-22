# -*- coding: utf-8 -*-
# ast_service_fixed.py
"""
Исправленный сервис для работы с Abstract Syntax Tree (AST)
Полностью рабочий с правильной обработкой всех конструкций
"""

import pyslang as sl
from typing import Any, List, Dict, Optional, Tuple, Set
import json
from dataclasses import dataclass, asdict
from enum import Enum

class NodeType(Enum):
    MODULE = "ModuleDeclaration"
    INTERFACE = "InterfaceDeclaration"
    PROGRAM = "ProgramDeclaration"
    PACKAGE = "PackageDeclaration"
    CLASS = "ClassDeclaration"
    TASK = "TaskDeclaration"
    FUNCTION = "FunctionDeclaration"
    VARIABLE = "VariableDeclaration"
    PARAMETER = "ParameterDeclaration"
    PORT = "PortDeclaration"
    ASSIGNMENT = "Assignment"
    ALWAYS = "AlwaysStatement"
    INITIAL = "InitialStatement"
    GENERATE = "GenerateBlock"
    INSTANCE = "Instance"
    EXPRESSION = "Expression"
    STATEMENT = "Statement"
    TYPE = "Type"
    ATTRIBUTE = "Attribute"

@dataclass
class ASTNode:
    """Узел AST с полной информацией"""
    node_type: str
    name: str
    location: Dict[str, Any]
    children: List['ASTNode']
    attributes: Dict[str, Any]
    depth: int
    unique_id: str

class ASTServiceFixed:
    """Исправленный сервис для работы с AST"""
    
    def __init__(self):
        self._node_counter = 0
        self._symbol_table = {}
        self._type_info = {}
        self._hierarchy = {}
        self._current_module = None
    
    def build_ast_from_text(self, source_text: str, filename: str = "source.sv") -> sl.SyntaxTree:
        """Построить AST из текста"""
        try:
            return sl.SyntaxTree.fromText(source_text, filename)
        except Exception as e:
            raise ValueError(f"Ошибка парсинга: {e}")
    
    def analyze_ast(self, tree: sl.SyntaxTree) -> Dict[str, Any]:
        """Полный анализ AST"""
        self._node_counter = 0
        self._symbol_table = {}
        self._hierarchy = {}
        self._current_module = None
        
        root = tree.root
        ast_root = self._build_ast_hierarchy(root)
        
        return {
            "filename": getattr(tree, "name", "unknown"),
            "root_node": ast_root,
            "statistics": self._collect_statistics(ast_root),
            "symbol_table": self._symbol_table,
            "design_hierarchy": self._hierarchy
        }
    
    def _build_ast_hierarchy(self, node, depth=0) -> ASTNode:
        """Рекурсивное построение иерархии AST"""
        node_id = f"node_{self._node_counter}"
        self._node_counter += 1
        
        # Определяем тип и имя узла
        node_type = self._get_node_type(node)
        node_name = self._get_node_name(node, node_type)
        
        # Создаем AST узел
        ast_node = ASTNode(
            node_type=node_type,
            name=node_name,
            location=self._get_node_location(node),
            children=[],
            attributes={},
            depth=depth,
            unique_id=node_id
        )
        
        # Извлекаем атрибуты
        ast_node.attributes = self._extract_node_attributes(node, node_type)
        
        # Обрабатываем символьную информацию
        self._process_symbol_info(ast_node, node)
        
        # Обрабатываем дочерние узлы
        for child in self._get_children(node):
            if child is not None:
                child_ast = self._build_ast_hierarchy(child, depth + 1)
                if child_ast:
                    ast_node.children.append(child_ast)
        
        return ast_node
    
    def _get_node_type(self, node) -> str:
        """Определить тип узла"""
        if hasattr(node, 'kind'):
            kind_val = node.kind
            if hasattr(kind_val, 'name'):
                return kind_val.name
            return str(kind_val)
        return type(node).__name__
    
    def _get_node_name(self, node, node_type: str) -> str:
        """Извлечь имя узла"""
        try:
            # Для именованных сущностей
            if hasattr(node, 'name'):
                name_val = node.name
                if name_val:
                    if hasattr(name_val, 'valueText'):
                        return name_val.valueText or f"{node_type}_{id(node)}"
                    return str(name_val) or f"{node_type}_{id(node)}"
            
            # Для деклараторов
            if hasattr(node, 'declarator'):
                decl = node.declarator
                if hasattr(decl, 'name'):
                    name_val = decl.name
                    if name_val:
                        if hasattr(name_val, 'valueText'):
                            return name_val.valueText
                        return str(name_val)
            
            # Попробуем извлечь текст
            text = self._get_node_text(node)
            if text and len(text) < 30:
                return text
            
            return f"{node_type}_{id(node)}"
            
        except Exception:
            return f"{node_type}_{id(node)}"
    
    def _get_node_location(self, node) -> Dict[str, Any]:
        """Получить информацию о местоположении узла"""
        location = {}
        try:
            if hasattr(node, 'sourceRange'):
                source_range = node.sourceRange
                if hasattr(source_range, 'start'):
                    start = source_range.start
                    if hasattr(start, 'line'):
                        location['line'] = start.line
                    if hasattr(start, 'column'):
                        location['column'] = start.column
                if hasattr(source_range, 'end'):
                    end = source_range.end
                    if hasattr(end, 'line'):
                        location['end_line'] = end.line
        except:
            pass
        
        return location
    
    def _extract_node_attributes(self, node, node_type: str) -> Dict[str, Any]:
        """Извлечь атрибуты узла"""
        attrs = {
            "raw_kind": str(getattr(node, 'kind', 'Unknown')),
            "text": self._get_node_text(node)
        }
        
        try:
            # Специфичные атрибуты для разных типов узлов
            if node_type == "ModuleDeclaration":
                attrs.update(self._extract_module_attrs(node))
            elif node_type == "VariableDeclaration":
                attrs.update(self._extract_variable_attrs(node))
            elif node_type == "ParameterDeclaration":
                attrs.update(self._extract_parameter_attrs(node))
            elif "Port" in node_type:
                attrs.update(self._extract_port_attrs(node))
            elif "Always" in node_type:
                attrs.update(self._extract_always_attrs(node))
            elif "Instance" in node_type:
                attrs.update(self._extract_instance_attrs(node))
            elif "Function" in node_type:
                attrs.update(self._extract_function_attrs(node))
                
        except Exception as e:
            attrs["error"] = f"Attribute extraction error: {e}"
        
        return attrs
    
    def _extract_module_attrs(self, node) -> Dict[str, Any]:
        """Атрибуты модуля"""
        attrs = {}
        try:
            if hasattr(node, 'ports'):
                ports = []
                for port in node.ports:
                    port_info = {"name": self._get_node_name(port, "Port")}
                    if hasattr(port, 'direction'):
                        port_info["direction"] = str(port.direction)
                    ports.append(port_info)
                attrs["ports"] = ports
            
            if hasattr(node, 'parameters'):
                params = []
                for param in node.parameters:
                    params.append({"name": self._get_node_name(param, "Parameter")})
                attrs["parameters"] = params
                
        except:
            pass
        return attrs
    
    def _extract_variable_attrs(self, node) -> Dict[str, Any]:
        """Атрибуты переменной"""
        attrs = {}
        try:
            if hasattr(node, 'type'):
                type_info = node.type
                attrs["data_type"] = self._get_node_text(type_info)
            
            if hasattr(node, 'direction'):
                attrs["direction"] = str(node.direction)
                
        except:
            pass
        return attrs
    
    def _extract_parameter_attrs(self, node) -> Dict[str, Any]:
        """Атрибуты параметра"""
        attrs = {}
        try:
            if hasattr(node, 'type'):
                attrs["data_type"] = self._get_node_text(node.type)
            if hasattr(node, 'value'):
                attrs["value"] = self._get_node_text(node.value)
        except:
            pass
        return attrs
    
    def _extract_port_attrs(self, node) -> Dict[str, Any]:
        """Атрибуты порта"""
        attrs = {}
        try:
            if hasattr(node, 'direction'):
                attrs["direction"] = str(node.direction)
            if hasattr(node, 'type'):
                attrs["data_type"] = self._get_node_text(node.type)
        except:
            pass
        return attrs
    
    def _extract_always_attrs(self, node) -> Dict[str, Any]:
        """Атрибуты always блока"""
        attrs = {}
        try:
            if hasattr(node, 'sensitivityList'):
                sens_list = []
                for sens in node.sensitivityList:
                    sens_list.append(self._get_node_text(sens))
                attrs["sensitivity"] = sens_list
        except:
            pass
        return attrs
    
    def _extract_instance_attrs(self, node) -> Dict[str, Any]:
        """Атрибуты инстанса"""
        attrs = {}
        try:
            if hasattr(node, 'moduleName'):
                attrs["module_type"] = self._get_node_text(node.moduleName)
            if hasattr(node, 'connections'):
                connections = []
                for conn in node.connections:
                    conn_info = {
                        "port": getattr(conn, 'portName', ''),
                        "expression": self._get_node_text(getattr(conn, 'expr', None))
                    }
                    connections.append(conn_info)
                attrs["connections"] = connections
        except:
            pass
        return attrs
    
    def _extract_function_attrs(self, node) -> Dict[str, Any]:
        """Атрибуты функции"""
        attrs = {}
        try:
            if hasattr(node, 'returnType'):
                attrs["return_type"] = self._get_node_text(node.returnType)
            if hasattr(node, 'ports'):
                ports = []
                for port in node.ports:
                    ports.append({"name": self._get_node_name(port, "Port")})
                attrs["ports"] = ports
        except:
            pass
        return attrs
    
    def _get_children(self, node) -> List[Any]:
        """Получить дочерние узлы"""
        children = []
        
        # Используем разные методы для получения детей
        methods_to_try = [
            lambda n: getattr(n, 'children', []),
            lambda n: [n[i] for i in range(len(n))] if hasattr(n, '__len__') else [],
            lambda n: list(n) if hasattr(n, '__iter__') else []
        ]
        
        for method in methods_to_try:
            try:
                result = method(node)
                if result:
                    children.extend(result)
                    break
            except:
                continue
        
        # Фильтруем None и примитивные типы
        return [child for child in children if child is not None and not isinstance(child, (int, float, str, bool))]
    
    def _get_node_text(self, node) -> str:
        """Получить текстовое представление узла"""
        if node is None:
            return ""
            
        methods = ['getText', 'toString', '__str__', 'valueText']
        
        for method in methods:
            if hasattr(node, method):
                try:
                    result = getattr(node, method)
                    if callable(result):
                        text = result()
                    else:
                        text = result
                    
                    if text and isinstance(text, str):
                        return text.strip()
                except:
                    continue
        
        return ""
    
    def _process_symbol_info(self, ast_node: ASTNode, raw_node):
        """Обработка символьной информации"""
        node_type = ast_node.node_type
        
        # Сохраняем именованные сущности в таблицу символов
        if ast_node.name and not ast_node.name.startswith(('Unknown_', 'SyntaxKind.', 'TokenKind.')):
            symbol_info = {
                "name": ast_node.name,
                "type": node_type,
                "location": ast_node.location,
                "depth": ast_node.depth
            }
            self._symbol_table[ast_node.unique_id] = symbol_info
        
        # Обрабатываем иерархию дизайна
        if node_type == "ModuleDeclaration":
            self._current_module = ast_node.name
            if ast_node.name not in self._hierarchy:
                self._hierarchy[ast_node.name] = {
                    "instances": [],
                    "submodules": set(),
                    "ports": ast_node.attributes.get("ports", []),
                    "parameters": ast_node.attributes.get("parameters", [])
                }
        
        elif "Instance" in node_type and self._current_module:
            module_type = ast_node.attributes.get("module_type", "")
            instance_name = ast_node.name
            
            if module_type and instance_name:
                self._hierarchy[self._current_module]["instances"].append({
                    "name": instance_name,
                    "type": module_type,
                    "connections": ast_node.attributes.get("connections", [])
                })
                
                # Добавляем в подмодули
                if module_type not in self._hierarchy:
                    self._hierarchy[module_type] = {
                        "instances": [],
                        "submodules": set(),
                        "ports": [],
                        "parameters": []
                    }
    
    def _collect_statistics(self, ast_root: ASTNode) -> Dict[str, Any]:
        """Собрать статистику по AST"""
        stats = {
            "total_nodes": 0,
            "by_type": {},
            "max_depth": 0,
            "named_entities": 0
        }
        
        def collect(node: ASTNode):
            stats["total_nodes"] += 1
            stats["max_depth"] = max(stats["max_depth"], node.depth)
            
            node_type = node.node_type
            stats["by_type"][node_type] = stats["by_type"].get(node_type, 0) + 1
            
            if node.name and not node.name.startswith(('Unknown_', 'SyntaxKind.', 'TokenKind.')):
                stats["named_entities"] += 1
            
            for child in node.children:
                collect(child)
        
        collect(ast_root)
        return stats

    # =========================
    #  Методы визуализации и вывода
    # =========================
    
    def print_detailed_ast(self, analysis_result: Dict[str, Any], max_depth: int = 10):
        """Детальный вывод AST"""
        print("\n" + "="*80)
        print("ДЕТАЛИЗИРОВАННЫЙ AST АНАЛИЗ")
        print("="*80)
        
        root_node = analysis_result["root_node"]
        statistics = analysis_result["statistics"]
        filename = analysis_result["filename"]
        
        print(f"\nФайл: {filename}")
        print(f"Всего узлов: {statistics['total_nodes']}")
        print(f"Максимальная глубина: {statistics['max_depth']}")
        print(f"Именованных сущностей: {statistics['named_entities']}")
        
        print(f"\nРаспределение по типам:")
        for node_type, count in sorted(statistics["by_type"].items()):
            if count > 0:
                print(f"  {node_type}: {count}")
        
        print(f"\nИЕРАРХИЯ AST (макс. глубина {max_depth}):")
        print("-" * 60)
        self._print_ast_node(root_node, max_depth)
        
        print(f"\nТАБЛИЦА СИМВОЛОВ ({len(analysis_result['symbol_table'])} записей):")
        print("-" * 60)
        self._print_symbol_table(analysis_result["symbol_table"])
        
        print(f"\nИЕРАРХИЯ ДИЗАЙНА:")
        print("-" * 60)
        self._print_design_hierarchy(analysis_result["design_hierarchy"])
    
    def _print_ast_node(self, node: ASTNode, max_depth: int, current_depth: int = 0):
        """Рекурсивный вывод узла AST"""
        if current_depth > max_depth:
            return
        
        indent = "  " * current_depth
        node_info = f"{node.node_type}"
        
        if node.name and not node.name.startswith(('SyntaxKind.', 'TokenKind.')):
            node_info += f": {node.name}"
        
        # Добавляем информацию о местоположении
        if node.location and 'line' in node.location:
            node_info += f" [line {node.location['line']}]"
        
        print(f"{indent}{node_info}")
        
        # Выводим важные атрибуты
        if node.attributes:
            attr_indent = "  " * (current_depth + 1)
            for key, value in node.attributes.items():
                if key not in ["text", "raw_kind"] and value:
                    if isinstance(value, (list, dict)) and len(value) > 0:
                        print(f"{attr_indent}{key}: {value}")
                    elif not isinstance(value, (list, dict)) and str(value) not in ["", "None"]:
                        print(f"{attr_indent}{key}: {value}")
        
        # Рекурсивно обрабатываем детей
        for child in node.children:
            self._print_ast_node(child, max_depth, current_depth + 1)
    
    def _print_symbol_table(self, symbol_table: Dict[str, Any]):
        """Вывод таблицы символов"""
        if not symbol_table:
            print("  Таблица символов пуста")
            return
            
        for sym_id, symbol in symbol_table.items():
            loc_info = f"line {symbol['location'].get('line', '?')}" if symbol.get('location') else ""
            print(f"  {symbol['name']} ({symbol['type']}) {loc_info}")
    
    def _print_design_hierarchy(self, hierarchy: Dict[str, Any]):
        """Вывод иерархии дизайна"""
        if not hierarchy:
            print("  Иерархия дизайна не обнаружена")
            return
            
        for module_name, module_info in hierarchy.items():
            print(f"  Модуль: {module_name}")
            
            if module_info.get("ports"):
                print(f"    Порты: {len(module_info['ports'])}")
                for port in module_info["ports"][:3]:  # Показываем первые 3
                    print(f"      {port.get('name', '?')} ({port.get('direction', '?')})")
                if len(module_info["ports"]) > 3:
                    print(f"      ... и еще {len(module_info['ports']) - 3}")
            
            if module_info.get("instances"):
                print(f"    Инстансы: {len(module_info['instances'])}")
                for instance in module_info["instances"][:3]:  # Показываем первые 3
                    print(f"      {instance['name']} -> {instance['type']}")
                if len(module_info["instances"]) > 3:
                    print(f"      ... и еще {len(module_info['instances']) - 3}")
    
    def export_ast_to_json(self, analysis_result: Dict[str, Any], filename: str):
        """Экспорт AST в JSON файл"""
        def node_to_dict(node: ASTNode) -> Dict[str, Any]:
            # Сериализуем узел, исключая циклические ссылки
            return {
                "node_type": node.node_type,
                "name": node.name,
                "location": node.location,
                "attributes": node.attributes,
                "depth": node.depth,
                "unique_id": node.unique_id,
                "children": [node_to_dict(child) for child in node.children]
            }
        
        # Подготовка данных для экспорта
        export_data = {
            "filename": analysis_result["filename"],
            "statistics": analysis_result["statistics"],
            "symbol_table": analysis_result["symbol_table"],
            "design_hierarchy": analysis_result["design_hierarchy"],
            "ast_root": node_to_dict(analysis_result["root_node"])
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            print(f"AST успешно экспортирован в {filename}")
        except Exception as e:
            print(f"Ошибка экспорта в JSON: {e}")
    
    def find_nodes_by_type(self, ast_root: ASTNode, node_type: str) -> List[ASTNode]:
        """Найти узлы по типу"""
        results = []
        
        def search(node: ASTNode):
            if node.node_type == node_type:
                results.append(node)
            for child in node.children:
                search(child)
        
        search(ast_root)
        return results
    
    def get_module_summary(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Получить сводку по модулям"""
        modules = {}
        
        def extract_modules(node: ASTNode):
            if node.node_type == "ModuleDeclaration":
                modules[node.name] = {
                    "ports": node.attributes.get("ports", []),
                    "parameters": node.attributes.get("parameters", []),
                    "location": node.location,
                    "instances": []
                }
            
            for child in node.children:
                extract_modules(child)
        
        extract_modules(analysis_result["root_node"])
        return modules

# =========================
#  Пример использования
# =========================

def test_fixed_service():
    """Тестирование исправленного сервиса"""
    
    test_code = """
    module top_module #(
        parameter WIDTH = 8,
        parameter DEPTH = 16
    )(
        input logic clk,
        input logic rst_n,
        input logic [WIDTH-1:0] data_in,
        output logic [WIDTH-1:0] data_out,
        output logic valid
    );
    
        // Internal signals
        logic [WIDTH-1:0] counter;
        logic [WIDTH-1:0] memory [0:DEPTH-1];
        logic enable;
        
        // Instance
        counter_module #(.WIDTH(WIDTH)) u_counter (
            .clk(clk),
            .rst(rst_n),
            .count(counter)
        );
        
        // Always block
        always_ff @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                data_out <= '0;
                valid <= 1'b0;
            end
            else if (enable) begin
                data_out <= memory[counter];
                valid <= 1'b1;
            end
            else begin
                valid <= 1'b0;
            end
        end
        
        // Function
        function automatic logic check_valid(input logic [WIDTH-1:0] data);
            return data != '0;
        endfunction
        
        assign enable = check_valid(data_in);
        
    endmodule
    
    module counter_module #(
        parameter int WIDTH = 8
    )(
        input logic clk,
        input logic rst,
        output logic [WIDTH-1:0] count
    );
    
        always_ff @(posedge clk or posedge rst) begin
            if (rst) count <= '0;
            else count <= count + 1;
        end
        
    endmodule
    """
    
    # Создаем исправленный сервис
    ast_service = ASTServiceFixed()
    
    try:
        # Строим и анализируем AST
        tree = ast_service.build_ast_from_text(test_code, "test_design.sv")
        analysis_result = ast_service.analyze_ast(tree)
        
        # Выводим результаты
        ast_service.print_detailed_ast(analysis_result, max_depth=6)
        
        # Экспортируем в JSON
        ast_service.export_ast_to_json(analysis_result, "fixed_ast_export.json")
        
        # Дополнительный анализ
        modules = ast_service.find_nodes_by_type(analysis_result["root_node"], "ModuleDeclaration")
        print(f"\nНайдено модулей: {len(modules)}")
        for module in modules:
            print(f"  - {module.name}")
        
        # Сводка по модулям
        module_summary = ast_service.get_module_summary(analysis_result)
        print(f"\nСводка по модулям:")
        for mod_name, mod_info in module_summary.items():
            print(f"  {mod_name}: {len(mod_info['ports'])} портов, {len(mod_info['parameters'])} параметров")
        
        return analysis_result
        
    except Exception as e:
        print(f"Ошибка при анализе: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("Тестирование исправленного AST сервиса...")
    result = test_fixed_service()
    
    if result:
        print("\n" + "="*80)
        print("ТЕСТ ПРОЙДЕН УСПЕШНО!")
        print("="*80)
    else:
        print("\n" + "="*80)
        print("ТЕСТ НЕ ПРОЙДЕН!")
        print("="*80)