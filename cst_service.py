# -*- coding: utf-8 -*-
# cst_service.py
"""
Сервис для работы с Concrete Syntax Tree (CST)
Только построение CST и базовые операции обхода
"""

import pyslang as sl
from typing import Any, List, Optional

# =========================
#  Утилиты для CST
# =========================

def kind(n) -> str:
    """Получить тип узла"""
    k = getattr(n, "kind", None)
    return getattr(k, "name", None) or str(k) or "Unknown"

def get_text (node):
    return collect_identifiers_inline(node)

def children(n):
    """Получить дочерние узлы"""
    for cnt_name, get_name in (("getChildCount","getChild"),("childCount","getChild")):
        if hasattr(n, cnt_name) and hasattr(n, get_name):
            try:
                cnt = int(getattr(n, cnt_name)() if callable(getattr(n, cnt_name)) else getattr(n, cnt_name))
                getter = getattr(n, get_name)
                return [getter(i) if callable(getter) else n[i] for i in range(cnt)]
            except Exception:
                pass
    if hasattr(n, "children"):
        try:
            it = n.children() if callable(n.children) else n.children
            return list(it)
        except Exception:
            pass
    try:
        return list(iter(n))
    except Exception:
        return []

def text_of(n) -> Optional[str]:
    """Получить текстовое представление узла"""
    for attr in ("valueText","getValueText","text","getText","toString","__str__"):
        if hasattr(n, attr):
            fn = getattr(n, attr)
            try:
                return str(fn() if callable(fn) else fn)
            except Exception:
                continue
    return None

def find_first(n, kind_name: str):
    """Найти первый узел указанного типа"""
    if kind(n) == kind_name:
        return n
    for ch in children(n):
        r = find_first(ch, kind_name)
        if r is not None:
            return r
    return None

def find_all(n, kind_name: str):
    """Найти все узлы указанного типа"""
    out = []
    if kind(n) == kind_name:
        out.append(n)
    for ch in children(n):
        out.extend(find_all(ch, kind_name))
    return out

def first_identifier_text(n) -> Optional[str]:
    """Получить текст первого идентификатора"""
    node = find_first(n, "Identifier")
    return text_of(node) if node is not None else None

def collect_identifiers_inline(n) -> str:
    """Собрать все идентификаторы в строку"""
    parts: List[str] = []
    def walk(x):
        t = text_of(x)
        if t and len(children(x)) == 0:
            parts.append(t)
        else:
            for c in children(x):
                walk(c)
    walk(n)
    return "".join(parts).strip()

def range_width_text(var_dim_node) -> str:
    """Извлечь текст диапазона [left:right]"""
    rng = find_first(var_dim_node, "SimpleRangeSelect")
    if not rng:
        return ""
    subs = children(rng)
    lhs_parts, rhs_parts, into_rhs = [], [], False
    for c in subs:
        kk = kind(c)
        t = text_of(c)
        if kk == "Colon":
            into_rhs = True
            continue
        if into_rhs:
            rhs_parts.append(t if t is not None else collect_identifiers_inline(c))
        else:
            lhs_parts.append(t if t is not None else collect_identifiers_inline(c))
    left_txt = "".join(p for p in lhs_parts if p) or "?"
    right_txt = "".join(p for p in rhs_parts if p) or "?"
    return f"[{left_txt}:{right_txt}]"

class CSTService:
    """Сервис для работы с Concrete Syntax Tree"""
    
    def build_cst_from_text(self, source_text: str, filename: str = "source.sv") -> sl.SyntaxTree:
        """Построить CST из текста"""
        return sl.SyntaxTree.fromText(source_text, filename)
    
    def build_compilation(self, files: dict) -> tuple:
        """Построить компиляцию из нескольких файлов"""
        comp = sl.Compilation()
        trees = []
        for name, text in files.items():
            st = sl.SyntaxTree.fromText(text, name)
            comp.addSyntaxTree(st)
            trees.append(st)
        return comp, trees
    
    def get_tree_info(self, tree: sl.SyntaxTree) -> dict:
        """Получить базовую информацию о дереве"""
        root = tree.root
        return {
            "filename": getattr(tree, "name", "unknown"),
            "root_kind": kind(root),
            "total_nodes": self._count_nodes(root),
            "modules_count": len(find_all(root, "ModuleDeclaration")),
            "interfaces_count": len(find_all(root, "InterfaceDeclaration")),
            "classes_count": len(find_all(root, "ClassDeclaration")),
        }
    
    def _count_nodes(self, node) -> int:
        """Рекурсивно посчитать количество узлов"""
        count = 1
        for child in children(node):
            count += self._count_nodes(child)
        return count
    
    def find_nodes_by_kind(self, tree: sl.SyntaxTree, kind_name: str) -> List[dict]:
        """Найти все узлы указанного типа с их позициями"""
        nodes = find_all(tree.root, kind_name)
        result = []
        for node in nodes:
            result.append({
                "kind": kind_name,
                "text": text_of(node),
                "position": self._get_node_position(node)
            })
        return result
    
    def _get_node_position(self, node) -> dict:
        """Получить позицию узла в исходном коде"""
        # Базовая реализация - можно расширить при необходимости
        return {
            "line": getattr(node, "line", None),
            "column": getattr(node, "column", None),
            "start": getattr(node, "start", None),
            "end": getattr(node, "end", None),
        }
    
    def print_tree_structure(self, tree: sl.SyntaxTree, max_depth: int = 3):
        """Напечатать структуру дерева"""
        root = tree.root
        print(f"\n=== CST STRUCTURE: {getattr(tree, 'name', 'unknown')} ===")
        self._print_node(root, 0, max_depth)
    
    def _print_node(self, node, depth: int, max_depth: int):
        """Рекурсивно напечатать узел"""
        if depth > max_depth:
            return
            
        indent = "  " * depth
        node_kind = kind(node)
        node_text = text_of(node)
        text_preview = f" - '{node_text}'" if node_text and len(node_text) < 50 else ""
        print(f"{indent}{node_kind}{text_preview}")
        
        for child in children(node):
            self._print_node(child, depth + 1, max_depth)

# =========================
#  Пример использования
# =========================

def example_usage():
    """Пример использования CST сервиса"""
    
    example_code = """
    module simple_module(input clk, input rst, output reg [7:0] data);
        always @(posedge clk) begin
            if (rst) data <= 8'h0;
            else data <= data + 1;
        end
    endmodule
    """
    
    cst_service = CSTService()
    
    # Построение CST
    tree = cst_service.build_cst_from_text(example_code, "example.sv")
    
    # Получение информации о дереве
    info = cst_service.get_tree_info(tree)
    print("CST Info:", info)
    
    # Поиск узлов определенного типа
    modules = cst_service.find_nodes_by_kind(tree, "ModuleDeclaration")
    print(f"Found {len(modules)} modules")
    
    # Печать структуры дерева
    cst_service.print_tree_structure(tree, max_depth=2)
    
    return tree

if __name__ == "__main__":
    example_usage()