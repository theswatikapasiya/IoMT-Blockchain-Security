"""
Layer 1 - Step 1: Real-World Medical Data Acquisition
Downloads medical datasets or generates high-fidelity fallbacks.
"""

import os
import zipfile
import requests
import numpy as np
import pandas as pd

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")

# URLs
UCI_HEART_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/processed.cleveland.data"
PHYSIONET_100_HEA = "https://physionet.org/files/mitdb/1.0.0/100.hea"
PHYSIONET_100_DAT = "https://physionet.org/files/mitdb/1.0.0/100.dat"
MIMIC_III_DEMO_ZIP = "https://physionet.org/files/mimiciii-demo/1.4/mimiciii-demo-1.4.zip"

def create_dirs():
    """Ensure directory structure exists"""
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    print(f"📁 Created directories:\n - {RAW_DATA_DIR}\n - {PROCESSED_DATA_DIR}")

def download_file(url: str, dest_path: str, timeout: int = 15) -> bool:
    """Download a file with a progress tracker/indicator and timeout"""
    try:
        print(f"📥 Attempting to download: {url}")
        response = requests.get(url, stream=True, timeout=timeout)
        if response.status_code == 200:
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"✅ Successfully downloaded to {dest_path}")
            return True
        else:
            print(f"⚠️  Failed to download. Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error downloading {url}: {e}")
        return False

def generate_fallback_uci():
    """Generate high-fidelity synthetic fallback for UCI Cleveland dataset"""
    print("🛠️  Generating fallback UCI Cleveland dataset...")
    np.random.seed(42)
    n_samples = 303
    
    # UCI Cleveland columns:
    # 1. age, 2. sex, 3. cp, 4. trestbps (resting BP), 5. chol (cholesterol),
    # 6. fbs (fasting blood sugar), 7. restecg, 8. thalach (max HR), 9. exang,
    # 10. oldpeak, 11. slope, 12. ca, 13. thal, 14. num (diagnosis)
    
    age = np.random.randint(29, 78, n_samples)
    sex = np.random.choice([0, 1], n_samples, p=[0.32, 0.68]) # 0=female, 1=male
    cp = np.random.choice([1, 2, 3, 4], n_samples, p=[0.1, 0.15, 0.25, 0.5])
    
    # Resting BP (trestbps) is correlated with age
    trestbps = 110 + (age * 0.4) + np.random.normal(0, 10, n_samples)
    trestbps = np.clip(trestbps, 90, 200).astype(int)
    
    # Cholesterol (chol)
    chol = 180 + (age * 0.6) + np.random.normal(0, 30, n_samples)
    chol = np.clip(chol, 120, 400).astype(int)
    
    fbs = np.random.choice([0, 1], n_samples, p=[0.85, 0.15])
    restecg = np.random.choice([0, 1, 2], n_samples, p=[0.48, 0.5, 0.02])
    
    # Max HR (thalach) is inversely correlated with age: 220 - age
    thalach = (220 - age) * 0.9 + np.random.normal(0, 15, n_samples)
    # Heart disease patients (num > 0) have lower max HR
    num = np.random.choice([0, 1, 2, 3, 4], n_samples, p=[0.54, 0.18, 0.12, 0.10, 0.06])
    thalach[num > 0] -= 15
    thalach = np.clip(thalach, 60, 202).astype(int)
    
    exang = np.zeros(n_samples)
    exang[num > 0] = np.random.choice([0, 1], sum(num > 0), p=[0.3, 0.7])
    exang[num == 0] = np.random.choice([0, 1], sum(num == 0), p=[0.9, 0.1])
    
    oldpeak = np.zeros(n_samples)
    oldpeak[num > 0] = np.abs(np.random.normal(1.5, 1.0, sum(num > 0)))
    oldpeak[num == 0] = np.abs(np.random.normal(0.2, 0.3, sum(num == 0)))
    oldpeak = np.round(oldpeak, 1)
    
    slope = np.random.choice([1, 2, 3], n_samples, p=[0.47, 0.46, 0.07])
    ca = np.random.choice([0.0, 1.0, 2.0, 3.0], n_samples, p=[0.58, 0.22, 0.13, 0.07])
    thal = np.random.choice([3.0, 6.0, 7.0], n_samples, p=[0.55, 0.06, 0.39])
    
    # Store as raw CSV without headers (matching the UCI archive format)
    df = pd.DataFrame({
        'age': age, 'sex': sex, 'cp': cp, 'trestbps': trestbps, 'chol': chol,
        'fbs': fbs, 'restecg': restecg, 'thalach': thalach, 'exang': exang,
        'oldpeak': oldpeak, 'slope': slope, 'ca': ca, 'thal': thal, 'num': num
    })
    
    # 5% missing values in trestbps, chol, thalach
    for col in ['trestbps', 'chol', 'thalach']:
        mask = np.random.random(n_samples) < 0.05
        df.loc[mask, col] = np.nan
        
    # Introduce some extreme invalid outliers to test filtering (Step 2)
    # e.g., 2% of heart rates are 999
    hr_outliers = np.random.random(n_samples) < 0.02
    df.loc[hr_outliers, 'thalach'] = 999.0
    
    # e.g., 2% of cholesterol are negative or impossible
    chol_outliers = np.random.random(n_samples) < 0.02
    df.loc[chol_outliers, 'chol'] = -99.0
    
    dest_path = os.path.join(RAW_DATA_DIR, "processed.cleveland.data")
    df.to_csv(dest_path, header=False, index=False)
    print(f"✅ Generated fallback UCI data at {dest_path}")

def generate_fallback_physionet():
    """Generate high-fidelity synthetic fallback for PhysioNet MIT-BIH Arrhythmia Record 100"""
    print("🛠️  Generating fallback MIT-BIH Record 100...")
    
    # Write .hea file
    hea_content = (
        "100 2 360 650000\n"
        "100.dat 212 200 11 1024 995 -22131 0 MLII\n"
        "100.dat 212 200 11 1024 1011 20052 0 V5\n"
        "# 69 M 1085 1629 x1\n"
        "# Comments: Baseline Normal ECG Simulation\n"
    )
    hea_path = os.path.join(RAW_DATA_DIR, "100.hea")
    with open(hea_path, "w") as f:
        f.write(hea_content)
        
    # Write mock binary .dat file (format 212 has 3 bytes for 2 samples, 1.5 bytes per sample)
    # Let's generate a simulated ECG waveform of 1000 samples (2 channels)
    # MLII channel will have a standard QRS complexes, V5 will be similar but smaller
    fs = 360  # Hz
    duration = 10  # seconds
    n_samples = fs * duration
    
    t = np.linspace(0, duration, n_samples)
    
    # Synthesize ECG (QRS, P, T waves)
    ecg_mlii = np.zeros(n_samples)
    ecg_v5 = np.zeros(n_samples)
    
    # Heart rate = 72 bpm -> 1.2 Hz -> beat every 0.83 seconds (300 samples)
    beat_interval = int(fs * 0.83)
    
    for i in range(0, n_samples, beat_interval):
        if i + 100 >= n_samples:
            break
        # P wave
        p_idx = i + int(fs * 0.1)
        ecg_mlii[p_idx-15 : p_idx+15] += 0.1 * np.exp(-((t[p_idx-15:p_idx+15] - t[p_idx])**2) / (0.02**2))
        
        # QRS complex
        q_idx = i + int(fs * 0.2)
        r_idx = i + int(fs * 0.22)
        s_idx = i + int(fs * 0.24)
        ecg_mlii[q_idx-5 : q_idx+5] -= 0.15 * np.exp(-((t[q_idx-5:q_idx+5] - t[q_idx])**2) / (0.005**2))
        ecg_mlii[r_idx-8 : r_idx+8] += 1.0 * np.exp(-((t[r_idx-8:r_idx+8] - t[r_idx])**2) / (0.008**2))
        ecg_mlii[s_idx-5 : s_idx+5] -= 0.25 * np.exp(-((t[s_idx-5:s_idx+5] - t[s_idx])**2) / (0.005**2))
        
        # T wave
        t_idx = i + int(fs * 0.4)
        ecg_mlii[t_idx-25 : t_idx+25] += 0.25 * np.exp(-((t[t_idx-25:t_idx+25] - t[t_idx])**2) / (0.04**2))
        
    # Scale to 11-bit ADC values (0 to 2047, baseline at 1024)
    # MLII has range -0.25 to 1.0. Let's map it to ADC
    ch1_adc = (1024 + ecg_mlii * 500).astype(int)
    ch2_adc = (1024 + ecg_mlii * 300 + np.random.normal(0, 0.05, n_samples) * 500).astype(int) # Add some noise
    
    # Introduce ECG baseline wander/drift noise (Step 2 Preprocessing will smooth this)
    drift = 100 * np.sin(2 * np.pi * 0.1 * t) # 0.1 Hz drift
    ch1_adc = (ch1_adc + drift).astype(int)
    
    # Format 212 packing:
    # Each pair of samples (ch1, ch2) takes 3 bytes:
    # Byte 1: low 8 bits of ch1
    # Byte 2: low 4 bits of ch2 (high nibble), low 4 bits of ch1 (low nibble)
    # Byte 3: low 8 bits of ch2
    # Wait, let's write them as integers in binary for simplicity. We can write a flat format 212 packer.
    dat_path = os.path.join(RAW_DATA_DIR, "100.dat")
    with open(dat_path, "wb") as f:
        for val1, val2 in zip(ch1_adc, ch2_adc):
            # Format 212 packing
            # val1 is 12-bit (0-4095)
            # val2 is 12-bit (0-4095)
            val1 = max(0, min(4095, val1))
            val2 = max(0, min(4095, val2))
            
            b1 = val1 & 0xFF
            b2 = ((val2 & 0x0F) << 4) | ((val1 >> 8) & 0x0F)
            b3 = (val2 >> 4) & 0xFF
            
            f.write(bytes([b1, b2, b3]))
            
    print(f"✅ Generated fallback MIT-BIH waveform data at {dat_path} and header at {hea_path}")

def generate_fallback_mimic():
    """Generate high-fidelity synthetic fallback for MIMIC-III ICU Demo Database"""
    print("🛠️  Generating fallback MIMIC-III clinical demo files...")
    
    np.random.seed(42)
    n_patients = 100
    
    # Generate PATIENTS.csv
    genders = np.random.choice(['M', 'F'], n_patients, p=[0.56, 0.44])
    # Age range 18-90
    ages = np.random.randint(18, 91, n_patients)
    # Birth dates
    dob_years = 2100 - ages # MIMIC dates are shifted to future (2100s)
    
    patients_data = {
        'row_id': range(1, n_patients + 1),
        'subject_id': [10000 + i for i in range(n_patients)],
        'gender': genders,
        'dob': [f"{yr}-06-15 00:00:00" for yr in dob_years],
        'dod': [np.nan] * n_patients,
        'expire_flag': [0] * n_patients
    }
    
    # Set a few deceased patients (15%)
    deceased = np.random.random(n_patients) < 0.15
    for idx in np.where(deceased)[0]:
        patients_data['dod'][idx] = f"2180-04-20 12:00:00"
        patients_data['expire_flag'][idx] = 1
        
    patients_df = pd.DataFrame(patients_data)
    patients_csv_path = os.path.join(RAW_DATA_DIR, "PATIENTS.csv")
    patients_df.to_csv(patients_csv_path, index=False)
    
    # Generate CHARTEVENTS.csv (vital trends)
    # ICU Chart records for heart rate, body temp, blood pressure
    chartevents_data = []
    row_idx = 1
    
    # Item IDs in MIMIC-III:
    # 220045: Heart Rate
    # 220179: Non Invasive Blood Pressure Systolic
    # 220180: Non Invasive Blood Pressure Diastolic
    # 223762: Temperature Celsius
    
    item_ids = {
        220045: ("Heart Rate", "bpm", 60, 100, 10),
        220179: ("SYS BP", "mmHg", 100, 140, 15),
        220180: ("DIA BP", "mmHg", 60, 90, 8),
        223762: ("Temperature", "C", 36.0, 37.5, 0.4)
    }
    
    # Let's create charts for 10 patients over 12 hours (hourly measurements)
    for p_idx in range(10):
        sub_id = patients_data['subject_id'][p_idx]
        hadm_id = 200000 + p_idx
        
        # Clinical condition baseline modifiers
        condition = np.random.choice(["Normal", "Critical", "Observation"], p=[0.6, 0.2, 0.2])
        hr_mod = 25 if condition == "Critical" else (10 if condition == "Observation" else 0)
        temp_mod = 1.5 if condition == "Critical" else (0.5 if condition == "Observation" else 0.0)
        
        for hr_offset in range(12):
            timestamp = f"2180-03-12 {8 + hr_offset:02d}:00:00"
            
            # Generate each vital sign
            for item_id, (name, unit, low, high, std) in item_ids.items():
                mean_val = (low + high) / 2
                
                # Apply modifiers
                if item_id == 220045: # HR
                    mean_val += hr_mod
                elif item_id == 223762: # Temp
                    mean_val += temp_mod
                elif item_id == 220179: # SYS BP
                    mean_val += hr_mod * 0.8
                
                val = np.random.normal(mean_val, std)
                val = round(val, 1) if item_id == 223762 else int(val)
                
                chartevents_data.append({
                    'row_id': row_idx,
                    'subject_id': sub_id,
                    'hadm_id': hadm_id,
                    'itemid': item_id,
                    'charttime': timestamp,
                    'valuenum': val,
                    'valueuom': unit,
                    'error': 0
                })
                row_idx += 1
                
    # Introduce some noise/nulls/impossible values in chart events to test cleaning
    chartevents_df = pd.DataFrame(chartevents_data)
    
    # 2% null values
    null_mask = np.random.random(len(chartevents_df)) < 0.02
    chartevents_df.loc[null_mask, 'valuenum'] = np.nan
    
    # 1% impossible values (e.g. Temp = -20 or HR = -99)
    outlier_mask = np.random.random(len(chartevents_df)) < 0.01
    for idx in np.where(outlier_mask)[0]:
        itemid = chartevents_df.loc[idx, 'itemid']
        if itemid == 220045:
            chartevents_df.loc[idx, 'valuenum'] = 999.0
        elif itemid == 223762:
            chartevents_df.loc[idx, 'valuenum'] = -20.0
            
    chartevents_csv_path = os.path.join(RAW_DATA_DIR, "CHARTEVENTS.csv")
    chartevents_df.to_csv(chartevents_csv_path, index=False)
    
    print(f"✅ Generated fallback MIMIC-III tables at {patients_csv_path} and {chartevents_csv_path}")

def run_acquisition():
    """Main function to run the Step 1 data acquisition pipeline"""
    create_dirs()
    
    # 1. Download UCI Cleveland Dataset
    uci_dest = os.path.join(RAW_DATA_DIR, "processed.cleveland.data")
    if not download_file(UCI_HEART_URL, uci_dest):
        generate_fallback_uci()
        
    # 2. Download PhysioNet MIT-BIH Arrhythmia Record 100
    physio_hea_dest = os.path.join(RAW_DATA_DIR, "100.hea")
    physio_dat_dest = os.path.join(RAW_DATA_DIR, "100.dat")
    if not (download_file(PHYSIONET_100_HEA, physio_hea_dest) and download_file(PHYSIONET_100_DAT, physio_dat_dest)):
        generate_fallback_physionet()
        
    # 3. Download MIMIC-III Clinical Database Demo
    mimic_zip_dest = os.path.join(RAW_DATA_DIR, "mimiciii-demo-1.4.zip")
    mimic_extracted = False
    
    # Let's try downloading the demo zip. If it fails, generate fallbacks.
    if download_file(MIMIC_III_DEMO_ZIP, mimic_zip_dest, timeout=25):
        try:
            print("📦 Extracting MIMIC-III Demo Zip...")
            with zipfile.ZipFile(mimic_zip_dest, 'r') as zip_ref:
                # Find PATIENTS.csv and CHARTEVENTS.csv in zip and extract to RAW_DATA_DIR
                for name in zip_ref.namelist():
                    if name.endswith("PATIENTS.csv"):
                        # Extract PATIENTS.csv
                        data = zip_ref.read(name)
                        with open(os.path.join(RAW_DATA_DIR, "PATIENTS.csv"), "wb") as f:
                            f.write(data)
                        print("✅ Extracted PATIENTS.csv")
                    elif name.endswith("CHARTEVENTS.csv"):
                        # Extract CHARTEVENTS.csv
                        data = zip_ref.read(name)
                        with open(os.path.join(RAW_DATA_DIR, "CHARTEVENTS.csv"), "wb") as f:
                            f.write(data)
                        print("✅ Extracted CHARTEVENTS.csv")
            mimic_extracted = True
        except Exception as e:
            print(f"⚠️  Error extracting MIMIC-III Demo zip: {e}")
            
    if not mimic_extracted:
        generate_fallback_mimic()
        
    print("\n🏁 Layer 1 - Step 1: Data Acquisition completed successfully!")

if __name__ == "__main__":
    run_acquisition()
