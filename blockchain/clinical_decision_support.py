"""
Clinical Decision Support and Digital Twin Engine
Implements physiological twins, predictive forecasting, septic behavior checking,
knowledge graphs, forensic replay buffering, and clinician feedback/overrides.
"""

import math
import os
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Simple helper to calculate linear regression slope
def calculate_slope(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    n = len(values)
    x = list(range(n))
    y = values
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    num = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
    den = sum((x[i] - x_mean) ** 2 for i in range(n))
    if den == 0:
        return 0.0
    return num / den

class DigitalPatientTwin:
    """Continously updating virtual physiological representation of the patient"""
    
    def __init__(self, patient_id: str, baseline_hr: float = 75.0, 
                 baseline_temp: float = 37.0, baseline_bp_sys: float = 120.0,
                 baseline_bp_dia: float = 80.0):
        self.patient_id = patient_id
        self.baseline_hr = baseline_hr
        self.baseline_temp = baseline_temp
        self.baseline_bp_sys = baseline_bp_sys
        self.baseline_bp_dia = baseline_bp_dia
        self.recovery_speed = 0.15  # speed of returning to baseline (damping factor)
        
    def calculate_deterioration_index(self, hr: float, temp: float, bp_sys: float, bp_dia: float) -> float:
        """Compute virtual deterioration index (0-100%) based on clinical deviations"""
        score = 0.0
        
        # Heart Rate deviations
        if hr > 100:
            score += min(35.0, (hr - 100) * 1.5)
        elif hr < 60:
            score += min(35.0, (60 - hr) * 1.5)
            
        # Temp deviations
        if temp > 37.5:
            score += min(35.0, (temp - 37.5) * 15.0)
        elif temp < 36.0:
            score += min(35.0, (36.0 - temp) * 15.0)
            
        # BP deviations (Systolic)
        if bp_sys > 130:
            score += min(30.0, (bp_sys - 130) * 1.0)
        elif bp_sys < 90:
            score += min(30.0, (90 - bp_sys) * 1.5)
            
        return min(100.0, max(0.0, score))
        
    def generate_projections(self, history: List[Dict[str, Any]], steps: int = 10, is_septic: bool = False) -> Dict[str, List[float]]:
        """Project future vital signs over a lookahead window (10 steps)"""
        # Get latest measurements as starting point
        if not history:
            current_hr = self.baseline_hr
            current_temp = self.baseline_temp
            current_bp_sys = self.baseline_bp_sys
            current_bp_dia = self.baseline_bp_dia
            hr_slope = 0.0
            temp_slope = 0.0
            bp_sys_slope = 0.0
            bp_dia_slope = 0.0
        else:
            latest = history[-1]
            current_hr = latest.get("hr", self.baseline_hr)
            current_temp = latest.get("temp", self.baseline_temp)
            bp_str = latest.get("bp", f"{self.baseline_bp_sys}/{self.baseline_bp_dia}")
            try:
                current_bp_sys, current_bp_dia = map(float, bp_str.split("/"))
            except Exception:
                current_bp_sys, current_bp_dia = self.baseline_bp_sys, self.baseline_bp_dia
                
            # Extract slopes from recent history (last 5 points)
            recent = history[-5:]
            hrs = [r.get("hr", self.baseline_hr) for r in recent]
            temps = [r.get("temp", self.baseline_temp) for r in recent]
            bp_sys_list = []
            bp_dia_list = []
            for r in recent:
                try:
                    s, d = map(float, r.get("bp", "120/80").split("/"))
                    bp_sys_list.append(s)
                    bp_dia_list.append(d)
                except Exception:
                    bp_sys_list.append(self.baseline_bp_sys)
                    bp_dia_list.append(self.baseline_bp_dia)
                    
            hr_slope = calculate_slope(hrs)
            temp_slope = calculate_slope(temps)
            bp_sys_slope = calculate_slope(bp_sys_list)
            bp_dia_slope = calculate_slope(bp_dia_list)
            
        projected_hrs = []
        projected_temps = []
        projected_bp_sys = []
        projected_bp_dia = []
        projected_deterioration = []
        
        for i in range(1, steps + 1):
            if is_septic:
                # Septic projection pathway: HR rises, Temp rises, BP drops
                # Target levels for sepsis simulation
                target_hr = 130.0
                target_temp = 39.5
                target_bp_sys = 80.0
                target_bp_dia = 50.0
                
                # Asymptotic approach to septic targets
                factor = 1.0 - (0.75 ** i)
                proj_hr = current_hr + (target_hr - current_hr) * factor
                proj_temp = current_temp + (target_temp - current_temp) * factor
                proj_sys = current_bp_sys + (target_bp_sys - current_bp_sys) * factor
                proj_dia = current_bp_dia + (target_bp_dia - current_bp_dia) * factor
            else:
                # Standard autoregressive projection + diurnal wave
                # Damp slopes exponentially back toward baselines
                damping = 0.8 ** i
                proj_hr = current_hr + (hr_slope * i * damping)
                proj_temp = current_temp + (temp_slope * i * damping)
                proj_sys = current_bp_sys + (bp_sys_slope * i * damping)
                proj_dia = current_bp_dia + (bp_dia_slope * i * damping)
                
                # Add diurnal wave oscillation (e.g. ±5 bpm, ±0.3°C, ±4 mmHg)
                wave_factor = math.sin(i * (2 * math.pi / 24))
                proj_hr += 4.0 * wave_factor
                proj_temp += 0.25 * wave_factor
                proj_sys += 5.0 * wave_factor
                proj_dia += 3.0 * wave_factor
                
            # Apply safety bounds
            proj_hr = max(40.0, min(200.0, proj_hr))
            proj_temp = max(34.0, min(43.0, proj_temp))
            proj_sys = max(60.0, min(220.0, proj_sys))
            proj_dia = max(35.0, min(140.0, proj_dia))
            
            projected_hrs.append(round(proj_hr, 1))
            projected_temps.append(round(proj_temp, 2))
            projected_bp_sys.append(round(proj_sys, 1))
            projected_bp_dia.append(round(proj_dia, 1))
            
            det_idx = self.calculate_deterioration_index(proj_hr, proj_temp, proj_sys, proj_dia)
            projected_deterioration.append(round(det_idx, 1))
            
        return {
            "hr": projected_hrs,
            "temp": projected_temps,
            "bp_sys": projected_bp_sys,
            "bp_dia": projected_bp_dia,
            "deterioration_index": projected_deterioration
        }

class SepticBehaviorChecker:
    """Evaluates multi-parametric physiological trends to alert on septic shock risks"""
    
    def check_septic_behavior(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        if len(history) < 3:
            return {
                "alert_triggered": False,
                "septic_risk_score": 0.0,
                "severity": "NORMAL",
                "recommendations": ["Insufficient data points to assess trends (minimum 3 records required)."]
            }
            
        recent = history[-5:]
        hrs = [r.get("hr", 75.0) for r in recent]
        temps = [r.get("temp", 37.0) for r in recent]
        bp_sys = []
        for r in recent:
            try:
                s, _ = map(float, r.get("bp", "120/80").split("/"))
                bp_sys.append(s)
            except Exception:
                bp_sys.append(120.0)
                
        # Calculate slopes
        hr_slope = calculate_slope(hrs)
        temp_slope = calculate_slope(temps)
        bp_sys_slope = calculate_slope(bp_sys)
        
        # Septic Criteria check: rising HR, rising Temp, falling BP
        hr_rising = hr_slope > 1.0        # rising at > 1 bpm per reading
        temp_rising = temp_slope > 0.05   # rising at > 0.05°C per reading
        bp_falling = bp_sys_slope < -0.5   # falling at > 0.5 mmHg per reading
        
        septic_risk_score = 0.0
        indicators = []
        
        if hr_slope > 0.0:
            septic_risk_score += min(30.0, hr_slope * 15.0)
            if hr_rising:
                indicators.append("Rapidly rising heart rate (Tachycardia trend)")
        if temp_slope > 0.0:
            septic_risk_score += min(35.0, temp_slope * 250.0)
            if temp_rising:
                indicators.append("Rising body temperature (Fever escalation trend)")
        if bp_sys_slope < 0.0:
            septic_risk_score += min(35.0, abs(bp_sys_slope) * 35.0)
            if bp_falling:
                indicators.append("Falling blood pressure (Hypotension risk)")
                
        septic_risk_score = round(min(100.0, max(0.0, septic_risk_score)), 1)
        alert_triggered = hr_rising and temp_rising and bp_falling and (septic_risk_score >= 50.0)
        
        recommendations = []
        if alert_triggered:
            severity = "CRITICAL"
            recommendations = [
                "🚨 Possible early-stage septic behavior detected.",
                "Draw blood cultures immediately and order lactate levels.",
                "Administer broad-spectrum IV antibiotics within 1 hour.",
                "Initiate aggressive fluid resuscitation (30ml/kg crystalloid).",
                "Ensure continuous ECG, pulse oximetry, and arterial pressure monitoring."
            ]
        elif septic_risk_score > 30.0:
            severity = "WARNING"
            recommendations = [
                "⚠️ Elevated septic risk indices detected. Clinical observation advised.",
                "Monitor vital signs every 15 minutes.",
                "Verify device placement and calibrate sensors to rule out artifact noise."
            ]
        else:
            severity = "NORMAL"
            recommendations = [
                "Physiological trends reside within normal variance parameters."
            ]
            
        return {
            "alert_triggered": alert_triggered,
            "septic_risk_score": septic_risk_score,
            "severity": severity,
            "recommendations": recommendations,
            "indicators": indicators,
            "slopes": {
                "hr_slope": round(hr_slope, 3),
                "temp_slope": round(temp_slope, 4),
                "bp_sys_slope": round(bp_sys_slope, 3)
            }
        }

class HealthcareKnowledgeGraph:
    """Builds interconnected explainable relations between patient, devices, alerts, and blocks"""
    
    def generate_graph(self, patient_id: str, patient_info: Dict[str, Any], 
                       block_history: List[Dict[str, Any]], alerts: List[Dict[str, Any]], 
                       device_registry: Dict[str, Any]) -> Dict[str, Any]:
        nodes = []
        links = []
        
        # 1. Patient Node
        nodes.append({
            "id": f"patient_{patient_id}",
            "label": f"Patient: {patient_info.get('name', patient_id)}",
            "type": "patient",
            "metadata": {
                "id": patient_id,
                "condition": patient_info.get("condition", "Normal"),
                "age": patient_info.get("age", "N/A")
            }
        })
        
        # Find active device for this patient
        active_device_id = None
        for dev_id, dev_info in device_registry.items():
            if dev_info.get("assigned_patient") == patient_id:
                active_device_id = dev_id
                nodes.append({
                    "id": f"device_{dev_id}",
                    "label": f"IoMT Device: {dev_id}",
                    "type": "device",
                    "metadata": {
                        "device_id": dev_id,
                        "manufacturer": dev_info.get("manufacturer", "Unknown"),
                        "status": "Isolated" if dev_info.get("isolated", False) else "Active",
                        "trust_score": dev_info.get("trust_score", 100)
                    }
                })
                links.append({
                    "source": f"patient_{patient_id}",
                    "target": f"device_{dev_id}",
                    "relationship": "monitored_by"
                })
                
        # 2. Blockchain Blocks Nodes & Previous Links
        # Include last 5 blocks to avoid over-complicating the graph
        recent_blocks = block_history[-5:]
        for block in recent_blocks:
            idx = block.get("index", 0)
            nodes.append({
                "id": f"block_{patient_id}_{idx}",
                "label": f"Block #{idx}",
                "type": "blockchain_block",
                "metadata": {
                    "index": idx,
                    "validation": block.get("validation_status", "ACCEPT"),
                    "trust": block.get("trust_score", 100.0),
                    "label": block.get("label", "NORMAL"),
                    "hash": block.get("hash", "")[:8]
                }
            })
            
            # Link patient to their blocks
            links.append({
                "source": f"patient_{patient_id}",
                "target": f"block_{patient_id}_{idx}",
                "relationship": "has_record"
            })
            
            # Cryptographic links between blocks
            if idx > 0:
                prev_idx = idx - 1
                links.append({
                    "source": f"block_{patient_id}_{idx}",
                    "target": f"block_{patient_id}_{prev_idx}",
                    "relationship": "cryptographic_parent"
                })
                
        # 3. Clinical/Security Alert Nodes
        for idx, alert in enumerate(alerts[-5:]):  # last 5 alerts
            alert_id = f"alert_{patient_id}_{idx}_{int(datetime.utcnow().timestamp())}"
            nodes.append({
                "id": alert_id,
                "label": alert.get("message", "Alert"),
                "type": "alert",
                "metadata": {
                    "category": alert.get("category", "General"),
                    "severity": alert.get("severity", "MEDIUM"),
                    "timestamp": alert.get("timestamp", "")
                }
            })
            
            # Connect patient to alert
            links.append({
                "source": f"patient_{patient_id}",
                "target": alert_id,
                "relationship": "triggered_alert"
            })
            
            # Connect device to alert if security-related
            if active_device_id and alert.get("category") in ["Security", "CYBERSECURITY"]:
                links.append({
                    "source": f"device_{active_device_id}",
                    "target": alert_id,
                    "relationship": "source_of_threat"
                })
                
        return {"nodes": nodes, "links": links}

class ForensicReplayManager:
    """Manages circular buffering (limit 50 logs) for step-by-step forensic audits"""
    
    def __init__(self, limit: int = 50):
        self.limit = limit
        self.buffers: Dict[str, List[Dict[str, Any]]] = {}
        
    def add_record(self, patient_id: str, record: Dict[str, Any]):
        if patient_id not in self.buffers:
            self.buffers[patient_id] = []
            
        record_copy = dict(record)
        record_copy["replay_timestamp"] = datetime.utcnow().isoformat()
        
        self.buffers[patient_id].append(record_copy)
        
        # Maintain sliding window buffer size constraints
        if len(self.buffers[patient_id]) > self.limit:
            self.buffers[patient_id].pop(0)
            
    def get_replay(self, patient_id: str) -> List[Dict[str, Any]]:
        return self.buffers.get(patient_id, [])

class ClinicianFeedbackManager:
    """Manages clinician validation overrides and notes"""
    
    def __init__(self, filepath: str = "data/processed/clinician_overrides.json"):
        self.filepath = filepath
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        self.overrides = self._load()
        
    def _load(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    return json.load(f)
            except Exception:
                return []
        return []
        
    def _save(self):
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.overrides, f, indent=4)
        except Exception as e:
            print(f"Error saving clinician overrides: {e}")
            
    def record_override(self, clinician_id: str, patient_id: str, record_index: int, 
                        original_decision: str, overridden_decision: str, notes: str) -> Dict[str, Any]:
        entry = {
            "override_id": len(self.overrides) + 1,
            "timestamp": datetime.utcnow().isoformat(),
            "clinician_id": clinician_id,
            "patient_id": patient_id,
            "record_index": record_index,
            "original_decision": original_decision,
            "overridden_decision": overridden_decision,
            "notes": notes
        }
        self.overrides.append(entry)
        self._save()
        return entry
        
    def get_overrides(self, patient_id: str = None) -> List[Dict[str, Any]]:
        if patient_id:
            return [o for o in self.overrides if o["patient_id"] == patient_id]
        return self.overrides

class AnonymizedResearchExporter:
    """Exports patient data logs stripped of direct identifier tokens for research studies"""
    
    def export_data(self, patient_id: str, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        anonymized_history = []
        # Generate stable mock researcher ID for the session/patient
        anonymized_id = f"SUBJ_{hashlib.sha256(patient_id.encode()).hexdigest()[:8].upper()}"
        
        for record in history:
            anon_rec = {
                "subject_id": anonymized_id,
                "timestamp": record.get("timestamp"),
                "hr": record.get("hr"),
                "bp": record.get("bp"),
                "temp": record.get("temp"),
                "trust_score": record.get("trust_score"),
                "label": record.get("label"),
                "validation_status": record.get("validation_status")
            }
            anonymized_history.append(anon_rec)
        return anonymized_history
