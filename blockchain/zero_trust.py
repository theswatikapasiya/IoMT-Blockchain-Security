"""
Layer 2 - Zero Trust Device Authentication and Edge Validation Layer
Implements cryptographic validation, identity verification, physiological ranges,
behavioral consistency checks, trust scoring, and forensic audit logging.
"""

import os
import json
import time
import hmac
import hashlib
import numpy as np
import pandas as pd
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, List

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(BASE_DIR, "data", "processed", "device_registry.json")
AUDIT_LOG_PATH = os.path.join(BASE_DIR, "data", "processed", "security_audit_log.json")
QUARANTINE_PATH = os.path.join(BASE_DIR, "data", "processed", "quarantine_log.json")

FILE_LOCK = threading.Lock()

class ZeroTrustValidator:
    """Enforces zero-trust checks on all incoming IoMT healthcare packets"""
    
    APPROVED_MANUFACTURERS = ["Philips Healthcare", "Medtronic", "Fitbit", "GE Healthcare"]
    
    def __init__(self):
        self.lock = threading.Lock()
        os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
        self.device_registry = self._load_or_create_registry()
        self.timestamp_caches: Dict[str, List[str]] = {} # Cache of recent timestamps per device
        
        # Initialize log files
        self._init_json_file(AUDIT_LOG_PATH)
        self._init_json_file(QUARANTINE_PATH)

    def _init_json_file(self, path: str):
        """Create empty JSON array file if it does not exist"""
        with FILE_LOCK:
            if not os.path.exists(path):
                with open(path, "w") as f:
                    json.dump([], f)

    def _load_or_create_registry(self) -> Dict[str, Any]:
        """Load secure device registry or generate a default one mapping patient IDs"""
        with FILE_LOCK:
            if os.path.exists(REGISTRY_PATH):
                try:
                    with open(REGISTRY_PATH, "r") as f:
                        return json.load(f)
                except Exception as e:
                    print(f"⚠️  Error reading registry: {e}. Recreating...")
                    
            # Generate registry for 20 patients (PS1000 - PS1019)
            registry = {}
            for i in range(20):
                patient_id = f"PS{1000 + i}"
                device_id = f"ECG_{1000 + i}" if i % 2 == 0 else f"TEMP_{1000 + i}"
                device_type = "ECG Bedside Monitor" if i % 2 == 0 else "Digital Temperature Sensor"
                manufacturer = self.APPROVED_MANUFACTURERS[i % len(self.APPROVED_MANUFACTURERS)]
                
                # Cryptographic keys
                token = f"tok_{device_id.lower()}_{hashlib.sha256(f'token_{patient_id}'.encode()).hexdigest()[:16]}"
                key = f"key_{device_id.lower()}_{hashlib.sha256(f'secret_{patient_id}'.encode()).hexdigest()[:16]}"
                
                registry[device_id] = {
                    "device_id": device_id,
                    "device_type": device_type,
                    "patient_id": patient_id,
                    "status": "Active",
                    "manufacturer": manufacturer,
                    "api_token": token,
                    "auth_key": key,
                    "trust_score": 100.0,
                    "status_reason": "Registered",
                    "last_hr": 72,
                    "last_temp": 37.0,
                    "last_bp_sys": 120,
                    "last_bp_dia": 80,
                    "last_timestamp": None,
                    "recent_failures": 0,
                    "total_packets": 0,
                    "vital_history": [] # Cache for sliding window jitter checks
                }
                
            try:
                tmp_path = REGISTRY_PATH + ".tmp"
                with open(tmp_path, "w") as f:
                    json.dump(registry, f, indent=4)
                os.replace(tmp_path, REGISTRY_PATH)
            except Exception as e:
                print(f"⚠️  Failed to save initial registry atomically: {e}")
                with open(REGISTRY_PATH, "w") as f:
                    json.dump(registry, f, indent=4)

            print(f"✅ Secure device registry initialized with {len(registry)} devices at {REGISTRY_PATH}")
            return registry

    def _save_registry(self):
        """Save registry updates to disk"""
        with FILE_LOCK:
            try:
                os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
                tmp_path = REGISTRY_PATH + ".tmp"
                with open(tmp_path, "w") as f:
                    json.dump(self.device_registry, f, indent=4)
                os.replace(tmp_path, REGISTRY_PATH)
            except Exception as e:
                print(f"⚠️  Failed to save registry: {e}")

    def _log_audit_event(self, entry: Dict[str, Any], path: str):
        """Append log entry to JSON log file"""
        with self.lock:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                logs = []
                if os.path.exists(path):
                    try:
                        with open(path, "r") as f:
                            logs = json.load(f)
                        if not isinstance(logs, list):
                            logs = []
                    except Exception as e:
                        print(f"⚠️  Log file corrupted, resetting: {e}")
                        logs = []
                logs.append(entry)
                
                # Limit logs size in memory if needed
                if len(logs) > 500:
                    logs = logs[-500:]
                    
                tmp_path = path + ".tmp"
                with open(tmp_path, "w") as f:
                    json.dump(logs, f, indent=4)
                os.replace(tmp_path, path)
            except Exception as e:
                print(f"⚠️  Failed to write security log: {e}")

    def validate_packet(self, packet: Dict[str, Any], topic: str = "iot/hospital/patients", is_tls: bool = True) -> Tuple[str, float, List[str]]:
        """
        Runs Steps 2 to 10.
        Returns: (decision, packet_trust_score, failure_reasons)
        Decision is one of: ACCEPT, FLAG, REJECT, QUARANTINE
        """
        reasons = []
        packet_score = 100.0
        
        # 1. Step 5 (Part 1): Protocol compliance / Schema format checks
        required_keys = ["device_id", "patient_id", "hr", "bp", "temp", "timestamp"]
        for key in required_keys:
            if key not in packet:
                return "REJECT", 0.0, [f"MISSING_PARAMETER_{key.upper()}"]
                
        device_id = packet["device_id"]
        patient_id = packet["patient_id"]
        
        # 2. Step 2: Device Identity Verification
        if device_id not in self.device_registry:
            reasons.append("DEVICE_NOT_REGISTERED")
            self._log_forensics(packet, "REJECT", 0.0, ["DEVICE_NOT_REGISTERED"])
            return "REJECT", 0.0, ["DEVICE_NOT_REGISTERED"]
            
        dev = self.device_registry[device_id]
        
        # Active status check
        if dev["status"] == "Isolated":
            reasons.append("DEVICE_ISOLATED")
            self._log_forensics(packet, "REJECT", 0.0, ["DEVICE_ISOLATED"])
            return "REJECT", 0.0, ["DEVICE_ISOLATED"]
        elif dev["status"] == "Suspended":
            reasons.append("DEVICE_SUSPENDED")
            packet_score -= 100.0
        elif dev["status"] == "Maintenance Required":
            reasons.append("DEVICE_NEEDS_MAINTENANCE")
            packet_score -= 20.0
            
        # Manufacturer validation
        if dev["manufacturer"] not in self.APPROVED_MANUFACTURERS:
            reasons.append("UNAUTHORIZED_MANUFACTURER")
            packet_score -= 40.0
            
        # Patient-device association check
        if dev["patient_id"] != patient_id:
            reasons.append("UNAUTHORIZED_PATIENT_DEVICE_ASSOCIATION")
            packet_score -= 100.0 # Strict mismatch penalty
            
        # 3. Step 3: API Token and Digital Signature Authentication
        # Token validation
        packet_token = packet.get("api_token")
        if packet_token != dev["api_token"]:
            reasons.append("INVALID_API_TOKEN")
            packet_score -= 50.0
            
        # Digital signature HMAC-SHA256 validation
        packet_sig = packet.get("packet_signature")
        auth_key = dev["auth_key"]
        
        # Construct HMAC signature payload matching generator
        # payload_str = f"{patient_id}|{hr}|{bp}|{temp}|{timestamp}"
        msg_payload = f"{patient_id}|{packet['hr']}|{packet['bp']}|{packet['temp']}|{packet['timestamp']}"
        expected_sig = hmac.new(auth_key.encode(), msg_payload.encode(), hashlib.sha256).hexdigest()
        
        if packet_sig != expected_sig:
            reasons.append("CRYPTOGRAPHIC_SIGNATURE_MISMATCH")
            packet_score -= 50.0

        # 4. Step 4: Timestamp Validation
        try:
            ts_str = packet["timestamp"]
            ts = pd.to_datetime(ts_str)
            now = datetime.utcnow()
            
            # Freshness delay check (max ±30 seconds window)
            time_diff = abs((now - ts).total_seconds())
            if time_diff > 30.0:
                reasons.append("TIMESTAMP_EXCEEDS_FRESHNESS_WINDOW")
                packet_score -= 30.0
                
            # Chronological sequence and duplicate check
            if device_id not in self.timestamp_caches:
                self.timestamp_caches[device_id] = []
                
            if dev["last_timestamp"]:
                last_ts = pd.to_datetime(dev["last_timestamp"])
                if ts <= last_ts:
                    reasons.append("CHRONOLOGICAL_SEQUENCE_VIOLATION_OR_REPLAY")
                    packet_score -= 30.0
                    
            if ts_str in self.timestamp_caches[device_id]:
                reasons.append("DUPLICATE_TIMESTAMP_DETECTED")
                packet_score -= 30.0
            else:
                self.timestamp_caches[device_id].append(ts_str)
                if len(self.timestamp_caches[device_id]) > 100:
                    self.timestamp_caches[device_id].pop(0)
        except Exception as e:
            reasons.append(f"INVALID_TIMESTAMP_FORMAT_{str(e)}")
            packet_score -= 30.0

        # 5. Step 5 (Part 2): Communication Channel Validation
        # Topic compliance check
        if topic != "iot/hospital/patients":
            reasons.append("UNAUTHORIZED_MQTT_TOPIC")
            packet_score -= 30.0
            
        # Encryption (TLS) verification
        if not is_tls:
            reasons.append("UNENCRYPTED_COMMUNICATION_CHANNEL")
            packet_score -= 30.0

        # 6. Step 6: Physiological Range Validation
        hr = int(packet["hr"])
        temp = float(packet["temp"])
        try:
            sys_bp, dia_bp = map(int, str(packet["bp"]).split("/"))
        except Exception:
            sys_bp, dia_bp = -1, -1
            reasons.append("INVALID_BP_FORMAT")
            packet_score -= 40.0
            
        # HR bounds: [30, 220] bpm
        if hr < 30 or hr > 220:
            reasons.append("HR_OUT_OF_PHYSIOLOGICAL_BOUNDS")
            packet_score -= 40.0
            
        # Temp bounds: [30.0, 45.0] °C
        if temp < 30.0 or temp > 45.0:
            reasons.append("TEMP_OUT_OF_PHYSIOLOGICAL_BOUNDS")
            packet_score -= 40.0
            
        # BP bounds: Systolic [50, 250], Diastolic [30, 150]
        if sys_bp < 50 or sys_bp > 250 or dia_bp < 30 or dia_bp > 150:
            reasons.append("BP_OUT_OF_PHYSIOLOGICAL_BOUNDS")
            packet_score -= 40.0

        # 7. Step 7: Behavioral Consistency Analysis
        # Compare vital steps against registered preceding trends
        if dev["last_timestamp"] is not None:
            # Check Heart Rate jump
            hr_jump = abs(hr - dev["last_hr"])
            if hr_jump > 30:
                reasons.append("HR_ABRUPT_BEHAVIORAL_JUMP")
                packet_score -= 30.0
                
            # Check Temp jump
            temp_jump = abs(temp - dev["last_temp"])
            if temp_jump > 1.0:
                reasons.append("TEMP_ABRUPT_BEHAVIORAL_JUMP")
                packet_score -= 30.0
                
            # Check BP jump
            bp_sys_jump = abs(sys_bp - dev["last_bp_sys"])
            if bp_sys_jump > 30:
                reasons.append("BP_ABRUPT_BEHAVIORAL_JUMP")
                packet_score -= 30.0

        # 8. Step 8: Device Health & Jitter Monitoring
        # Append to vital history for local sliding-window standard deviation calculations
        dev["vital_history"].append(hr)
        if len(dev["vital_history"]) > 10:
            dev["vital_history"].pop(0)
            
        if len(dev["vital_history"]) >= 5:
            # Calculate Heart Rate variance (Jitter)
            hr_std = np.std(dev["vital_history"])
            if hr_std > 25.0: # Abnormally high local variation represents sensor noise/jitter
                reasons.append("HIGH_SENSOR_JITTER_DETECTED")
                packet_score -= 15.0

        # Calculate final clamped packet score (Step 9)
        packet_score = max(0.0, packet_score)
        
        # Update running trust score using exponential moving average (Step 9)
        dev["trust_score"] = round(0.8 * dev["trust_score"] + 0.2 * packet_score, 1)
        dev["total_packets"] += 1
        
        # 9. Step 8: Health checks warning accumulation
        has_validation_warning = any(r in reasons for r in [
            "HR_OUT_OF_PHYSIOLOGICAL_BOUNDS", "TEMP_OUT_OF_PHYSIOLOGICAL_BOUNDS", 
            "BP_OUT_OF_PHYSIOLOGICAL_BOUNDS", "HR_ABRUPT_BEHAVIORAL_JUMP",
            "TEMP_ABRUPT_BEHAVIORAL_JUMP", "BP_ABRUPT_BEHAVIORAL_JUMP",
            "HIGH_SENSOR_JITTER_DETECTED"
        ])
        
        if has_validation_warning:
            dev["recent_failures"] += 1
        else:
            dev["recent_failures"] = max(0, dev["recent_failures"] - 1)
            
        # Isolate device if failing repeatedly
        if dev["recent_failures"] >= 3:
            dev["status"] = "Maintenance Required"
            dev["status_reason"] = "Repeated physiological validation errors"
            dev["trust_score"] = max(0.0, dev["trust_score"] - 30.0) # Penalty for quarantine
            reasons.append("HARDWARE_MALFUNCTION_DECLARED")

        # 10. Step 10: Edge Decision Routing
        decision = "ACCEPT"
        
        # Strict quarantine triggers (cryptographic tampering or replay attacks)
        quarantine_triggers = [
            "CRYPTOGRAPHIC_SIGNATURE_MISMATCH", "INVALID_API_TOKEN", 
            "DUPLICATE_TIMESTAMP_DETECTED", "CHRONOLOGICAL_SEQUENCE_VIOLATION_OR_REPLAY"
        ]
        
        if any(r in reasons for r in quarantine_triggers) or packet_score < 50.0:
            decision = "QUARANTINE"
            
        # Flat rejects (totally unregistered devices or severe association issues)
        reject_triggers = ["DEVICE_NOT_REGISTERED", "UNAUTHORIZED_PATIENT_DEVICE_ASSOCIATION"]
        if any(r in reasons for r in reject_triggers):
            decision = "REJECT"
            
        # Flags (moderate warnings, trust score [50, 79])
        if decision == "ACCEPT" and (50.0 <= packet_score < 80.0 or dev["status"] == "Maintenance Required"):
            decision = "FLAG"

        # Update last accepted values in registry to compare trends next time
        if decision in ["ACCEPT", "FLAG"]:
            dev["last_hr"] = hr
            dev["last_temp"] = temp
            dev["last_bp_sys"] = sys_bp
            dev["last_bp_dia"] = dia_bp
            dev["last_timestamp"] = packet["timestamp"]
            
        # Save registry state
        self._save_registry()
        
        # 11. Step 11: Security logging and forensic recording
        self._log_forensics(packet, decision, packet_score, reasons)
        
        return decision, packet_score, reasons

    def isolate_device(self, device_id: str, reason: str = "Autonomous security response isolation") -> bool:
        """Isolate a compromised device in the registry"""
        if device_id in self.device_registry:
            self.device_registry[device_id]["status"] = "Isolated"
            self.device_registry[device_id]["status_reason"] = reason
            self._save_registry()
            return True
        return False

    def activate_device(self, device_id: str) -> bool:
        """Activate an isolated or suspended device in the registry"""
        if device_id in self.device_registry:
            self.device_registry[device_id]["status"] = "Active"
            self.device_registry[device_id]["status_reason"] = "Restored by clinician/administrator"
            self.device_registry[device_id]["recent_failures"] = 0
            self.device_registry[device_id]["trust_score"] = 100.0
            self._save_registry()
            return True
        return False

    def _log_forensics(self, packet: Dict[str, Any], decision: str, score: float, reasons: List[str]):
        """Step 11: Writes complete security details to audit logs and quarantines if needed"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "device_id": packet.get("device_id", "UNKNOWN"),
            "patient_id": packet.get("patient_id", "UNKNOWN"),
            "packet_timestamp": packet.get("timestamp"),
            "packet_meta": {
                "hr": packet.get("hr"),
                "bp": packet.get("bp"),
                "temp": packet.get("temp"),
                "api_token": packet.get("api_token")
            },
            "decision": decision,
            "trust_score": score,
            "rejection_reasons": reasons
        }
        
        # Write to security audit log
        self._log_audit_event(log_entry, AUDIT_LOG_PATH)
        
        # Write to quarantine log if isolated
        if decision == "QUARANTINE":
            self._log_audit_event(log_entry, QUARANTINE_PATH)
            print(f"⚠️  SECURITY AUDIT: Telemetry packet from device {log_entry['device_id']} isolated in quarantine!")
        elif decision == "REJECT":
            print(f"❌ SECURITY AUDIT: Telemetry packet from device {log_entry['device_id']} discarded completely!")
        elif decision == "FLAG":
            print(f"⚠️  SECURITY AUDIT: Telemetry packet from device {log_entry['device_id']} flagged as suspicious!")

# Global instance of ZeroTrustValidator
zero_trust_validator = ZeroTrustValidator()
