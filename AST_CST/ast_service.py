# -*- coding: utf-8 -*-
# ast_service.py
"""
Сервис для построения Abstract Syntax Tree (AST) из CST
Извлечение семантической информации о модулях, сигналах, соединениях и т.д.
"""

from typing import Any, Dict, List, Optional
from .cst_service import CSTService, find_first, find_all, first_identifier_text, collect_identifiers_inline, range_width_text

class ASTService:
    """Сервис для построения Abstract Syntax Tree"""
    
    def build_ast_from_cst(self, tree) -> Dict[str, Any]:
        """Построить AST из CST"""
        root = tree.root
        modules = [self._parse_module(md) for md in find_all(root, "ModuleDeclaration")]
        interfaces = [self._parse_interface(x) for x in find_all(root, "InterfaceDeclaration")]
        packages = [self._parse_package(x) for x in find_all(root, "PackageDeclaration")]
        classes = [self._parse_class(x) for x in find_all(root, "ClassDeclaration")]
        typedefs, structs, enums = self._collect_types(root)

        connections = []
        for m in modules:
            for inst in m.get("instances", []):
                connections.append({
                    "type": "instance",
                    "from": m["name"],
                    "to": inst.get("type", "?"),
                    "instance_name": inst.get("name", "?")
                })

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
            "metadata": {
                "total_modules": len(modules),
                "interfaces_count": len(interfaces),
                "packages_count": len(packages),
                "classes_count": len(classes),
                "typedefs_count": len(typedefs),
            }
        }

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

# =========================
#  Утилиты печати AST
# =========================

def print_unified_ast(ast: Dict[str, Any]):
    """Печать AST в читаемом формате"""
    print("\n=== UNIFIED AST ===")
    print(f"parser_used: {ast.get('parser_used')}  |  modules: {len(ast.get('modules',[]))}")
    for m in ast.get("modules", []):
        print(f"\nMODULE {m['name']}")
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
        if m["nets"]:
            print("  NETS:")
            for n in m["nets"]:
                w = f" {n['width']}" if n['width'] else ""
                print(f"    {n['name']}{w} ({n['kind']})")
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
        if m["initial_blocks"]:
            print("  INITIAL:")
            for ib in m["initial_blocks"]:
                for asg in ib["assignments"]:
                    print(f"    {asg['left']} {asg['op']} {asg['right']}")
        if m["instances"]:
            print("  INSTANCES:")
            for inst in m["instances"]:
                print(f"    {inst['name']} : {inst['type']}")
                for c in inst.get("connections", []):
                    print(f"      .{c['port']}({c['arg']})")
        if m["generate"]:
            print("  GENERATE:")
            for g in m["generate"]:
                if g["kind"] == "if":
                    print(f"    if {g.get('cond','?')} ...")
                elif g["kind"] == "case":
                    print(f"    case {g.get('expr','?')} ...")
                else:
                    print(f"    {g['kind']} ...")

    sve = ast.get("systemverilog_elements", {})
    for k in ("interfaces","packages","classes","typedefs","structs","enums"):
        lst = sve.get(k, [])
        if lst:
            print(f"\n{k.upper()} ({len(lst)}):")
            for e in lst:
                print(f"  - {e.get('name','unnamed')}")
    conns = ast.get("connections", [])
    if conns:
        print(f"\nCONNECTIONS ({len(conns)}):")
        for c in conns:
            print(f"  {c['from']} --({c['instance_name']})--> {c['to']}")

# =========================
#  Пример использования
# =========================

def example_usage():
    """Пример использования AST сервиса"""
    
    example_code = """
    module simple_module(
        input clk,
        input rst,
        output reg [7:0] data
    );
        parameter WIDTH = 8;
        
        always @(posedge clk) begin
            if (rst) data <= 8'h0;
            else data <= data + 1;
        end
        
        sub_module u_sub(.clk(clk), .in_data(data));
    endmodule
    """
    
    # Используем CST сервис для построения CST
    from cst_service import CSTService
    cst_service = CSTService()
    tree = cst_service.build_cst_from_text(example_code, "example.sv")
    
    # Используем AST сервис для построения AST
    ast_service = ASTService()
    ast = ast_service.build_ast_from_cst(tree)
    
    # Печатаем результат
    print_unified_ast(ast)
    
    return ast

if __name__ == "__main__":
    example_usage()
    