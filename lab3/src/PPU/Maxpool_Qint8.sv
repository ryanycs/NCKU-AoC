module Maxpool_Qint8 (
    input clk,
    input rst,
    input [7:0] data_in,
    input maxpool_en,
    input maxpool_init,
    output logic [7:0] data_out
);

always_ff @(posedge clk or posedge rst) begin
    if (rst || maxpool_init)
        data_out <= data_in;
    else if (maxpool_en)
        data_out <= (data_in > data_out) ? data_in : data_out;
end

endmodule
