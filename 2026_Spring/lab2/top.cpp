#include "dcl.h"

// 9-point weighted stencil (constant weights):
// nxt[i][j] = wc * cur[i][j]
//           + wa * (cur[i-1][j] + cur[i+1][j] + cur[i][j-1] + cur[i][j+1])
//           + wd * (cur[i-1][j-1] + cur[i-1][j+1] + cur[i+1][j-1] + cur[i+1][j+1])
//
// Boundary handling: boundaries are copied unchanged each timestep.

void top_kernel(const data_t A_in[NX][NY],
                data_t A_out[NX][NY]) {
    #pragma HLS interface m_axi port=A_in offset=slave bundle=gmem
    #pragma HLS interface m_axi port=A_out offset=slave bundle=gmem
    #pragma HLS interface s_axilite port=return

    // Ping-pong buffers
    static data_t buf0[NX][NY];
    static data_t buf1[NX][NY];
    
    // Partition along columns (dim=2) to allow parallel access for 9-point stencil
    #pragma HLS ARRAY_PARTITION variable=buf0 dim=2 type=cyclic factor=8
    #pragma HLS ARRAY_PARTITION variable=buf1 dim=2 type=cyclic factor=8

    // Constant weights
    const data_t wc = (data_t)0.50;
    const data_t wa = (data_t)0.10;
    const data_t wd = (data_t)0.025;

    // Load input
    Loop_Read: for (int i = 0; i < NX; i++) {
        for (int j = 0; j < NY; j++) {
            #pragma HLS PIPELINE II=1
            buf0[i][j] = A_in[i][j];
        }
    }

    // Time stepping with Ping-Pong
    Loop_Time: for (int t = 0; t < TSTEPS; t++) {
        
        // Pointers/Refs to current and next buffers
        // We can't use real pointers easily in HLS for arrays this way without care,
        // so we use a flag to select logic. HLS handles "if" inside loops well if expected.
        bool use_buf0_as_cur = (t % 2 == 0);

        // Compute Boundary
        // (Optimized: we could skip this if we handled borders differently, 
        // but for now, just copy from cur -> nxt like baseline)
        Loop_Boundary_Row: for (int j = 0; j < NY; j++) {
            #pragma HLS PIPELINE II=1
            if (use_buf0_as_cur) {
                buf1[0][j]      = buf0[0][j];
                buf1[NX - 1][j] = buf0[NX - 1][j];
            } else {
                buf0[0][j]      = buf1[0][j];
                buf0[NX - 1][j] = buf1[NX - 1][j];
            }
        }
        Loop_Boundary_Col: for (int i = 0; i < NX; i++) {
            #pragma HLS PIPELINE II=1
             if (use_buf0_as_cur) {
                buf1[i][0]      = buf0[i][0];
                buf1[i][NY - 1] = buf0[i][NY - 1];
            } else {
                buf0[i][0]      = buf1[i][0];
                buf0[i][NY - 1] = buf1[i][NY - 1];
            }
        }

        // Update Interior
        Loop_Internal_Rows: for (int i = 1; i < NX - 1; i++) {
            Loop_Internal_Cols: for (int j = 1; j < NY - 1; j++) {
                #pragma HLS PIPELINE II=1

                data_t v_n, v_s, v_w, v_e;
                data_t v_nw, v_ne, v_sw, v_se;
                data_t v_c;

                // Select Source Data
                if (use_buf0_as_cur) {
                    v_n  = buf0[i - 1][j];
                    v_s  = buf0[i + 1][j];
                    v_w  = buf0[i][j - 1];
                    v_e  = buf0[i][j + 1];
                    
                    v_nw = buf0[i - 1][j - 1];
                    v_ne = buf0[i - 1][j + 1];
                    v_sw = buf0[i + 1][j - 1];
                    v_se = buf0[i + 1][j + 1];
                    
                    v_c  = buf0[i][j];
                } else {
                    v_n  = buf1[i - 1][j];
                    v_s  = buf1[i + 1][j];
                    v_w  = buf1[i][j - 1];
                    v_e  = buf1[i][j + 1];
                    
                    v_nw = buf1[i - 1][j - 1];
                    v_ne = buf1[i - 1][j + 1];
                    v_sw = buf1[i + 1][j - 1];
                    v_se = buf1[i + 1][j + 1];
                    
                    v_c  = buf1[i][j];
                }

                // Math (Identical to baseline)
                acc_t sum_axis = (acc_t)v_n + (acc_t)v_s + (acc_t)v_w + (acc_t)v_e;
                acc_t sum_diag = (acc_t)v_nw + (acc_t)v_ne + (acc_t)v_sw + (acc_t)v_se;
                acc_t center   = (acc_t)v_c;
                
                acc_t out = (acc_t)wc * center + (acc_t)wa * sum_axis + (acc_t)wd * sum_diag;
                
                // Write Destination
                if (use_buf0_as_cur) {
                    buf1[i][j] = (data_t)out;
                } else {
                    buf0[i][j] = (data_t)out;
                }
            }
        }
    }

    // Write Output
    // Final result is in buf0 if TSTEPS is even, buf1 if odd.
    // TSTEPS is 30 (even), so result is in buf0.
    // Wait, let's trace: t=0 (cur=buf0, nxt=buf1), t=1 (cur=buf1, nxt=buf0)...
    // t=29 (cur=buf1, nxt=buf0). 
    // Wait, TSTEPS=30 means t runs 0..29.
    // t=0: READ buf0, WRITE buf1
    // ...
    // t=29: READ buf1, WRITE buf0
    // So final result is in buf0.
    
    // However, to be generic (if TSTEPS changes), we check valid output buffer.
    bool final_result_in_buf0 = (TSTEPS % 2 == 0);

    Loop_Write: for (int i = 0; i < NX; i++) {
        for (int j = 0; j < NY; j++) {
            #pragma HLS PIPELINE II=1
            if (final_result_in_buf0)
                A_out[i][j] = buf0[i][j];
            else
                A_out[i][j] = buf1[i][j];
        }
    }
}
