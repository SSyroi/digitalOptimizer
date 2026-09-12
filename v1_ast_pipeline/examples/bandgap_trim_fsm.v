// Bandgap Voltage Reference Digital Trimming FSM
// Searches for optimal 3-bit trim code based on analog comparator feedback.

module bandgap_trim_fsm (
    input clk,
    input rst_n,
    input start_trim,
    input comp_high,
    output [2:0] trim_code,
    output trim_done
);

    reg [2:0] trim_reg;
    reg done_reg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            trim_reg <= 3'b000;
            done_reg <= 1'b0;
        end else if (start_trim && !done_reg) begin
            if (comp_high) begin
                done_reg <= 1'b1;
            end else begin
                trim_reg <= trim_reg + 3'd1;
            end
        end
    end

    assign trim_code = trim_reg;
    assign trim_done = done_reg;

endmodule
