module GON_MulticastController #(
    parameter ID_SIZE = `XID_BITS
)(
    input clk,
    input rst,

    // config id
    input set_id,
    input [ID_SIZE - 1:0] id_in,
    output logic [ID_SIZE - 1:0] id,

    // tag
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
    ready_out = ready_in && (tag == id);
    valid_out = valid_in && (tag == id);
end

endmodule
