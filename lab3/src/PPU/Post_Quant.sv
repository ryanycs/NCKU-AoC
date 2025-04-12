module Post_Quant(
    input signed [`DATA_BITS-1:0] data_in,
    input [5:0] scaling_factor,
    output logic [7:0] data_out
);

logic signed [`DATA_BITS-1:0] tmp;
logic sign_bit = data_in[`DATA_BITS-1];

Comparator_Qint8 comparator (
    .data_in(tmp),
    .data_out(data_out)
);

always_comb begin
    tmp = (data_in >>> scaling_factor);

    if (!sign_bit && tmp[7])
        // Carry one bit if the number is in range [128, 255]
        tmp[8:7] = 2'b10;
    else
        tmp[7] = ~tmp[7];
end

endmodule
