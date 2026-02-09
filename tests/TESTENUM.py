from AST_CST.cst_service import CSTService
from FSM_core.FindeENUM import detect_enum_variables_from_cst

code = """
package bus_defs;
  typedef enum logic [1:0] {IDLE, BUSY, ERROR} bus_state_t;
endpackage

module bus_ctrl(input logic clk);
  import bus_defs::*;

  bus_state_t bus_state;

  enum logic [1:0] {REQ, GNT} arb_state;
endmodule

class Transaction;
  typedef enum {READ, WRITE} tr_type_t;

  tr_type_t tr_type;
endclass


"""

cst_service = CSTService()
tree = cst_service.build_cst_from_text(code, "ticket.sv")

result = detect_enum_variables_from_cst(tree)

for item in result:
    print(item)
