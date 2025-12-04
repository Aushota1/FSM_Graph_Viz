import React, { useState } from 'react'
import './CodeEditor.css'

const EXAMPLE_CODE = `// Пример SystemVerilog кода с FSM
package defs;
  typedef enum logic [2:0] {IDLE, REQ, WAIT, GNT} state_t;
endpackage

module fsm_example(input  logic clk,
                   input  logic rst,
                   input  logic req,
                   input  logic gnt,
                   output logic gr);
  import defs::*;

  state_t state, next_state;

  always_ff @(posedge clk or posedge rst) begin
    if (rst)
      state <= IDLE;
    else
      state <= next_state;
  end

  always_comb begin
    next_state = state;
    unique case (state)
      IDLE: if (req)       next_state = REQ;
      REQ:                 next_state = WAIT;
      WAIT: if (gnt)       next_state = GNT;
      GNT:                 next_state = IDLE;
    endcase
  end

endmodule`

function CodeEditor({ code, onCodeChange, onParse, loading }) {
  const [localCode, setLocalCode] = useState(code || EXAMPLE_CODE)

  const handleCodeChange = (e) => {
    const newCode = e.target.value
    setLocalCode(newCode)
    onCodeChange(newCode)
  }

  const handleParse = () => {
    onParse(localCode)
  }

  const handleLoadExample = () => {
    setLocalCode(EXAMPLE_CODE)
    onCodeChange(EXAMPLE_CODE)
  }

  return (
    <div className="code-editor">
      <div className="code-editor-header">
        <h3>Редактор кода</h3>
        <div className="code-editor-actions">
          <button onClick={handleLoadExample} className="btn-secondary">
            Пример
          </button>
          <button 
            onClick={handleParse} 
            disabled={loading}
            className="btn-primary"
          >
            {loading ? 'Парсинг...' : 'Парсить'}
          </button>
        </div>
      </div>
      <textarea
        className="code-textarea"
        value={localCode}
        onChange={handleCodeChange}
        placeholder="Вставьте SystemVerilog код здесь..."
        spellCheck={false}
      />
    </div>
  )
}

export default CodeEditor

