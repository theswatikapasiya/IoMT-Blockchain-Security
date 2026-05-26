"""
Layer 1 - Step 2: Data Cleaning and Preprocessing
Cleans, filters, smooths, synchronizes, and normalizes the acquired medical datasets.
"""

import os
import re
from typing import Dict, Any
import numpy as np
import pandas as pd

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")

# Column names for UCI Heart Disease
UCI_COLUMNS = [
    'age', 'sex', 'cp', 'trestbps', 'chol', 'fbs', 'restecg', 
    'thalach', 'exang', 'oldpeak', 'slope', 'ca', 'thal', 'num'
]

def clean_uci() -> pd.DataFrame:
    """
    Clean the UCI Cleveland Heart Disease dataset.
    - Missing value removal/imputation.
    - Invalid data filtering.
    - Unit normalization.
    """
    raw_path = os.path.join(RAW_DATA_DIR, "processed.cleveland.data")
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"UCI Cleveland raw dataset not found at {raw_path}")
        
    print("🧹 Cleaning UCI Heart Disease Cleveland dataset...")
    # Load raw data (comma-separated, no headers, missing values might be '?')
    df = pd.read_csv(raw_path, header=None, names=UCI_COLUMNS, na_values='?')
    
    # 1. Missing Value Imputation
    # Fill numeric columns' missing values with their respective median
    for col in df.columns:
        if df[col].isnull().any():
            median_val = df[col].median()
            df[col].fillna(median_val, inplace=True)
            print(f"   Filled missing values in '{col}' with median: {median_val}")
            
    # 2. Invalid Data Filtering
    # Impossible heart rates: HR should be within [30, 220] bpm
    # Impossible resting blood pressures: trestbps should be within [60, 250] mmHg
    # Impossible cholesterol levels: chol should be within [80, 600] mg/dl
    initial_rows = len(df)
    
    # Filter heart rate outliers (e.g. the 999 values we injected)
    df = df[(df['thalach'] >= 30) & (df['thalach'] <= 220)]
    # Filter BP outliers
    df = df[(df['trestbps'] >= 60) & (df['trestbps'] <= 250)]
    # Filter cholesterol outliers (e.g. the -99 values)
    df = df[(df['chol'] >= 80) & (df['chol'] <= 600)]
    
    filtered_rows = initial_rows - len(df)
    if filtered_rows > 0:
        print(f"   Removed {filtered_rows} rows containing invalid physiological measurements.")
        
    # 3. Unit Normalization & Standard Types
    df['age'] = df['age'].astype(int)
    df['sex'] = df['sex'].astype(int)
    df['cp'] = df['cp'].astype(int)
    df['num'] = df['num'].astype(int) # Target heart disease level (0 = normal, 1-4 = heart disease)
    
    processed_path = os.path.join(PROCESSED_DATA_DIR, "cleaned_uci_heart.csv")
    df.to_csv(processed_path, index=False)
    print(f"✅ Cleaned UCI dataset saved to {processed_path} ({len(df)} records)")
    return df

def clean_physionet() -> Dict[str, Any]:
    """
    Parse and clean PhysioNet MIT-BIH Arrhythmia Record 100.
    - Unpacks binary format 212.
    - Noise reduction (moving average and baseline drift removal).
    - Unit normalization to physical millivolts.
    """
    hea_path = os.path.join(RAW_DATA_DIR, "100.hea")
    dat_path = os.path.join(RAW_DATA_DIR, "100.dat")
    
    if not (os.path.exists(hea_path) and os.path.exists(dat_path)):
        raise FileNotFoundError(f"MIT-BIH files 100.hea/dat not found in {RAW_DATA_DIR}")
        
    print("🧹 Parsing and cleaning PhysioNet MIT-BIH Record 100...")
    
    # Read header parameters
    baseline = 1024
    gain = 200
    with open(hea_path, "r") as f:
        for line in f:
            if "100.dat" in line:
                # Format: 100.dat 212 200 11 1024 ...
                parts = line.split()
                if len(parts) >= 5:
                    gain = float(parts[2].split('/')[0]) # 200 adu/mV
                    baseline = int(parts[4]) # 1024
                    
    # Read binary signal data (Format 212)
    with open(dat_path, "rb") as f:
        binary_data = f.read()
        
    ch1_raw = []
    ch2_raw = []
    
    # Format 212: 3 bytes pack two samples (ch1 and ch2)
    for i in range(0, len(binary_data) - 2, 3):
        b1 = binary_data[i]
        b2 = binary_data[i+1]
        b3 = binary_data[i+2]
        
        # Unpack values
        val1 = b1 | ((b2 & 0x0F) << 8)
        val2 = (b2 >> 4) | (b3 << 4)
        
        # Handle 12-bit signed offsets (WFDB baseline correction)
        ch1_raw.append(val1)
        ch2_raw.append(val2)
        
    ch1_raw = np.array(ch1_raw)
    ch2_raw = np.array(ch2_raw)
    
    # 1. Unit Normalization
    # Convert ADC values to millivolts (mV)
    ch1_mv = (ch1_raw - baseline) / gain
    ch2_mv = (ch2_raw - baseline) / gain
    
    # 2. Noise Reduction: Baseline Wander Drift Removal
    # We apply a high-pass filter approximation: subtract a slow rolling average
    # 1 second window is 360 samples
    window_size = 360
    ch1_drift = pd.Series(ch1_mv).rolling(window=window_size, center=True, min_periods=1).mean().values
    ch1_clean = ch1_mv - ch1_drift
    
    # 3. Noise Reduction: High-Frequency Smoothing
    # Smooth signal using a rolling moving average of 5 samples (14ms)
    ch1_clean = pd.Series(ch1_clean).rolling(window=5, center=True, min_periods=1).mean().values
    ch2_clean = pd.Series(ch2_mv).rolling(window=5, center=True, min_periods=1).mean().values
    
    # Save the cleaned signal data
    processed_signal_path = os.path.join(PROCESSED_DATA_DIR, "cleaned_ecg_signals.csv")
    pd.DataFrame({
        'time_sec': np.arange(len(ch1_clean)) / 360.0,
        'ch1_mlii_mv': np.round(ch1_clean, 4),
        'ch2_v5_mv': np.round(ch2_clean, 4)
    }).to_csv(processed_signal_path, index=False)
    
    print(f"✅ Cleaned ECG signal saved to {processed_signal_path} ({len(ch1_clean)} samples at 360Hz)")
    return {
        'ch1_clean': ch1_clean,
        'ch2_clean': ch2_clean,
        'fs': 360
    }

def clean_mimic() -> pd.DataFrame:
    """
    Clean the MIMIC-III Clinical Database Demo files.
    - Merges demographic profiles and time-series charts.
    - Missing value removal.
    - Invalid data filtering.
    - Unit normalization (Fahrenheit to Celsius).
    - Timestamp synchronization.
    """
    patients_path = os.path.join(RAW_DATA_DIR, "PATIENTS.csv")
    chartevents_path = os.path.join(RAW_DATA_DIR, "CHARTEVENTS.csv")
    
    if not (os.path.exists(patients_path) and os.path.exists(chartevents_path)):
        raise FileNotFoundError("MIMIC-III Demo PATIENTS.csv/CHARTEVENTS.csv not found in RAW_DATA_DIR")
        
    print("🧹 Cleaning MIMIC-III Demo clinical dataset...")
    patients_df = pd.read_csv(patients_path)
    chartevents_df = pd.read_csv(chartevents_path)
    
    # 1. Missing Value Removal
    # Drop rows in chart events where valuenum is null
    chartevents_df.dropna(subset=['valuenum'], inplace=True)
    
    # 2. Invalid Data Filtering
    # Item IDs mapping:
    # 220045: HR, 220179: Sys BP, 220180: Dia BP, 223762: Temp Celsius
    initial_len = len(chartevents_df)
    
    # Keep reasonable physiological values
    # HR: [30, 250]
    # Sys BP: [40, 260]
    # Dia BP: [20, 150]
    # Temp (Celsius): [25, 45]
    # Temp (Fahrenheit): [77, 113] (we will convert it next)
    
    def is_valid_vital(row):
        item = row['itemid']
        val = row['valuenum']
        if item == 220045: # HR
            return 30 <= val <= 250
        elif item == 220179: # Sys BP
            return 40 <= val <= 260
        elif item == 220180: # Dia BP
            return 20 <= val <= 150
        elif item == 223762: # Temp (could be in F or C depending on label)
            # If it's a large value, it's Fahrenheit, let's filter range for both
            return (25 <= val <= 45) or (77 <= val <= 113)
        return True
        
    valid_mask = chartevents_df.apply(is_valid_vital, axis=1)
    chartevents_df = chartevents_df[valid_mask]
    print(f"   Removed {initial_len - len(chartevents_df)} invalid vital readings.")
    
    # 3. Unit Normalization (Fahrenheit to Celsius conversion)
    # Check if any temp items are in F and convert them
    temp_mask = chartevents_df['itemid'] == 223762
    f_mask = temp_mask & (chartevents_df['valuenum'] > 50) # Fahrenheit readings are > 50
    if f_mask.any():
        chartevents_df.loc[f_mask, 'valuenum'] = (chartevents_df.loc[f_mask, 'valuenum'] - 32) * 5.0 / 9.0
        chartevents_df.loc[f_mask, 'valueuom'] = 'C'
        print(f"   Normalized {f_mask.sum()} Temperature values from Fahrenheit to Celsius.")
        
    # 4. Timestamp Synchronization & Merging
    # Parse chart time
    chartevents_df['charttime'] = pd.to_datetime(chartevents_df['charttime'])
    
    # Merge demographics (PATIENTS.csv) with chart events (CHARTEVENTS.csv)
    merged_df = pd.merge(
        chartevents_df, 
        patients_df[['subject_id', 'gender', 'dob']], 
        on='subject_id', 
        how='inner'
    )
    
    # Sort chronologically by subject_id and charttime
    merged_df.sort_values(by=['subject_id', 'charttime'], inplace=True)
    
    processed_path = os.path.join(PROCESSED_DATA_DIR, "cleaned_mimic_charts.csv")
    merged_df.to_csv(processed_path, index=False)
    print(f"✅ Cleaned MIMIC dataset saved to {processed_path} ({len(merged_df)} records)")
    return merged_df

def run_preprocessing():
    """Main function to run the Step 2 preprocessing pipeline"""
    clean_uci()
    clean_physionet()
    clean_mimic()
    print("\n🏁 Layer 1 - Step 2: Data Cleaning and Preprocessing completed successfully!")

if __name__ == "__main__":
    run_preprocessing()
