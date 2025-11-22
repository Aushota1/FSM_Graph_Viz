module fsm_example8_fake_state
(
  input  logic clk,
  input  logic rst,
  input  logic [7:0] data,
  output logic [7:0] state_out
);

  logic [7:0] state_counter;

  always_ff @(posedge clk or posedge rst) begin
    if (rst)
      state_counter <= 8'd0;
    else
      state_counter <= state_counter + 1'b1;
  end

  assign state_out = state_counter;

endmodule
