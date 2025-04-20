module GIN_Bus #(
    parameter NUMS_SLAVE = `NUMS_PE_COL,
    parameter ID_SIZE = `XID_BITS
)(
    input clk,
    input rst,

    // Master I/O
    input [ID_SIZE-1:0] tag,
    input master_valid,
    input [`DATA_BITS-1:0] master_data,
    output logic master_ready,

    // Slave I/O
    input [NUMS_SLAVE-1:0] slave_ready,
    output logic [NUMS_SLAVE-1:0] slave_valid,
    output logic [`DATA_BITS-1:0] slave_data,

    // Config
    input set_id,
    input [ID_SIZE-1:0] ID_scan_in,
    output logic [ID_SIZE-1:0] ID_scan_out
);

logic [ID_SIZE-1:0] id_in [NUMS_SLAVE-1:0];
logic [ID_SIZE-1:0] id [NUMS_SLAVE-1:0];

/*
                   MC              MC              MC
             ┌────────────┐  ┌────────────┐  ┌────────────┐
ID_scan_out◄─│ id   id_in │◄─│ id   id_in │◄─│ id   id_in │◄─ID_scan_in
             └────────────┘  └────────────┘  └────────────┘
 */
always_comb begin
    id_in[0] = ID_scan_in;
    for (int i = 1; i < NUMS_SLAVE; i++) begin
        id_in[i] = id[i-1];
    end
    ID_scan_out = id[NUMS_SLAVE-1];
end

generate
    for (genvar i = 0; i < NUMS_SLAVE; i++) begin : MC_gen
        GIN_MulticastController #(
            .ID_SIZE(ID_SIZE)
        ) MC (
            .clk,
            .rst,
            .set_id   (set_id),
            .id_in    (id_in[i]),
            .id       (id[i]),
            .tag      (tag),
            .valid_in (master_valid),
            .valid_out(slave_valid[i]),
            .ready_in (slave_ready[i]),
            .ready_out()
        );
    end
endgenerate

always_comb begin
    master_ready = |slave_ready; // Valid if any slaves are ready
    slave_data = master_valid ? master_data : '0; // Pass data if valid
end

endmodule
