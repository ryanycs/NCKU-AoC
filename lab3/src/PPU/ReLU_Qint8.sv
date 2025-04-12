module ReLU_Qint8(
    input [7:0] data_post_quant,
    input [7:0] data_maxpool,
    input relu_sel,
    input relu_en,
    output logic [7:0] data_out
);

localparam ZERO_POINT = 8'd128;

always_comb begin
    if (relu_en) begin
        case (relu_sel)
            1'b0: data_out = data_post_quant[7] ? data_post_quant : ZERO_POINT;
            1'b1: data_out = data_maxpool[7] ? data_maxpool : ZERO_POINT;
        endcase
    end else begin
        data_out = relu_sel ? data_post_quant : data_maxpool;
    end
end

endmodule
