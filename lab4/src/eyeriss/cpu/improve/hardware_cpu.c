#include "hardware_cpu.h"

#include <stdio.h>
#include <immintrin.h>

void conv_maxpooling(uint32_t input_C, uint32_t input_H, uint32_t input_W,
                     uint8_t* activation, uint32_t filter_N, uint32_t filter_C,
                     uint32_t filter_H, uint32_t filter_W, int8_t* filter,
                     int32_t* bias, uint32_t padding, uint8_t* output,
                     uint32_t scale) {
    /*! <<<========= Implement here =========>>>*/
    uint8_t *activation_padding;
    int8_t *filter_cache;
    uint32_t input_size = input_H * input_W;
    uint32_t filter_size = filter_H * filter_W;
    uint32_t output_H = (input_H - filter_H + (padding << 1)) + 1;
    uint32_t output_W = (input_W - filter_W + (padding << 1)) + 1;
    uint32_t padding_H = input_H + (padding << 1);
    uint32_t padding_W = input_W + (padding << 1);
    uint32_t padding_size = padding_H * padding_W;
    uint32_t maxpool_H = output_H >> 1;
    uint32_t maxpool_W = output_W >> 1;

    // Allocate memory and align it to 64 bytes
    posix_memalign(
        (void**)&activation_padding,
        64,
        input_C * padding_H * padding_W * sizeof(uint8_t)
    );
    posix_memalign(
        (void**)&filter_cache,
        64,
        filter_C * filter_H * filter_W * sizeof(int8_t)
    );

    // Initialize padding with 128 (zero point)
    memset(activation_padding, 128, input_C * padding_H * padding_W * sizeof(uint8_t));

    // Copy activation to padding
    for (int c = 0; c < input_C; c++) {
        int c_offset = c * padding_size;
        int c_offset_input = c * input_size;
        for (int y = 1; y <= input_H; y++) {
            memcpy(
                activation_padding +
                (c_offset + y * padding_W + padding),
                activation + (c_offset_input + (y - 1) * input_W),
                input_W * sizeof(uint8_t)
            );
        }
    }

    for (int m = 0; m < filter_N; m++) { // M
        int m_offset = m * filter_C * filter_size;

        // Copy filter to cache
        memcpy(
            filter_cache,
            filter + m_offset,
            filter_C * filter_size * sizeof(int8_t)
        );

        for (int y = 0; y < output_H; y++) { // E
            for (int x = 0; x < output_W; x++) { // F
                int output_index = m * maxpool_H * maxpool_W + (y >> 1) * maxpool_W + (x >> 1);
                int32_t sum = bias[m];

                for (int i = 0; i < filter_H; i++) { // R
                    for (int j = 0; j < filter_W; j++) { // S
                        for (int k = 0; k < filter_C; k++) { // C
                            int input_index = (
                                k * padding_size +
                                (y + i) * padding_W +
                                (x + j)
                            );

                            int filter_index = (
                                k * filter_size +
                                i * filter_W +
                                j
                            );

                            sum += (activation_padding[input_index] - 128) *
                                   filter_cache[filter_index];
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

    free(activation_padding);
    free(filter_cache);
};

void conv(uint32_t input_C, uint32_t input_H, uint32_t input_W,
          uint8_t* activation, uint32_t filter_N, uint32_t filter_C,
          uint32_t filter_H, uint32_t filter_W, int8_t* filter, int32_t* bias,
          uint32_t padding, uint8_t* output, uint32_t scale) {
    /*! <<<========= Implement here =========>>>*/
    uint8_t *activation_padding;
    int8_t *filter_cache;
    uint32_t input_size = input_H * input_W;
    uint32_t filter_size = filter_H * filter_W;
    uint32_t output_H = (input_H - filter_H + (padding << 1)) + 1;
    uint32_t output_W = (input_W - filter_W + (padding << 1)) + 1;
    uint32_t padding_H = input_H + (padding << 1);
    uint32_t padding_W = input_W + (padding << 1);
    uint32_t padding_size = padding_H * padding_W;

    // Allocate memory and align it to 64 bytes
    posix_memalign(
        (void**)&activation_padding,
        64,
        input_C * padding_H * padding_W * sizeof(uint8_t)
    );
    posix_memalign(
        (void**)&filter_cache,
        64,
        filter_C * filter_H * filter_W * sizeof(int8_t)
    );

    // Initialize padding with 128 (zero point)
    memset(activation_padding, 128, input_C * padding_H * padding_W * sizeof(uint8_t));

    // Copy activation to padding
    for (int c = 0; c < input_C; c++) {
        int c_offset = c * padding_size;
        int c_offset_input = c * input_size;
        for (int y = 1; y <= input_H; y++) {
            memcpy(
                activation_padding +
                (c_offset + y * padding_W + padding),
                activation + (c_offset_input + (y - 1) * input_W),
                input_W * sizeof(uint8_t)
            );
        }
    }

    for (int m = 0; m < filter_N; m++) { // M
        int m_offset = m * filter_C * filter_size;

        // Copy filter to cache
        memcpy(
            filter_cache,
            filter + m_offset,
            filter_C * filter_size * sizeof(int8_t)
        );

        for (int y = 0; y < output_H; y++) { // E
            for (int x = 0; x < output_W; x++) { // F
                int output_index = m * output_H * output_W + y * output_W + x;
                int32_t sum = bias[m];

                for (int i = 0; i < filter_H; i++) { // R
                    for (int j = 0; j < filter_W; j++) { // S
                        for (int k = 0; k < filter_C; k++) { // C
                            int input_index = (
                                k * padding_size +
                                (y + i) * padding_W +
                                (x + j)
                            );

                            int filter_index = (
                                k * filter_size +
                                i * filter_W +
                                j
                            );

                            sum += (activation_padding[input_index] - 128) *
                                   filter_cache[filter_index];
                        }
                    }
                }
                output[output_index] = requant(relu(sum), scale);
            }
        }
    }

    free(activation_padding);
    free(filter_cache);
};

void linear_relu(uint32_t input_size, uint32_t output_size, uint8_t* activation,
                 uint8_t* output, int8_t* filter, int32_t* bias,
                 uint32_t scale) {
    /*! <<<========= Implement here =========>>>*/
    for (int m = 0; m < output_size; m++) {
        int32_t sum = bias[m];

#ifdef __AVX2__
        int i = 0;
        // Calculate 16 elements at a time
        for (; i + 16 < input_size; i += 16) {
            int filter_index = m * input_size + i;
            __m128i a = _mm_loadu_si128((__m128i*)&activation[i]);
            __m128i b = _mm_loadu_si128((__m128i*)&filter[filter_index]);
            a = _mm_sub_epi8(a, _mm_set1_epi8(128)); // subtract zero point
            __m128i c = _mm_maddubs_epi16(a, b);

            c = _mm_hadd_epi16(c, c); // 8 -> 4
            c = _mm_cvtepi16_epi32(c); // convert to 32-bit integers
            c = _mm_hadd_epi32(c, c); // 4 -> 2
            c = _mm_hadd_epi32(c, c); // 2 -> 1
            sum += _mm_extract_epi32(c, 0); // extract the sum
        }
        for (; i < input_size; i++) {
            int filter_index = m * input_size + i;
            sum += (activation[i] - 128) * filter[filter_index];
        }
#else
        for (int i = 0; i < input_size; i++) {
            int filter_index = m * input_size + i;
            sum += (activation[i] - 128) * filter[filter_index];
        }
#endif

        output[m] = requant(relu(sum), scale);
    }
};

void linear(uint32_t input_size, uint32_t output_size, uint8_t* activation,
            uint8_t* output, int8_t* filter, int32_t* bias, uint32_t scale) {
    /*! <<<========= Implement here =========>>>*/
    for (int m = 0; m < output_size; m++) {
        int32_t sum = bias[m];

#ifdef __AVX2__
        int i = 0;
        // Calculate 16 elements at a time
        for (; i + 16 < input_size; i += 16) {
            int filter_index = m * input_size + i;
            __m128i a = _mm_loadu_si128((__m128i*)&activation[i]);
            __m128i b = _mm_loadu_si128((__m128i*)&filter[filter_index]);
            a = _mm_sub_epi8(a, _mm_set1_epi8(128)); // subtract zero point
            __m128i c = _mm_maddubs_epi16(a, b);

            c = _mm_hadd_epi16(c, c); // 8 -> 4
            c = _mm_cvtepi16_epi32(c); // convert to 32-bit integers
            c = _mm_hadd_epi32(c, c); // 4 -> 2
            c = _mm_hadd_epi32(c, c); // 2 -> 1
            sum += _mm_extract_epi32(c, 0); // extract the sum
        }
        for (; i < input_size; i++) {
            int filter_index = m * input_size + i;
            sum += (activation[i] - 128) * filter[filter_index];
        }
#else
        for (int i = 0; i < input_size; i++) {
            int filter_index = m * input_size + i;
            sum += (activation[i] - 128) * filter[filter_index];
        }
#endif

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