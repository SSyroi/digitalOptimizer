// Configurable 4-bit Clock Divider with Synchronous Load and Clear

module clock_divider_rst (
    input clk,
    input rst_n,
    input load,
    input [3:0] div_ratio,
    output reg clk_out,
    output [3:0] count
);

    reg [3:0] cnt_reg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cnt_reg <= 4'b0000;
            clk_out <= 1'b0;
        end else if (load) begin
            cnt_reg <= div_ratio;
            clk_out <= 1'b0;
        end else if (cnt_reg == 4'b0000) begin
            cnt_reg <= div_ratio;
            clk_out <= ~clk_out;
        end else begin
            cnt_reg <= cnt_reg + 4'd1;
        end
    end

    assign count = cnt_reg;

endmodule
