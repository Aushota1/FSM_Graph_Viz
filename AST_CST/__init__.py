# -*- coding: utf-8 -*-
"""
AST_CST пакет - модули для работы с Concrete Syntax Tree и Abstract Syntax Tree
"""

from .cst_service import (
    CSTService,
    build_cst_from_text,
    kind,
    children,
    find_first,
    find_all,
    text_of,
    first_identifier_text,
    collect_identifiers_inline,
    range_width_text,
)

from .ast_service import ASTService, print_unified_ast

__all__ = [
    'CSTService',
    'build_cst_from_text',
    'kind',
    'children',
    'find_first',
    'find_all',
    'text_of',
    'first_identifier_text',
    'collect_identifiers_inline',
    'range_width_text',
    'ASTService',
    'print_unified_ast',
]

