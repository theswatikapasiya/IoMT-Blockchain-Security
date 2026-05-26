"""
Patient Data Generator - Layer 2 Security Integration
Generates signed telemetry packets (HMAC-SHA256), API tokens,
and communication metadata matching the Zero Trust security specification.
"""

import os
import json
import random
import hmac
import hashlib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATTERNS_FILE = os.path.join(BASE_DIR, "data", "processed", "learned_patterns.json")
LABELED_DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "labeled_telemetry.csv")
REGISTRY_PATH = os.path.join(BASE_DIR, "data", "processed", "device_registry.json")

class PatientDataGenerator:
    """Generates signed telemetry packets and virtual patient profiles"""
    
    INDIAN_FIRST_NAMES = [
        "Arjun", "Priya", "Rahul", "Anjali", "Vikram", "Neha", "Aditya", "Pooja",
        "Rohan", "Divya", "Abhishek", "Shreya", "Nikhil", "Isha", "Varun", "Ananya",
        "Sanjay", "Diya", "Aman", "Nisha", "Karan", "Meera", "Harsh", "Richa"
    ]
    
    INDIAN_LAST_NAMES = [
        "Sharma", "Patel", "Singh", "Gupta", "Kumar", "Verma", "Rao", "Desai",
        "Nair", "Pillai", "Iyer", "Bhat", "Reddy", "Khan", "Chopra", "Saxena"
    ]
    
    DEVICE_TYPES = {
        "ECG": "ECG Bedside Monitor",
        "TEMP": "Digital Temperature Sensor",
        "ICU": "ICU Bedside Monitor",
        "WEAR": "Smart Health Wearable"
    }

    def __init__(self, seed=42):
        random.seed(seed)
        np.random.seed(seed)
        self.patients: Dict[str, Dict[str, Any]] = {}
        self.health_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Injected attacks configuration per patient
        self.active_attacks: Dict[str, str] = {}
        
        # Load patterns
        self.patterns = self._load_patterns()
        
        # Load registry
        self.device_registry: Dict[str, Any] = {}
        self._load_registry()
        
        # Initialize labeled telemetry export file
        self._initialize_csv_export()
        
    def _load_patterns(self) -> Dict[str, Any]:
        """Load the physiological patterns extracted in Steps 3 & 4"""
        if os.path.exists(PATTERNS_FILE):
            try:
                with open(PATTERNS_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Error loading learned patterns: {e}. Using fallback defaults.")
        
        return {
            "demographics_model": {"mean_age": 52.4, "std_age": 14.8, "age_bp_correlation": 0.42, "age_hr_correlation": -0.38},
            "physiological_baselines": {
                "Normal": {
                    "heart_rate": {"mean": 72.0, "std": 8.0},
                    "systolic_bp": {"mean": 115.0, "std": 10.0},
                    "diastolic_bp": {"mean": 75.0, "std": 6.0},
                    "temperature": {"mean": 36.8, "std": 0.3}
                },
                "Observation": {
                    "heart_rate": {"mean": 92.0, "std": 10.0},
                    "systolic_bp": {"mean": 135.0, "std": 12.0},
                    "diastolic_bp": {"mean": 88.0, "std": 8.0},
                    "temperature": {"mean": 37.8, "std": 0.5}
                },
                "Critical": {
                    "heart_rate": {"mean": 120.0, "std": 15.0},
                    "systolic_bp": {"mean": 160.0, "std": 18.0},
                    "diastolic_bp": {"mean": 105.0, "std": 12.0},
                    "temperature": {"mean": 39.0, "std": 0.8}
                }
            },
            "time_series_model": {
                "ar_coefficients": {
                    "temperature_hourly_diff_std": 0.15,
                    "temperature_ar_phi": 0.95,
                    "heart_rate_ar_phi": 0.82,
                    "bp_ar_phi": 0.85
                },
                "hrv_metrics": {"sdnn_ms": 50.0, "rmssd_ms": 42.0},
                "ecg_waveform_template": [0.0] * 180
            },
            "behavioral_model": {
                "state_transition_matrix": {
                    "Normal": {"Normal": 0.92, "Observation": 0.07, "Critical": 0.01},
                    "Observation": {"Normal": 0.10, "Observation": 0.85, "Critical": 0.05},
                    "Critical": {"Normal": 0.02, "Observation": 0.18, "Critical": 0.80}
                },
                "circadian_rhythm": {
                    "hr_night_dip_percent": 0.10,
                    "temp_night_dip_c": 0.4
                }
            }
        }
        
    def _load_registry(self):
        """Loads secure device registry from file system"""
        if os.path.exists(REGISTRY_PATH):
            import time
            for attempt in range(5):
                try:
                    with open(REGISTRY_PATH, "r") as f:
                        self.device_registry = json.load(f)
                    return
                except Exception as e:
                    if attempt == 4:
                        print(f"⚠️  Error reading registry in generator: {e}")
                    time.sleep(0.05)

    def _initialize_csv_export(self):
        """Create labeled telemetry CSV file with header if it does not exist"""
        os.makedirs(os.path.dirname(LABELED_DATA_PATH), exist_ok=True)
        if not os.path.exists(LABELED_DATA_PATH):
            df = pd.DataFrame(columns=[
                'timestamp', 'patient_id', 'device_id', 'device_type', 
                'age', 'gender', 'condition', 'hr', 'bp_systolic', 'bp_diastolic', 
                'temp', 'label'
            ])
            df.to_csv(LABELED_DATA_PATH, index=False)
            
    def _log_to_csv(self, packet: Dict[str, Any]):
        """Append a labeled packet record to the CSV training file"""
        try:
            sys, dia = 120, 80
            if "bp" in packet:
                try:
                    sys, dia = map(int, str(packet["bp"]).split("/"))
                except:
                    pass
            
            row = [{
                'timestamp': packet.get("timestamp"),
                'patient_id': packet.get("patient_id") or packet.get("id"),
                'device_id': packet.get("device_id"),
                'device_type': packet.get("device_type"),
                'age': packet.get("age", 50),
                'gender': packet.get("gender", "M"),
                'condition': packet.get("condition", "Normal"),
                'hr': packet.get("hr"),
                'bp_systolic': sys,
                'bp_diastolic': dia,
                'temp': packet.get("temp"),
                'label': packet.get("label", "NORMAL")
            }]
            df = pd.DataFrame(row)
            df.to_csv(LABELED_DATA_PATH, mode='a', header=False, index=False)
        except Exception as e:
            print(f"⚠️  Failed to log labeled data: {e}")

    def generate_patient_id(self, patient_num: int) -> str:
        """Generate unique patient ID"""
        return f"PS{1000 + patient_num}"
    
    def generate_patient_name(self) -> str:
        """Generate Indian patient name"""
        first = random.choice(self.INDIAN_FIRST_NAMES)
        last = random.choice(self.INDIAN_LAST_NAMES)
        return f"{first} {last}"
        
    def generate_patient_profile(self, patient_num: int) -> Dict[str, Any]:
        """Generate complete patient profile"""
        gender = random.choice(["M", "F"])
        model = self.patterns["demographics_model"]
        age = int(np.random.normal(model["mean_age"], model["std_age"]))
        age = max(18, min(88, age))
        
        patient_id = self.generate_patient_id(patient_num)
        
        # Load from registry if available
        self._load_registry()
        device_id = f"ECG_{1000 + patient_num}" if patient_num % 2 == 0 else f"TEMP_{1000 + patient_num}"
        device_type = self.DEVICE_TYPES["ECG"] if patient_num % 2 == 0 else self.DEVICE_TYPES["TEMP"]
        
        if device_id in self.device_registry:
            device_type = self.device_registry[device_id].get("device_type", device_type)
            
        bedtime = random.randint(21, 23)
        waketime = random.randint(5, 7)
        recovery_rate = round(0.1 + (90 - age) * 0.005, 3) 
        
        return {
            "id": patient_id,
            "name": self.generate_patient_name(),
            "age": age,
            "gender": gender,
            "bloodGroup": random.choice(["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]),
            "contact": f"+91-{random.randint(6000000000, 9999999999)}",
            "email": f"patient{patient_num}@hospital.in",
            "admissionDate": datetime.utcnow().isoformat(),
            "condition": random.choice(["Normal", "Observation", "Critical"]),
            "assignedDoctor": f"Dr. {random.choice(self.INDIAN_LAST_NAMES)}",
            "device_id": device_id,
            "device_type": device_type,
            "bedtime": bedtime,
            "waketime": waketime,
            "recovery_rate": recovery_rate
        }

    def generate_realistic_vitals(self, patient_profile: Dict = None) -> Dict[str, Any]:
        """Generates time-series patient vital signs using autoregressive modeling"""
        if not patient_profile:
            patient_profile = {"age": 50, "condition": "Normal", "bedtime": 22, "waketime": 6, "recovery_rate": 0.2}
            
        condition = patient_profile.get("condition", "Normal")
        age = patient_profile.get("age", 50)
        
        baseline = self.patterns["physiological_baselines"].get(condition, self.patterns["physiological_baselines"]["Normal"])
        
        bp_sys_base = baseline["systolic_bp"]["mean"] + (age - 50) * 0.3
        bp_dia_base = baseline["diastolic_bp"]["mean"] + (age - 50) * 0.15
        hr_base = baseline["heart_rate"]["mean"] + (age - 50) * 0.1
        temp_base = baseline["temperature"]["mean"]
        
        now = datetime.utcnow()
        hour = now.hour
        is_night = hour >= patient_profile.get("bedtime", 22) or hour < patient_profile.get("waketime", 6)
        
        if is_night:
            dip_pct = self.patterns["behavioral_model"]["circadian_rhythm"]["hr_night_dip_percent"]
            temp_dip = self.patterns["behavioral_model"]["circadian_rhythm"]["temp_night_dip_c"]
            hr_base *= (1.0 - dip_pct)
            temp_base -= temp_dip
            
        patient_id = patient_profile.get("id")
        history = self.health_history.get(patient_id)
        ar = self.patterns["time_series_model"]["ar_coefficients"]
        
        if history and len(history) > 0:
            last = history[-1]
            prev_hr = last.get("hr", hr_base)
            prev_temp = last.get("temp", temp_base)
            
            try:
                prev_sys, prev_dia = map(int, last.get("bp", f"{bp_sys_base}/{bp_dia_base}").split("/"))
            except:
                prev_sys, prev_dia = bp_sys_base, bp_dia_base
                
            hr = hr_base + ar["heart_rate_ar_phi"] * (prev_hr - hr_base) + np.random.normal(0, 2)
            temp = temp_base + ar["temperature_ar_phi"] * (prev_temp - temp_base) + np.random.normal(0, 0.05)
            bp_sys = bp_sys_base + ar["bp_ar_phi"] * (prev_sys - bp_sys_base) + np.random.normal(0, 3)
            bp_dia = bp_dia_base + ar["bp_ar_phi"] * (prev_dia - bp_dia_base) + np.random.normal(0, 1.5)
        else:
            hr = np.random.normal(hr_base, baseline["heart_rate"]["std"])
            temp = np.random.normal(temp_base, baseline["temperature"]["std"])
            bp_sys = np.random.normal(bp_sys_base, baseline["systolic_bp"]["std"])
            bp_dia = np.random.normal(bp_dia_base, baseline["diastolic_bp"]["std"])
            
        hr = int(np.clip(hr, 45, 180))
        temp = round(float(np.clip(temp, 35.0, 42.0)), 1)
        bp_sys = int(np.clip(bp_sys, 70, 220))
        bp_dia = int(np.clip(bp_dia, 40, 120))
        
        return {
            "hr": hr,
            "bp": f"{bp_sys}/{bp_dia}",
            "temp": temp,
            "timestamp": datetime.utcnow().isoformat()
        }

    def generate_ecg_stream(self, hr: int, length: int = 180) -> List[float]:
        """Generates a continuous ECG waveform segment matching the active Heart Rate"""
        template = self.patterns["time_series_model"]["ecg_waveform_template"]
        if not template or len(template) < 50:
            template = [0.0] * 180
            
        samples_per_beat = int(360 * (60.0 / hr))
        xp = np.linspace(0, len(template) - 1, len(template))
        x = np.linspace(0, len(template) - 1, samples_per_beat)
        resampled_beat = np.interp(x, xp, template)
        
        if len(resampled_beat) >= length:
            output = resampled_beat[:length].tolist()
        else:
            repeats = int(np.ceil(length / len(resampled_beat)))
            output = np.tile(resampled_beat, repeats)[:length].tolist()
            
        noise = np.random.normal(0, 0.015, length)
        drift = 0.05 * np.sin(2 * np.pi * 0.2 * np.arange(length) / 360.0)
        
        final_signal = (np.array(output) + noise + drift).tolist()
        return [round(v, 4) for v in final_signal]

    def create_patient_dataset(self, num_patients: int = 20) -> List[Dict[str, Any]]:
        """Generate complete initial patient dataset"""
        patients = []
        for i in range(num_patients):
            profile = self.generate_patient_profile(i)
            vitals = self.generate_realistic_vitals(profile)
            
            patient_data = {**profile, **vitals}
            patient_data["label"] = "NORMAL" if profile["condition"] != "Critical" else "ANOMALOUS"
            
            self.patients[profile["id"]] = patient_data
            self.health_history[profile["id"]] = [vitals]
            patients.append(patient_data)
            
        return patients

    def inject_attack(self, patient_id: str, attack_type: str):
        """Set active attack state for a patient device"""
        if patient_id in self.patients:
            self.active_attacks[patient_id] = attack_type
            print(f"🚨 Security simulation: Activated {attack_type} attack on patient {patient_id}")

    def update_patient_vitals(self, patient_id: str) -> Dict[str, Any]:
        """Updates vitals, performs transitions, signs packets, and handles attacks"""
        if patient_id not in self.patients:
            return {}
            
        patient = self.patients[patient_id]
        
        # 1. State Transition
        matrix = self.patterns["behavioral_model"]["state_transition_matrix"]
        current_state = patient.get("condition", "Normal")
        states = list(matrix[current_state].keys())
        probs = list(matrix[current_state].values())
        next_state = np.random.choice(states, p=probs)
        if next_state != current_state:
            patient["condition"] = next_state
            
        # 2. Generate vitals
        vitals = self.generate_realistic_vitals(patient)
        
        # Default safety labeling
        label = "NORMAL" if next_state != "Critical" else "ANOMALOUS"
        device_id = patient.get("device_id", f"ECG_{patient_id}")
        device_type = patient.get("device_type", "ECG Bedside Monitor")
        
        # Get active device registry details
        self._load_registry()
        dev_info = self.device_registry.get(device_id, {})
        auth_key = dev_info.get("auth_key", "default_secret_key")
        api_token = dev_info.get("api_token", "default_api_token")
        
        # 3. Security Attack Injection (Step 8 & 9)
        attack = self.active_attacks.get(patient_id)
        
        # Communication channel properties
        network_port = 8883 # Secure TLS port default
        encryption_used = "TLSv1.3"
        
        if attack == "spoofing":
            vitals["hr"] = random.randint(250, 320)
            vitals["temp"] = round(random.uniform(18.0, 24.0), 1)
            vitals["bp"] = f"{random.randint(240, 290)}/{random.randint(150, 180)}"
            label = "SPOOFED"
            
        elif attack == "replay":
            # Replay the last packet's vitals and timestamp
            history = self.health_history.get(patient_id, [])
            if len(history) > 0:
                last_record = history[-1]
                vitals["hr"] = last_record.get("hr", vitals["hr"])
                vitals["bp"] = last_record.get("bp", vitals["bp"])
                vitals["temp"] = last_record.get("temp", vitals["temp"])
                vitals["timestamp"] = last_record.get("timestamp", vitals["timestamp"])
            label = "REPLAY_ATTACK"
            
        elif attack == "delay":
            # Backdate timestamp by 10 minutes, use unencrypted channel (Step 5 simulation)
            delay_time = datetime.utcnow() - timedelta(minutes=10)
            vitals["timestamp"] = delay_time.isoformat()
            network_port = 1883 # Unsecured MQTT port
            encryption_used = "None"
            label = "ANOMALOUS"
            
        elif attack == "forged_id":
            # Change device ID to unauthorized ROGUE prefix
            device_id = f"ROGUE_{random.randint(1000, 9999)}"
            label = "MALICIOUS"
            
        # 4. Cryptographic HMAC Signature Generation (Step 3)
        # Construct HMAC signature over data keys
        msg_payload = f"{patient_id}|{vitals['hr']}|{vitals['bp']}|{vitals['temp']}|{vitals['timestamp']}"
        signature = hmac.new(auth_key.encode(), msg_payload.encode(), hashlib.sha256).hexdigest()
        
        # Inject key mismatches if requested
        if attack == "sig_mismatch":
            signature = "forged_signature_hash_37c89a01f8"
            label = "MALICIOUS"
        elif attack == "invalid_token":
            api_token = "invalid_token_xyz"
            label = "MALICIOUS"
            
        # Telemetry payload
        telemetry_packet = {
            "device_id": device_id,
            "device_type": device_type,
            "patient_id": patient_id,
            "id": patient_id,
            "name": patient["name"],
            "age": patient["age"],
            "gender": patient["gender"],
            "condition": patient["condition"],
            "hr": vitals["hr"],
            "bp": vitals["bp"],
            "temp": vitals["temp"],
            "timestamp": vitals["timestamp"],
            "label": label,
            "api_token": api_token,
            "packet_signature": signature,
            "sensor_metadata": {
                "protocol_version": "v1.2",
                "calibration_status": "Calibrated"
            },
            "communication_metadata": {
                "network_port": network_port,
                "encryption": encryption_used
            }
        }
        
        if "ECG" in device_type:
            telemetry_packet["ecg_waveform"] = self.generate_ecg_stream(vitals["hr"], length=360)
            
        # Append record to health history
        if patient_id not in self.health_history:
            self.health_history[patient_id] = []
        self.health_history[patient_id].append(vitals)
        
        if len(self.health_history[patient_id]) > 100:
            self.health_history[patient_id] = self.health_history[patient_id][-100:]
            
        # Cache updates in generator memory
        patient.update(vitals)
        patient["label"] = label
        
        # Log to labeled telemetry CSV
        self._log_to_csv(telemetry_packet)
        
        return telemetry_packet

    def get_patient(self, patient_id: str) -> Dict[str, Any]:
        """Get patient profile with history"""
        if patient_id not in self.patients:
            return {}
        return {
            "profile": self.patients[patient_id],
            "history": self.health_history.get(patient_id, [])
        }
        
    def get_all_patients(self) -> List[Dict[str, Any]]:
        """Get all patients"""
        return list(self.patients.values())
        
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate overall statistics"""
        if not self.patients:
            return {}
            
        all_patients = self.get_all_patients()
        avg_hr = sum([p.get("hr", 0) for p in all_patients]) / len(all_patients)
        avg_temp = sum([p.get("temp", 0) for p in all_patients]) / len(all_patients)
        
        bps_sys = []
        for p in all_patients:
            try:
                sys, dia = map(int, str(p.get("bp", "120/80")).split("/"))
                bps_sys.append(sys)
            except:
                pass
                
        avg_bp_sys = sum(bps_sys) / len(bps_sys) if bps_sys else 0
        
        return {
            "total_patients": len(self.patients),
            "average_hr": round(avg_hr, 1),
            "average_bp_sys": round(avg_bp_sys, 1),
            "average_temp": round(avg_temp, 1),
            "critical_patients": len([p for p in all_patients if p.get("condition") == "Critical"]),
            "observation_patients": len([p for p in all_patients if p.get("condition") == "Observation"]),
            "active_attacks_count": len([k for k, v in self.active_attacks.items() if v is not None])
        }

# Global data generator
patient_generator = PatientDataGenerator()
