#include "dcl.h"

void top_kernel(data_t A[N_ROWS][N_COLS],
                data_t C[N_ROWS][N_COLS]) {
    
    // REMOVED: Interface partitioning on A and C to fix Export Error.
    // This ensures standard RAM interfaces that Vivado can handle easily.

    // OPTIMIZATION: Partition internal buffers.
    // 'col_sums' is small, so we turn it into registers for fast random access.
    data_t col_sums[N_COLS];
    #pragma HLS ARRAY_PARTITION variable=col_sums type=complete

    // We keep 'tmp' unpartitioned to save BRAM, as our speed is limited
    // by the single port of A and C anyway.
    static data_t tmp[N_ROWS][N_COLS];

    // --- PHASE 1: Row Normalization ---
    Loop_Rows_Norm: for (int i = 0; i < N_ROWS; i++) {
        data_t row_sum = 0.0;

        // Sum Loop: Pipelined to process one element per clock cycle (II=1)
        Loop_Sum_Rows: for (int j = 0; j < N_COLS; j++) {
            #pragma HLS PIPELINE II=1
            row_sum += A[i][j];
        }

        data_t denom = row_sum + (data_t)1.0;

        // Normalize Loop
        Loop_Div_Rows: for (int j = 0; j < N_COLS; j++) {
            #pragma HLS PIPELINE II=1
            tmp[i][j] = A[i][j] / denom;
        }
    }

    // --- PHASE 2: Column-wise Scaling (OPTIMIZED) ---
    
    // Step 2a: Initialize Column Sums
    Loop_Init_Col_Sums: for (int j = 0; j < N_COLS; j++) {
        #pragma HLS PIPELINE II=1
        col_sums[j] = 0;
    }

    // Step 2b: Compute Column Sums (Row-Major Scan)
    // CRITICAL FIX: We iterate Row->Col to ensure sequential memory access.
    Loop_Calc_Col_Sums_Outer: for (int i = 0; i < N_ROWS; i++) {
        Loop_Calc_Col_Sums_Inner: for (int j = 0; j < N_COLS; j++) {
            #pragma HLS PIPELINE II=1
            // We can update col_sums[j] instantly because it is partitioned completely.
            col_sums[j] += tmp[i][j];
        }
    }

    // Step 2c: Apply Scale (Row-Major Scan)
    Loop_Apply_Scale_Outer: for (int i = 0; i < N_ROWS; i++) {
        Loop_Apply_Scale_Inner: for (int j = 0; j < N_COLS; j++) {
            #pragma HLS PIPELINE II=1
            
            data_t scale = col_sums[j] / (data_t)N_ROWS; 
            C[i][j] = tmp[i][j] * scale;
        }
    }
}