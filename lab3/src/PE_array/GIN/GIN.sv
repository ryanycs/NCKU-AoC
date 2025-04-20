`include "src/PE_array/GIN/GIN_Bus.sv"
`include "src/PE_array/GIN/GIN_MulticastController.sv"

module GIN (
    input clk,
    input rst,

    // Slave SRAM <-> GIN
    input GIN_valid,
    output logic GIN_ready,
    input [`DATA_BITS - 1:0] GIN_data,

    // Controller <-> GIN
    input [`XID_BITS - 1:0] tag_X,
    input [`YID_BITS - 1:0] tag_Y,

    // config
    input set_XID,
    input [`XID_BITS - 1:0] XID_scan_in,
    input set_YID,
    input [`YID_BITS - 1:0] YID_scan_in,

    // Master GIN <-> PE
    input [`NUMS_PE_ROW * `NUMS_PE_COL - 1:0] PE_ready,
    output logic [`NUMS_PE_ROW * `NUMS_PE_COL - 1:0] PE_valid,
    output logic [`DATA_BITS - 1:0] PE_data
);

logic [`NUMS_PE_ROW-1:0] X_bus_valid;
logic [`NUMS_PE_ROW-1:0] X_bus_ready;
logic [`XID_BITS-1:0] id_in [`NUMS_PE_ROW-1:0];
logic [`XID_BITS-1:0] id [`NUMS_PE_ROW-1:0];

// ===================================================================
//  Y bus
// ===================================================================

GIN_Bus #(
    .NUMS_SLAVE(`NUMS_PE_ROW),
    .ID_SIZE   (`YID_BITS)
) Y_bus (
    .clk         (clk),
    .rst         (rst),
    .tag         (tag_Y),
    .master_valid(GIN_valid),   // input
    .master_data (GIN_data),    // input
    .master_ready(GIN_ready),   // output
    .slave_ready (X_bus_ready), // input
    .slave_valid (X_bus_valid), // output
    .slave_data  (PE_data),     // output
    .set_id      (set_YID),
    .ID_scan_in  (YID_scan_in),
    .ID_scan_out () // Y_bus don't need to carry out
);

// ===================================================================
//  X bus
// ===================================================================

always_comb begin
    id_in[0] = XID_scan_in;
    for (int i = 1; i < `NUMS_PE_ROW; i = i + 1) begin
        id_in[i] = id[i-1];
    end
end

generate
    for (genvar i = 0; i < `NUMS_PE_ROW; i = i + 1) begin : X_bus_gen
        GIN_Bus X_bus (
            .clk         (clk),
            .rst         (rst),
            .tag         (tag_X),
            .master_valid(X_bus_valid[i]), // input
            .master_data (),               // input
            .master_ready(X_bus_ready[i]), // output
            .slave_ready (PE_ready[i * `NUMS_PE_COL +: `NUMS_PE_COL]), // input
            .slave_valid (PE_valid[i * `NUMS_PE_COL +: `NUMS_PE_COL]), // output
            .slave_data  (),                                           // output
            .set_id      (set_XID),
            .ID_scan_in  (id_in[i]), // from previous MC, or scan_in if is the first MC
            .ID_scan_out (id[i]) // to next MC
        );
    end
endgenerate

endmodule
