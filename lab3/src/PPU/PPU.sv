`include "define.svh"
`include "src/PPU/Post_Quant.sv"
`include "src/PPU/Comparator_Qint8.sv"
`include "src/PPU/Maxpool_Qint8.sv"
`include "src/PPU/ReLU_Qint8.sv"

/*
                                                                           ┌────────────┐
                 ┌────────────┐  ┌──────────────────┐            relu_en ─►│            │
       data_in ─►│            │  │                  │           relu_sel ─►│            │
                 │ Post_Quant ├─►│ Comparator_Qint8 ├─┬───────────────────►│            │
scaling_factor ─►│            │  │                  │ │                    │            │
                 └────────────┘  └──────────────────┘ │                    │ ReLU_Qint8 ├─► data_out
                                                      │ ┌───────────────┐  │            │
                                                      └►│               │  │            │
                                           maxpool_en ─►│ Maxpool_Qint8 ├─►│            │
                                         maxpool_init ─►│               │  │            │
                                                        └───────────────┘  └────────────┘
 */
module PPU (
    input clk,
    input rst,
    input [`DATA_BITS-1:0] data_in,
    input [5:0] scaling_factor,
    input maxpool_en,
    input maxpool_init,
    input relu_sel,
    input relu_en,
    output logic[7:0] data_out
);

logic [7:0] data_post_quant;
logic [7:0] data_maxpool;

Post_Quant post_quant (
    .data_in(data_in),
    .scaling_factor(scaling_factor),
    .data_out(data_post_quant)
);

Maxpool_Qint8 maxpool (
    .clk(clk),
    .rst(rst),
    .data_in(data_post_quant),
    .maxpool_en(maxpool_en),
    .maxpool_init(maxpool_init),
    .data_out(data_maxpool)
);

ReLU_Qint8 relu (
    .data_post_quant(data_post_quant),
    .data_maxpool(data_maxpool),
    .relu_sel(relu_sel),
    .relu_en(relu_en),
    .data_out(data_out)
);

endmodule
