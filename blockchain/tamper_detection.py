"""
Tamper Detection System for Healthcare IoT
Monitors data changes and alerts on anomalies/tampering
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any


class TamperDetector:
    """Detects data tampering and records anomalies"""
    
    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.logs: List[Dict[str, Any]] = []
        self.anomaly_thresholds = {
            "hr": (40, 180),      # Heart Rate: 40-180 bpm
            "bp_sys": (70, 180),  # BP Systolic: 70-180
            "bp_dia": (40, 120),  # BP Diastolic: 40-120
            "temp": (34, 42)      # Temperature: 34-42°C
        }
    
    def hash_record(self, record: Dict[str, Any]) -> str:
        """Generate hash of a patient record"""
        record_str = json.dumps(record, sort_keys=True)
        return hashlib.sha256(record_str.encode()).hexdigest()
    
    def check_anomaly(self, patient_id: str, health_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if health data contains anomalies"""
        anomalies = []
        
        hr = health_data.get("hr", 0)
        bp = health_data.get("bp", "0/0")
        temp = health_data.get("temp", 0)
        
        # Parse BP
        try:
            sys, dia = map(int, str(bp).split("/"))
        except:
            sys, dia = 0, 0
        
        # Check HR
        if not (self.anomaly_thresholds["hr"][0] <= hr <= self.anomaly_thresholds["hr"][1]):
            anomalies.append({
                "type": "hr_anomaly",
                "value": hr,
                "range": self.anomaly_thresholds["hr"],
                "severity": "HIGH" if hr > 160 or hr < 50 else "MEDIUM"
            })
        
        # Check BP Systolic
        if not (self.anomaly_thresholds["bp_sys"][0] <= sys <= self.anomaly_thresholds["bp_sys"][1]):
            anomalies.append({
                "type": "bp_sys_anomaly",
                "value": sys,
                "range": self.anomaly_thresholds["bp_sys"],
                "severity": "HIGH"
            })
        
        # Check BP Diastolic
        if not (self.anomaly_thresholds["bp_dia"][0] <= dia <= self.anomaly_thresholds["bp_dia"][1]):
            anomalies.append({
                "type": "bp_dia_anomaly",
                "value": dia,
                "range": self.anomaly_thresholds["bp_dia"],
                "severity": "HIGH"
            })
        
        # Check Temperature
        if not (self.anomaly_thresholds["temp"][0] <= temp <= self.anomaly_thresholds["temp"][1]):
            anomalies.append({
                "type": "temp_anomaly",
                "value": temp,
                "range": self.anomaly_thresholds["temp"],
                "severity": "CRITICAL" if temp > 40 or temp < 34.5 else "HIGH"
            })
        
        return {
            "has_anomaly": len(anomalies) > 0,
            "anomalies": anomalies,
            "patient_id": patient_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def detect_tamper(self, patient_id: str, previous_data: Dict[str, Any], 
                      current_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Alias for detect_tampering with flipped parameters to match the call in app.py
        """
        return self.detect_tampering(patient_id, current_data, previous_data)

    def detect_tampering(self, patient_id: str, current_data: Dict[str, Any], 
                        previous_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect data tampering by comparing current with previous
        """
        current_hash = self.hash_record(current_data)
        previous_hash = self.hash_record(previous_data)
        
        tampering_details = {
            "patient_id": patient_id,
            "is_tampered": current_hash != previous_hash,
            "timestamp": datetime.utcnow().isoformat(),
            "changes": {},
            "severity": "NONE"
        }
        
        if current_hash != previous_hash:
            # Find what changed
            for key in current_data:
                if key not in previous_data or current_data[key] != previous_data[key]:
                    tampering_details["changes"][key] = {
                        "old": previous_data.get(key),
                        "new": current_data[key]
                    }
            
            tampering_details["severity"] = "CRITICAL"
            self._log_tampering(tampering_details)
        
        return tampering_details
    
    def _log_tampering(self, tampering_details: Dict[str, Any]):
        """Log tampering incident"""
        self.logs.append(tampering_details)
    
    def record_snapshot(self, patient_id: str, data: Dict[str, Any]):
        """Record data snapshot for comparison"""
        self.history.append({
            "patient_id": patient_id,
            "data": data,
            "hash": self.hash_record(data),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def get_tampering_logs(self) -> List[Dict[str, Any]]:
        """Get all tampering logs"""
        return self.logs
    
    def get_patient_tampering_history(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get tampering history for specific patient"""
        return [log for log in self.logs if log["patient_id"] == patient_id]
    
    def export_report(self, patient_id: str) -> Dict[str, Any]:
        """Generate tamper detection report for patient"""
        patient_logs = self.get_patient_tampering_history(patient_id)
        
        return {
            "patient_id": patient_id,
            "total_tampering_incidents": len(patient_logs),
            "incidents": patient_logs,
            "report_generated": datetime.utcnow().isoformat()
        }
