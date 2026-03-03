#include "dcl.h"

void top_kernel(data_t A[N_ROWS][N_COLS],
                data_t C[N_ROWS][N_COLS]) {

    // ------------------------------------------------------------------------
    // INTERFACE CONFIGURATION
    // ------------------------------------------------------------------------
    // PER PROFESSOR'S INSTRUCTION:
    // We DO NOT partition A or C. This leaves them as standard DRAM interfaces.
    // We will handle the caching manually below for maximum speed.
    
    // ------------------------------------------------------------------------
    // INTERNAL MEMORY (BRAM/REGISTERS)
    // ------------------------------------------------------------------------
    
    // 'tmp' stores the normalized matrix.
    // Partitioning it allows us to read/write multiple elements if we unroll later,
    // though with II=1 and single-port DRAM, factor=2 or 4 is sufficient.
    static data_t tmp[N_ROWS][N_COLS];
    #pragma HLS ARRAY_PARTITION variable=tmp dim=2 type=cyclic factor=8

    // 'col_sums' is small (64 elements), so we explode it into registers.
    // This allows "Random Access" - we can update ANY column index instantly.
    data_t col_sums[N_COLS];
    #pragma HLS ARRAY_PARTITION variable=col_sums type=complete

    // ------------------------------------------------------------------------
    // INITIALIZATION
    // ------------------------------------------------------------------------
    Loop_Init_Sums: for (int j = 0; j < N_COLS; j++) {
        #pragma HLS PIPELINE II=1
        col_sums[j] = 0;
    }

    // ------------------------------------------------------------------------
    // PHASE 1 & 2 FUSED: Row Norm + Column Sum Accumulation
    // ------------------------------------------------------------------------
    // Strategy: Read from DRAM once per row. Compute Sum. 
    // Then Normalize and immediately add to Col Sums.
    
    Loop_Row_Processing: for (int i = 0; i < N_ROWS; i++) {
        
        // L1 CACHE: Local buffer for the current row.
        // This decouples us from the slow DRAM interface.
        data_t row_buf[N_COLS];
        data_t row_sum = 0.0;

        // Step 1: Read DRAM -> BRAM + Compute Row Sum (Fused)
        Loop_Read_Sum: for (int j = 0; j < N_COLS; j++) {
            #pragma HLS PIPELINE II=1
            data_t val = A[i][j]; // DRAM Burst Read
            row_buf[j] = val;     // Cache it
            row_sum += val;       // Compute
        }

        data_t denom = row_sum + (data_t)1.0;

        // Step 2: Normalize + Accumulate Column Sums (Fused)
        // We write to 'tmp' AND update 'col_sums' in the same pass.
        Loop_Norm_Accum: for (int j = 0; j < N_COLS; j++) {
            #pragma HLS PIPELINE II=1
            
            data_t val = row_buf[j] / denom;
            
            tmp[i][j] = val;      // Save normalized value
            col_sums[j] += val;   // Update column sum (Phase 2a)
        }
    }

    // ------------------------------------------------------------------------
    // PHASE 3: Final Scaling
    // ------------------------------------------------------------------------
    // Strategy: Loop Interchange (Row -> Col).
    // Accessing 'C' sequentially (C[0][0], C[0][1]...) enables DRAM Burst Writes.
    
    Loop_Scale_Rows: for (int i = 0; i < N_ROWS; i++) {
        Loop_Scale_Cols: for (int j = 0; j < N_COLS; j++) {
            #pragma HLS PIPELINE II=1
            
            // Note: N_ROWS is 256. Division by power-of-2 is a cheap bit-shift.
            data_t scale = col_sums[j] / (data_t)N_ROWS; 
            C[i][j] = tmp[i][j] * scale; // DRAM Burst Write
        }
    }
}