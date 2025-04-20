module GIN_MulticastController #(
    parameter ID_SIZE = `XID_BITS
    )(
    input clk,
    input rst,

    input set_id,
    input [ID_SIZE - 1:0] id_in,
    output logic [ID_SIZE - 1:0] id,

    input [ID_SIZE - 1:0] tag,

    input valid_in,
    output logic valid_out,
    input ready_in,
    output logic ready_out
);

// id
always_ff @(posedge clk or posedge rst) begin
    if (rst) id <= 0;
    else id <= set_id ? id_in : id;
end

always_comb begin
    valid_out = ready_in && valid_in && (tag == id);
    ready_out = ready_in;
end

endmodule
