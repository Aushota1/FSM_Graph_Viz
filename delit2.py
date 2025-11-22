# -*- coding: utf-8 -*-
# run_complete_analysis.py
"""
ЗАПУСК ПОЛНОГО АНАЛИЗА ДЛЯ ВАШЕГО SYSTEMVERILOG КОДА
"""

import sys
from pathlib import Path

# Добавляем путь к вашим сервисам
sys.path.append('.')

from test_free import CompleteASTService, print_complete_ast
from delit1 import generate_complete_analysis_report, save_ast_json

def analyze_your_code():
    """Проанализировать ваш SystemVerilog код"""
    
    # Ваш код из вопроса
    your_code = """
//----------------------------------------------------------------------------
// Example
//----------------------------------------------------------------------------

module detect_4_bit_sequence_using_fsm
(
  input  clk,
  input  rst,
  input  a,
  output detected
);

  // Detection of the "1010" sequence

  // States (F — First, S — Second)
  enum logic[2:0]
  {
     IDLE   = 3'b001,
     F1 = 3'b000,
     F0   = 3'b010,
     S1   = 3'b011,
     S0   = 3'b100
  }
  fsm_state;

  fsm_state next_state;
  fsm_state state;

  // State transition logic
  always_comb
  begin
    next_state = state;

    // This lint warning is bogus because we assign the default value above
    // verilator lint_off CASEINCOMPLETE

    case (state)
      IDLE: if (  a) next_state = F1;
      F1:   if (~ a) next_state = F0;
      F0:   if (  a) next_state = S1;
            else     next_state = IDLE;
      S1:   if (~ a) next_state = S0;
            else     next_state = F1;
      S0:   if (  a) next_state = S1;
            else     next_state = IDLE;
    endcase

    // verilator lint_on CASEINCOMPLETE

  end

  // Output logic (depends only on the current state)
  assign detected = (state == S0);

  // State update
  always_ff @ (posedge clk)
    if (rst)
      state <= IDLE;
    else
      state <= next_state;

endmodule

//----------------------------------------------------------------------------
// Task
//----------------------------------------------------------------------------

module detect_6_bit_sequence_using_fsm
(
  input  clk,
  input  rst,
  input  a,
  output detected
);

  // Task:
  // Implement a module that detects the "110011" input sequence
  //
  // Hint: See Lecture 3 for details


endmodule


    """
    
    try:
        # Импортируем CST сервис
        from cst_service import CSTService
        
        print("🔍 ЗАПУСК ПОЛНОГО АНАЛИЗА SYSTEMVERILOG КОДА...")
        print("=" * 60)
        
        # Строим CST
        cst_service = CSTService()
        tree = cst_service.build_cst_from_text(your_code, "your_code.sv")
        
        # Строим ПОЛНЫЙ AST
        ast_service = CompleteASTService()
        ast_service.debug = True  # Включаем отладку для подробного вывода
        
        complete_ast = ast_service.build_complete_ast_from_cst(tree)
        
        print("✅ AST УСПЕШНО ПОСТРОЕН!")
        print("")
        
        # 1. Печать базового AST
        print("📊 БАЗОВЫЙ AST:")
        print_complete_ast(complete_ast)
        
        print("\n" + "=" * 80)
        print("📈 ПОЛНЫЙ АНАЛИТИЧЕСКИЙ ОТЧЕТ:")
        print("=" * 80)
        
        # 2. Генерация полного аналитического отчета
        generate_complete_analysis_report(
            complete_ast,
            output_file="complete_analysis_report.txt",
            console_output=True
        )
        
        # 3. Сохранение полных данных AST в JSON
        save_ast_json(complete_ast, "complete_ast_data.json")
        
        print("")
        print("✅ АНАЛИЗ ЗАВЕРШЕН!")
        print("📁 Отчет сохранен в: complete_analysis_report.txt")
        print("📁 Данные AST сохранены в: complete_ast_data.json")
        
        return complete_ast
        
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    analyze_your_code()