`include "src/PE_array/GON/GON_Bus.sv"
`include "src/PE_array/GON/GON_MulticastController.sv"

module GON (
    input clk,
    input rst,

    // Master GON <-> GLB
    output logic GON_valid,
    input GON_ready,
    output logic [`DATA_BITS-1:0] GON_data,

    // Controller <-> GON
    input [`XID_BITS-1:0] tag_X,
    input [`YID_BITS-1:0] tag_Y,

    // config
    input set_XID,
    input [`XID_BITS - 1:0] XID_scan_in,
    input set_YID,
    input [`YID_BITS - 1:0] YID_scan_in,

    // Master PE <-> GON
    input [`NUMS_PE_ROW * `NUMS_PE_COL - 1:0] PE_valid,
    output logic [`NUMS_PE_ROW * `NUMS_PE_COL - 1:0] PE_ready,
    input [`DATA_BITS * `NUMS_PE_ROW * `NUMS_PE_COL - 1:0] PE_data
);

logic [`NUMS_PE_ROW-1:0] X_bus_valid;
logic [`NUMS_PE_ROW-1:0] X_bus_ready;
logic [`XID_BITS-1:0] id_in [`NUMS_PE_ROW-1:0];
logic [`XID_BITS-1:0] id [`NUMS_PE_ROW-1:0];

// ===================================================================
//  Y bus
// ===================================================================

GON_Bus #(
    .NUMS_MASTER(`NUMS_PE_ROW),
    .ID_SIZE(`YID_BITS)
) Y_bus (
    .clk         (clk),
    .rst         (rst),
    .tag         (tag_Y),
    .master_valid(X_bus_valid), // input
    .master_data (),            // input, Y_bus don't need to pass data
    .master_ready(X_bus_ready), // output, decide which X_bus should send ready signal
    .slave_valid (GON_valid),   // output
    .slave_ready (GON_ready),   // input
    .slave_data  (),            // output
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
        GON_Bus X_bus (
            .clk         (clk),
            .rst         (rst),
            .tag         (tag_X),
            .master_valid(PE_valid[i * `NUMS_PE_COL +: `NUMS_PE_COL]), // input
            .master_data (PE_data[(i * `NUMS_PE_COL * `DATA_BITS) +: `NUMS_PE_COL * `DATA_BITS]),
            .master_ready(PE_ready[i * `NUMS_PE_COL +: `NUMS_PE_COL]), // output
            .slave_valid (X_bus_valid[i]), // output
            .slave_ready (X_bus_ready[i]), // input
            .slave_data  (),               // output
            .set_id      (set_XID),
            .ID_scan_in  (id_in[i]),
            .ID_scan_out (id[i])
        );
    end
endgenerate

// ===================================================================
//  Output
// ===================================================================

// GON_data
always_comb begin
    GON_data = '0;
    for (int i = 0; i < `NUMS_PE_ROW * `NUMS_PE_COL; i = i + 1) begin
        if (PE_ready[i] == 1'b1) begin
            GON_data = PE_data[(i * `DATA_BITS) +: `DATA_BITS];
        end
    end
end

endmodule
