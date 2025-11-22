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
