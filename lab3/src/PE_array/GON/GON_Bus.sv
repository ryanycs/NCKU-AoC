module GON_Bus #(
    parameter NUMS_MASTER = `NUMS_PE_COL,
    parameter ID_SIZE = `XID_BITS
)(
    input clk,
    input rst,

    // Master I/O
    input [ID_SIZE - 1:0] tag,
    input [NUMS_MASTER - 1:0] master_valid, // opsum_valid of each PE
    input [NUMS_MASTER * `DATA_BITS - 1:0] master_data, // opsum_data of each PE
    output logic [NUMS_MASTER - 1:0] master_ready,

    // Slave I/O
    output logic slave_valid,
    input slave_ready,
    output logic [`DATA_BITS - 1:0] slave_data, // PE data

    // Config
    input set_id,
    input [ID_SIZE - 1:0] ID_scan_in,
    output logic [ID_SIZE - 1 :0] ID_scan_out
);

logic [ID_SIZE-1:0] id_in [NUMS_MASTER-1:0];
logic [ID_SIZE-1:0] id [NUMS_MASTER-1:0];

logic [NUMS_MASTER-1:0] valid_out;

/*
                   MC              MC              MC
             ┌────────────┐  ┌────────────┐  ┌────────────┐
ID_scan_out◄─│ id   id_in │◄─│ id   id_in │◄─│ id   id_in │◄─ID_scan_in
             └────────────┘  └────────────┘  └────────────┘
 */
always_comb begin
    id_in[0] = ID_scan_in;
    for (int i = 1; i < NUMS_MASTER; i++) begin
        id_in[i] = id[i-1];
    end
    ID_scan_out = id[NUMS_MASTER-1];
end

generate
    for (genvar i = 0; i < NUMS_MASTER; i = i + 1) begin : MC_gen
        GON_MulticastController #(
            .ID_SIZE(ID_SIZE)
        ) MC (
            .clk      (clk),
            .rst      (rst),
            .set_id   (set_id),
            .id_in    (id_in[i]),
            .id       (id[i]),
            .tag      (tag),
            .valid_in (master_valid[i]), // opsum_valid of each PE
            .valid_out(valid_out[i]),
            .ready_in (slave_ready), // from GLB
            .ready_out(master_ready[i])
        );
    end
endgenerate

always_comb begin
    slave_valid = |valid_out; // if any PE is valid, then slave is valid
end

endmodule
