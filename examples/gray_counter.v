// 3-bit Synchronous Binary and Gray Code Counter for AMS Clock Generators

module gray_counter (
    input clk,
    input rst_n,
    input ena,
    output [2:0] count_bin,
    output [2:0] count_gray
);

    reg [2:0] q;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            q <= 3'b000;
        end else if (ena) begin
            q <= q + 3'd1;
        end
    end

    assign count_bin = q;
    // Glitch-free Gray code conversion: G[i] = B[i] ^ B[i+1]
    assign count_gray[2] = q[2];
    assign count_gray[1] = q[2] ^ q[1];
    assign count_gray[0] = q[1] ^ q[0];

endmodule
