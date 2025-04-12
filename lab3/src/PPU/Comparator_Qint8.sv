module Comparator_Qint8(
    input [`DATA_BITS-1:0] data_in,
    output logic [7:0] data_out
);

logic [7:0] data_out_temp;
logic sign_bit = data_in[`DATA_BITS-1];

// clamp(data_in, 0, 255)
always_comb begin
    data_out_temp = data_in[7:0] & ~{8{sign_bit}}; // clamp to 0
    data_out = data_out_temp |
               {8{|data_in[`DATA_BITS-2:8] & ~sign_bit}}; // clamp to 255
end

endmodule
