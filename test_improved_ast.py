# -*- coding: utf-8 -*-
# test_fsm_detection.py
"""
Тестирование улучшенного детектирования FSM
"""

from cst_service import CSTService
from ast_serviceFSM import ASTService, print_unified_ast

def test_moore_machine():
    """Тест автомата Мура с полным детектированием"""
    print("=== Testing Moore Machine FSM Detection ===")
    
    code = """
//----------------------------------------------------------------------------
// Example
//----------------------------------------------------------------------------

module serial_divisibility_by_3_using_fsm
(
  input  clk,
  input  rst,
  input  new_bit,
  output div_by_3
);

  // States
  enum logic[1:0]
  {
     mod_0 = 2'b00,
     mod_1 = 2'b01,
     mod_2 = 2'b10
  }
  state, new_state;

  // State transition logic
  always_comb
  begin
    new_state = state;

    // This lint warning is bogus because we assign the default value above
    // verilator lint_off CASEINCOMPLETE

    case (state)
      mod_0 : if(new_bit) new_state = mod_1;
              else        new_state = mod_0;
      mod_1 : if(new_bit) new_state = mod_0;
              else        new_state = mod_2;
      mod_2 : if(new_bit) new_state = mod_2;
              else        new_state = mod_1;
    endcase

    // verilator lint_on CASEINCOMPLETE

  end

  // Output logic
  assign div_by_3 = state == mod_0;

  // State update
  always_ff @ (posedge clk)
    if (rst)
      state <= mod_0;
    else
      state <= new_state;

endmodule

//----------------------------------------------------------------------------
// Task
//----------------------------------------------------------------------------

module serial_divisibility_by_5_using_fsm
(
  input  clk,
  input  rst,
  input  new_bit,
  output div_by_5
);

  // Implement a module that performs a serial test if input number is divisible by 5.
  //
  // On each clock cycle, module receives the next 1 bit of the input number.
  // The module should set output to 1 if the currently known number is divisible by 5.
  //
  // Hint: new bit is coming to the right side of the long binary number `X`.
  // It is similar to the multiplication of the number by 2*X or by 2*X + 1.
  //
  // Hint 2: As we are interested only in the remainder, all operations are performed under the modulo 5 (% 5).
  // Check manually how the remainder changes under such modulo.


endmodule
"""
    
    # Создаем CST
    cst_service = CSTService()
    tree = cst_service.build_cst_from_text(code, "moore_machine.sv")
    
    # Создаем AST с детектированием FSM
    ast_service = ASTService()
    ast = ast_service.build_ast_from_cst(tree)
    
    # Печатаем результат
    print_unified_ast(ast)
    
    # Детальная проверка FSM
    print("\n" + "="*50)
    print("DETAILED FSM ANALYSIS:")
    print("="*50)
    
    fsms = ast.get("finite_state_machines", {})
    moore_fsm = fsms.get("MooreMachine")
    
    if moore_fsm and moore_fsm["detected"]:
        print("✅ FSM Detected Successfully!")
        print(f"   Type: {moore_fsm['type']}")
        print(f"   State variables: {[v['name'] for v in moore_fsm.get('state_variables', [])]}")
        print(f"   States found: {len(moore_fsm.get('states', []))}")
        print(f"   Reset condition: {moore_fsm.get('reset_condition', 'unknown')}")
        print(f"   Clock signal: {moore_fsm.get('clock_signal', 'unknown')}")
        print(f"   Transitions found: {len(moore_fsm.get('transitions', []))}")
        
        # Проверяем состояния
        states = moore_fsm.get('states', [])
        if states:
            print("\n📊 States Analysis:")
            for state in states:
                print(f"   - {state['name']} ({state['type']}) from {state.get('source', 'unknown')}")
        
        # Проверяем переходы
        transitions = moore_fsm.get('transitions', [])
        if transitions:
            print("\n🔄 Transitions Analysis:")
            for i, trans in enumerate(transitions):
                print(f"   {i+1}. {trans.get('from_state', '?')} → {trans.get('to_state', '?')} [{trans.get('condition', '?')}]")
        
        # Проверяем ожидаемые значения
        expected_states = ['S0', 'S1', 'S2']
        actual_states = [s['name'] for s in states]
        
        print(f"\n✅ Expected states: {expected_states}")
        print(f"✅ Actual states: {actual_states}")
        print(f"✅ States match: {set(expected_states) == set(actual_states)}")
        print(f"✅ Reset detected: {moore_fsm.get('reset_condition') == 'rstN'}")
        print(f"✅ Clock detected: {moore_fsm.get('clock_signal') == 'clk'}")
        print(f"✅ Type correct: {moore_fsm.get('type') == 'moore'}")
        
    else:
        print("❌ FSM NOT Detected!")
    
    return ast

def main():
    """Основная функция тестирования"""
    print("Testing Improved FSM Detection")
    print("=" * 60)
    
    try:
        ast = test_moore_machine()
        print("\n🎉 TEST COMPLETED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"\n💥 ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()