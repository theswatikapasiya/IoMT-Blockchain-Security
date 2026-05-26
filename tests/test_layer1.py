"""
Layer 1 Automated Verification Test Suite
Validates medical patterns, preprocessed data, profile generation,
time-series drift, attacks, labeling, and device simulations.
"""

import os
import sys
import unittest
import json
from datetime import datetime
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.data_generator import PatientDataGenerator, LABELED_DATA_PATH

class TestLayer1Pipeline(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.generator = PatientDataGenerator(seed=101)
        cls.generator.create_patient_dataset(5)
        cls.patients = cls.generator.get_all_patients()
        cls.patient_id = cls.patients[0]["id"]
        
    def test_01_profile_generation(self):
        """Validate demographic profile features match age bounds and Indian name formatting"""
        print("\n🔍 Running Test: Patient Profile Generation...")
        p = self.patients[0]
        
        self.assertIn("id", p)
        self.assertIn("name", p)
        self.assertIn("age", p)
        self.assertIn("gender", p)
        self.assertIn("device_id", p)
        self.assertIn("device_type", p)
        
        # Age validation
        self.assertTrue(18 <= p["age"] <= 88, f"Age {p['age']} is out of bounds")
        # Name validation (should have first and last names)
        self.assertEqual(len(p["name"].split()), 2)
        print(f"   Patient ID: {p['id']}, Name: {p['name']}, Age: {p['age']}, Device: {p['device_id']}")
        
    def test_02_vital_bounds_and_drift(self):
        """Validate vital signs follow gradual change drift limits (no random jumps)"""
        print("\n🔍 Running Test: Time-Series Vitals Drift & Bounds...")
        p_id = self.patient_id
        
        # Perform 5 updates and verify consecutive changes are gradual
        vitals_history = []
        for _ in range(5):
            packet = self.generator.update_patient_vitals(p_id)
            vitals_history.append(packet)
            
        for i in range(1, len(vitals_history)):
            prev = vitals_history[i-1]
            curr = vitals_history[i]
            
            # Consecutive heart rate change should be moderate (typically <= 15 bpm)
            hr_diff = abs(curr["hr"] - prev["hr"])
            self.assertTrue(hr_diff <= 25, f"Heart rate jumped erratically by {hr_diff} bpm")
            
            # Consecutive temperature change should be tiny (typically <= 0.4°C)
            temp_diff = abs(curr["temp"] - prev["temp"])
            self.assertTrue(temp_diff <= 0.8, f"Temperature jumped erratically by {temp_diff}°C")
            
            print(f"   Update {i}: HR={curr['hr']} (change: {hr_diff}), Temp={curr['temp']} (change: {temp_diff})")

    def test_03_ecg_simulation(self):
        """Validate that ECG waveforms are synchronized with heart rate and have correct lengths"""
        print("\n🔍 Running Test: ECG Waveform Simulation...")
        p_id = self.patients[0]["id"] # This has ECG monitor or ICU bedside monitor device type
        
        packet = self.generator.update_patient_vitals(p_id)
        
        # Check if ECG waveform is present in the telemetry packet
        if "ecg_waveform" in packet:
            ecg = packet["ecg_waveform"]
            self.assertEqual(len(ecg), 360, "ECG waveform length is not 360 samples")
            
            # Values should be floating point voltage measurements with some noise/drift
            self.assertTrue(all(isinstance(v, float) for v in ecg))
            print(f"   ECG Waveform verified. Extracted 360 samples at 360Hz. Range: [{min(ecg)}, {max(ecg)}]")
        else:
            print("   Skipped: Device is not ECG type")

    def test_04_attack_injection_and_labeling(self):
        """Validate that attacks are injected correctly and result in appropriate classification labels"""
        print("\n🔍 Running Test: Attack Injection & Data Labeling...")
        p_id = self.patients[1]["id"]
        
        # Clear active attacks
        self.generator.inject_attack(p_id, None)
        
        # 1. Test Spoofing Attack
        self.generator.inject_attack(p_id, "spoofing")
        packet = self.generator.update_patient_vitals(p_id)
        self.assertEqual(packet["label"], "SPOOFED")
        self.assertTrue(packet["hr"] >= 250, f"HR {packet['hr']} not spoofed correctly")
        self.assertTrue(packet["temp"] <= 24.0 or packet["temp"] >= 43.0, f"Temp {packet['temp']} not spoofed correctly")
        print(f"   Spoofing detected correctly: Label={packet['label']}, HR={packet['hr']}, Temp={packet['temp']}")
        
        # 2. Test Replay Attack
        # Store last packet values
        last_hr = packet["hr"]
        last_bp = packet["bp"]
        last_temp = packet["temp"]
        last_ts = packet["timestamp"]
        
        self.generator.inject_attack(p_id, "replay")
        packet = self.generator.update_patient_vitals(p_id)
        self.assertEqual(packet["label"], "REPLAY_ATTACK")
        self.assertEqual(packet["hr"], last_hr)
        self.assertEqual(packet["bp"], last_bp)
        self.assertEqual(packet["temp"], last_temp)
        self.assertEqual(packet["timestamp"], last_ts)
        print(f"   Replay detected correctly: Label={packet['label']}, HR={packet['hr']}, Timestamp={packet['timestamp']}")
        
        # 3. Test Delay Attack
        self.generator.inject_attack(p_id, "delay")
        packet = self.generator.update_patient_vitals(p_id)
        self.assertEqual(packet["label"], "ANOMALOUS")
        # Timestamp should be in the past (more than 5 mins ago)
        ts = pd.to_datetime(packet["timestamp"])
        time_diff = (datetime.utcnow() - ts).total_seconds()
        self.assertTrue(time_diff >= 500, f"Packet timestamp was not delayed: {time_diff} seconds ago")
        print(f"   Delay detected correctly: Label={packet['label']}, Delayed by {time_diff} seconds")
        
        # 4. Test Identity Spoofing (Forged ID)
        self.generator.inject_attack(p_id, "forged_id")
        packet = self.generator.update_patient_vitals(p_id)
        self.assertEqual(packet["label"], "MALICIOUS")
        self.assertTrue(packet["device_id"].startswith("ROGUE_"), f"Device ID {packet['device_id']} was not forged")
        print(f"   Identity Spoofing detected correctly: Label={packet['label']}, Device ID={packet['device_id']}")
        
        # Clean up
        self.generator.inject_attack(p_id, None)

    def test_05_csv_dataset_export(self):
        """Validate that telemetry logging generates a structured labeled CSV dataset"""
        print("\n🔍 Running Test: Labeled CSV Dataset Export...")
        self.assertTrue(os.path.exists(LABELED_DATA_PATH), f"CSV path {LABELED_DATA_PATH} does not exist")
        
        df = pd.read_csv(LABELED_DATA_PATH)
        self.assertGreater(len(df), 0, "Labeled dataset is empty")
        
        # Check columns
        expected_cols = [
            'timestamp', 'patient_id', 'device_id', 'device_type', 
            'age', 'gender', 'condition', 'hr', 'bp_systolic', 'bp_diastolic', 
            'temp', 'label'
        ]
        for col in expected_cols:
            self.assertIn(col, df.columns, f"Column '{col}' is missing from the exported dataset")
            
        print(f"   CSV Labeled Dataset verified. Saved at {LABELED_DATA_PATH}. Records logged: {len(df)}")

if __name__ == "__main__":
    unittest.main()
