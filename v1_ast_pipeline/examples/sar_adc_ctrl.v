// 4-bit Successive Approximation Register (SAR) ADC Digital Controller
// Typical mixed-signal block controlling capacitive DAC switches during conversion.

module sar_adc_ctrl (
    input clk,
    input rst_n,
    input start,
    input comp_out,
    output [3:0] dac_code,
    output eoc,
    output valid
);

    reg [3:0] dac_reg;
    reg [2:0] state;
    reg eoc_reg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= 3'b000;
            dac_reg <= 4'b0000;
            eoc_reg <= 1'b0;
        end else begin
            case (state)
                3'b000: begin
                    eoc_reg <= 1'b0;
                    if (start) begin
                        state <= 3'b001;
                        dac_reg <= 4'b1000;
                    end
                end
                3'b001: begin
                    dac_reg[3] <= comp_out;
                    dac_reg[2] <= 1'b1;
                    state <= 3'b010;
                end
                3'b010: begin
                    dac_reg[2] <= comp_out;
                    dac_reg[1] <= 1'b1;
                    state <= 3'b011;
                end
                3'b011: begin
                    dac_reg[1] <= comp_out;
                    dac_reg[0] <= 1'b1;
                    state <= 3'b100;
                end
                3'b100: begin
                    dac_reg[0] <= comp_out;
                    state <= 3'b000;
                    eoc_reg <= 1'b1;
                end
                default: state <= 3'b000;
            endcase
        end
    end

    assign dac_code = dac_reg;
    assign eoc = eoc_reg;
    assign valid = eoc_reg;

endmodule
