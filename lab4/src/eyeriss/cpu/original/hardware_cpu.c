#include "hardware_cpu.h"

void conv_maxpooling(uint32_t input_C, uint32_t input_H, uint32_t input_W,
                     uint8_t* activation, uint32_t filter_N, uint32_t filter_C,
                     uint32_t filter_H, uint32_t filter_W, int8_t* filter,
                     int32_t* bias, uint32_t padding, uint8_t* output,
                     uint32_t scale) {

    /*! <<<========= Implement here =========>>>*/
    uint32_t output_H = (input_H - filter_H + 2 * padding) + 1;
    uint32_t output_W = (input_W - filter_W + 2 * padding) + 1;
    uint32_t maxpool_H = output_H / 2;
    uint32_t maxpool_W = output_W / 2;

    for (int m = 0; m < filter_N; m++) { // M
        for (int y = 0; y < output_H; y++) { // E
            for (int x = 0; x < output_W; x++) { // F
                int output_index = m * maxpool_H * maxpool_W + (y / 2) * maxpool_W + (x / 2);
                int32_t sum = bias[m];

                for (int i = 0; i < filter_H; i++) { // R
                    for (int j = 0; j < filter_W; j++) { // S
                        for (int k = 0; k < filter_C; k++) { // C
                            int y_p = y + i - padding;
                            int x_p = x + j - padding;

                            // 0 padding
                            if (y_p < 0 || y_p >= input_H || x_p < 0 || x_p >= input_W)
                                continue;

                            int input_index = (
                                k * input_H * input_W +
                                y_p * input_W +
                                x_p
                            );

                            int filter_index = (
                                m * filter_C * filter_H * filter_W +
                                k * filter_H * filter_W +
                                i * filter_W +
                                j
                            );

                            sum += (activation[input_index] - 128) *
                                   filter[filter_index];
                        }
                    }
                }

                output[output_index] = max(
                    output[output_index],
                    requant(relu(sum), scale)
                );
            }
        }
    }
};

void conv(uint32_t input_C, uint32_t input_H, uint32_t input_W,
          uint8_t* activation, uint32_t filter_N, uint32_t filter_C,
          uint32_t filter_H, uint32_t filter_W, int8_t* filter, int32_t* bias,
          uint32_t padding, uint8_t* output, uint32_t scale) {

    /*! <<<========= Implement here =========>>>*/
    uint32_t output_H = (input_H - filter_H + 2 * padding) + 1;
    uint32_t output_W = (input_W - filter_W + 2 * padding) + 1;

    for (int m = 0; m < filter_N; m++) { // M
        for (int y = 0; y < output_H; y++) { // E
            for (int x = 0; x < output_W; x++) { // F
                int output_index = m * output_H * output_W + y * output_W + x;
                int32_t sum = bias[m];

                for (int i = 0; i < filter_H; i++) { // R
                    for (int j = 0; j < filter_W; j++) { // S
                        for (int k = 0; k < filter_C; k++) { // C
                            int y_p = y + i - padding;
                            int x_p = x + j - padding;

                            // 0 padding
                            if (y_p < 0 || y_p >= input_H || x_p < 0 || x_p >= input_W)
                                continue;

                            int input_index = (
                                k * input_H * input_W +
                                y_p * input_W +
                                x_p
                            );

                            int filter_index = (
                                m * filter_C * filter_H * filter_W +
                                k * filter_H * filter_W +
                                i * filter_W +
                                j
                            );

                            sum += (activation[input_index] - 128) *
                                   filter[filter_index];
                        }
                    }
                }

                output[output_index] = requant(relu(sum), scale);
            }
        }
    }
};

void linear_relu(uint32_t input_size, uint32_t output_size, uint8_t* activation,
                 uint8_t* output, int8_t* filter, int32_t* bias,
                 uint32_t scale) {
    /*! <<<========= Implement here =========>>>*/
    for (int m = 0; m < output_size; m++) {
        int32_t sum = bias[m];

        for (int i = 0; i < input_size; i++) {
            int filter_index = m * input_size + i;
            sum += ((int32_t)activation[i] - 128) * (int32_t)filter[filter_index];
        }

        output[m] = requant(relu(sum), scale);
    }
};

void linear(uint32_t input_size, uint32_t output_size, uint8_t* activation,
            uint8_t* output, int8_t* filter, int32_t* bias, uint32_t scale) {
    /*! <<<========= Implement here =========>>>*/
    for (int m = 0; m < output_size; m++) {
        int32_t sum = bias[m];

        for (int i = 0; i < input_size; i++) {
            int filter_index = m * input_size + i;
            sum += ((int32_t)activation[i] - 128) * (int32_t)filter[filter_index];
        }

        output[m] = requant(sum, scale);
    }
};

void quantize(float* input_in_DRAM, uint8_t* output_in_DRAM, uint32_t size,
              uint32_t scale) {
    float fp_scale = 1;
    for (uint32_t i = 0; i < scale; i++) {
        fp_scale *= 2;
    }
    for (uint32_t i = 0; i < size; i++) {
        float t = input_in_DRAM[i] * fp_scale;
        int32_t temp = (int32_t)t + 128;
        // clamp to 0 ~ 255
        if (temp < 0) {
            output_in_DRAM[i] = 0;
        } else if (temp > 255)
            output_in_DRAM[i] = 255;
        else
            output_in_DRAM[i] = (uint8_t)temp;
    }
};

void dequantize(uint8_t* input_in_DRAM, float* output_in_DRAM, uint32_t size,
                uint32_t scale) {
    float fp_scale = 1;
    for (uint32_t i = 0; i < scale; i++) {
        fp_scale *= 2;
    }
    for (uint32_t i = 0; i < size; i++) {
        float temp = *(input_in_DRAM + i) - 128;
        *(output_in_DRAM + i) = temp / fp_scale;
    }
};
