"""
IoMT + Blockchain Healthcare Monitoring System
Flask Backend - Port 5001
Standardized Architecture v2.0
"""

from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
import json
import hashlib
import threading
import time
import collections
import logging
import sys
from datetime import datetime
import paho.mqtt.client as mqtt
from typing import Tuple, Dict, Any, List

# Structured JSON Logger Configuration (Step 13)
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "filename": record.filename,
            "line": record.lineno
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

# Configure root logger to output structured JSON
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_handler = logging.StreamHandler(sys.stdout)
root_handler.setFormatter(JSONFormatter())
root_logger.handlers = [root_handler]

# Global request tracker counter (Step 12)
REQUEST_COUNTS = collections.defaultdict(int)

# Import custom modules
from blockchain.blockchain import BlockchainManager
from blockchain.tamper_detection import TamperDetector
from blockchain.data_generator import patient_generator
from blockchain.zero_trust import zero_trust_validator
from blockchain.ai_anomaly_detector import ai_threat_detector
from blockchain.cloud_gateway import cloud_security_gateway

# Layer 7 clinical decision support integrations
from blockchain.clinical_decision_support import (
    DigitalPatientTwin, SepticBehaviorChecker, HealthcareKnowledgeGraph,
    ForensicReplayManager, ClinicianFeedbackManager, AnonymizedResearchExporter
)

septic_checker = SepticBehaviorChecker()
knowledge_graph_generator = HealthcareKnowledgeGraph()
replay_manager = ForensicReplayManager()
feedback_manager = ClinicianFeedbackManager()
research_exporter = AnonymizedResearchExporter()
# Maintain registry of patient twins dynamically
patient_twins = {}

# Layer 8 federated intelligence network integrations
from blockchain.federated_network import federated_network


# ============================================
# FLASK CONFIGURATION
# ============================================

app = Flask(__name__, template_folder='templates', static_folder='static')

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.after_request
def after_request(response):
    """Add CORS headers to every response"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.before_request
def handle_preflight():
    """Handle OPTIONS requests"""
    if request.method == 'OPTIONS':
        return '', 200

@app.before_request
def track_requests():
    """Track request metrics in a thread-safe dict"""
    if request.path != "/metrics":
        method = request.method
        endpoint = request.path
        # Normalize route variables to keep labels clean
        # e.g., /api/cloud/patient/PS1000 -> /api/cloud/patient/<pid>
        if "/api/cloud/patient/" in endpoint:
            endpoint = "/api/cloud/patient/<pid>"
        elif "/patient/" in endpoint:
            endpoint = "/patient/<pid>"
        REQUEST_COUNTS[(method, endpoint)] += 1

# ============================================
# INITIALIZATION & DATA MANAGEMENT
# ============================================

FILE = "patient_data.json"
blockchain_manager = BlockchainManager()
tamper_detector = TamperDetector()
previous_snapshots = {}

def read_data():
    """Read patient data from JSON file"""
    try:
        with open(FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception as e:
        print(f"⚠️  Error reading data: {e}")
        return []

def write_data(data):
    """Write patient data to JSON file"""
    try:
        with open(FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"⚠️  Error writing data: {e}")

# Initialize patients on startup
try:
    existing_patients = read_data()
    if not existing_patients or len(existing_patients) == 0:
        print("📊 Generating initial patient dataset...")
        existing_patients = patient_generator.create_patient_dataset(20)
        write_data(existing_patients)
        print(f"✅ Created {len(existing_patients)} patients")
    else:
        print(f"✅ Loaded {len(existing_patients)} existing patients")
        # Load loaded patients into the generator's memory cache for restarts
        for p in existing_patients:
            patient_generator.patients[p["id"]] = p
            patient_generator.health_history[p["id"]] = [{
                "hr": p.get("hr", 72),
                "bp": p.get("bp", "120/80"),
                "temp": p.get("temp", 37.0),
                "timestamp": p.get("time") or datetime.utcnow().isoformat()
            }]
except Exception as e:
    print(f"❌ Initialization error: {e}")
    existing_patients = patient_generator.create_patient_dataset(20)
    write_data(existing_patients)

# Initialize blockchains for all patients
for patient in existing_patients:
    patient_id = patient.get("id")
    if patient_id:
        blockchain_manager.create_patient_blockchain(patient_id)
        previous_snapshots[patient_id] = {
            "hr": patient.get("hr", 0),
            "bp": patient.get("bp", "0/0"),
            "temp": patient.get("temp", 0)
        }
        # Seed replay buffer with initial accepted telemetry
        replay_manager.add_record(patient_id, {
            "timestamp": patient.get("time") or datetime.utcnow().isoformat(),
            "hr": patient.get("hr", 72),
            "bp": patient.get("bp", "120/80"),
            "temp": patient.get("temp", 37.0),
            "trust_score": 100.0,
            "validation_status": "ACCEPT",
            "label": "NORMAL"
        })

# ============================================
# MQTT CONFIGURATION
# ============================================

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "iot/hospital/patients"
mqtt_connected = False
import random
mqtt_client = mqtt.Client(client_id=f"flask_iomt_server_{random.randint(100000, 999999)}")

def on_mqtt_connect(client, userdata, flags, rc):
    """Callback for MQTT connection"""
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        print(f"✅ MQTT Connected: {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
    else:
        mqtt_connected = False
        print(f"⚠️  MQTT Connection error: {rc}")

def on_mqtt_message(client, userdata, msg):
    """Handle incoming MQTT messages - Secured by Zero Trust Edge Engine"""
    try:
        payload = json.loads(msg.payload.decode())
        patient_id = payload.get("id") or payload.get("patient_id")
        
        if patient_id:
            # Check transport details for encryption validation (Step 5)
            meta = payload.get("communication_metadata", {})
            is_tls = meta.get("encryption", "TLSv1.3") != "None" and meta.get("network_port", 8883) == 8883
            
            # Step 1-10: Ingest and Validate
            decision, score, reasons = zero_trust_validator.validate_packet(
                payload, topic=msg.topic, is_tls=is_tls
            )
            
            if decision in ["ACCEPT", "FLAG"]:
                # Layer 3 - AI Anomaly Detection & Threat Analysis
                ai_decision, ai_score, classification, alerts = ai_threat_detector.analyze_packet(
                    payload, dev_trust_score=score
                )
                
                if ai_decision in ["ACCEPT", "FLAG"]:
                    patients = read_data()
                    updated = False
                    
                    for patient in patients:
                        if patient["id"] == patient_id:
                            patient["hr"] = payload.get("hr", patient.get("hr"))
                            patient["bp"] = payload.get("bp", patient.get("bp"))
                            patient["temp"] = payload.get("temp", patient.get("temp"))
                            patient["lastUpdate"] = payload.get("timestamp") or datetime.utcnow().isoformat()
                            patient["condition"] = payload.get("condition", patient.get("condition", "Normal"))
                            patient["label"] = classification
                            patient["trust_score"] = ai_score
                            patient["validation_status"] = ai_decision
                            
                            # Step 13: Forward Verified Healthcare Streams to Blockchain Ledger
                            # Freeze blockchain insertions during active tamper events (Step 7)
                            tamper_info = blockchain_manager.verify_patient_integrity(patient_id)
                            if not tamper_info.get("is_tampered", False):
                                blockchain_manager.record_health_data(patient_id, {
                                    "hr": patient["hr"],
                                    "bp": patient["bp"],
                                    "temp": patient["temp"],
                                    "trust_score": ai_score,
                                    "validation_status": ai_decision,
                                    "label": classification
                                })
                            else:
                                print(f"🔒 BLOCKCHAIN FROZEN: Active tamper event detected on patient {patient_id}. Insertions blocked.")
                            
                            # Layer 7 Forensic Replay buffering
                            replay_record = {
                                "timestamp": patient["lastUpdate"],
                                "hr": patient["hr"],
                                "bp": patient["bp"],
                                "temp": patient["temp"],
                                "trust_score": ai_score,
                                "validation_status": ai_decision,
                                "label": classification
                            }
                            replay_manager.add_record(patient_id, replay_record)
                            
                            updated = True
                            break
                    
                    if updated:
                        write_data(patients)
                        print(f"📡 MQTT: Ingested {ai_decision} packet for {patient_id} (Score: {ai_score}%, Threat: {classification})")
                else:
                    print(f"🛡️  MQTT AI Threat Engine BLOCKED: {ai_decision} packet for {patient_id}. Classification: {classification}. Alerts: {alerts}")
            else:
                print(f"🛡️  MQTT Zero Trust BLOCKED: Discarded {decision} packet for {patient_id}. Reasons: {reasons}")
    except Exception as e:
        print(f"⚠️  MQTT message error: {e}")

mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message

def connect_mqtt():
    """Connect to MQTT broker"""
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
        print("🔄 MQTT connecting...")
    except Exception as e:
        print(f"⚠️  MQTT connection failed: {e}")

connect_mqtt()

# ============================================
# BACKGROUND THREAD - AUTO UPDATE VITALS
# ============================================

def auto_update_vitals():
    """Background thread: automatically update patient vitals every 5 seconds (Secured by Zero Trust Validation)"""
    while True:
        try:
            time.sleep(5)
            patients = read_data()
            
            if not patients:
                continue
            
            updated = False
            
            for patient in patients:
                patient_id = patient.get("id")
                if not patient_id:
                    continue
                
                # Generate realistic, behavior-aware, and attack-aware vital variations
                telemetry = patient_generator.update_patient_vitals(patient_id)
                
                # Run Zero Trust Gatekeeper Validation (Layer 2)
                # Background updates are simulated as internal secure channels (TLS active, correct topic)
                decision, score, reasons = zero_trust_validator.validate_packet(
                    telemetry, topic="iot/hospital/patients", is_tls=True
                )
                
                if decision in ["ACCEPT", "FLAG"]:
                    # Layer 3 - AI Anomaly Detection & Threat Analysis
                    ai_decision, ai_score, classification, alerts = ai_threat_detector.analyze_packet(
                        telemetry, dev_trust_score=score
                    )
                    
                    if ai_decision in ["ACCEPT", "FLAG"]:
                        patient["hr"] = telemetry.get("hr", 72)
                        patient["bp"] = telemetry.get("bp", "120/80")
                        patient["temp"] = telemetry.get("temp", 37.0)
                        patient["lastUpdate"] = telemetry.get("timestamp", datetime.utcnow().isoformat())
                        patient["condition"] = telemetry.get("condition", patient.get("condition", "Normal"))
                        patient["label"] = classification
                        patient["trust_score"] = ai_score
                        patient["validation_status"] = ai_decision
                        
                        # Record on blockchain (immutable audit trail)
                        # Freeze blockchain insertions during active tamper events (Step 7)
                        try:
                            tamper_info = blockchain_manager.verify_patient_integrity(patient_id)
                            if not tamper_info.get("is_tampered", False):
                                blockchain_manager.add_record(
                                    patient_id,
                                    {
                                        "hr": patient["hr"],
                                        "bp": patient["bp"],
                                        "temp": patient["temp"],
                                        "timestamp": patient["lastUpdate"],
                                        "trust_score": ai_score,
                                        "validation_status": ai_decision,
                                        "label": classification
                                    }
                                )
                            else:
                                print(f"🔒 BLOCKCHAIN FROZEN: Active tamper event detected on patient {patient_id}. Insertions blocked.")
                        except Exception as e:
                            print(f"⚠️  Blockchain record error for {patient_id}: {e}")
                            
                        # Layer 7 Forensic Replay buffering
                        replay_record = {
                            "timestamp": patient["lastUpdate"],
                            "hr": patient["hr"],
                            "bp": patient["bp"],
                            "temp": patient["temp"],
                            "trust_score": ai_score,
                            "validation_status": ai_decision,
                            "label": classification
                        }
                        replay_manager.add_record(patient_id, replay_record)
                        
                        # Check for tamper/anomalies (historical threshold check)
                        current_data = {
                            "hr": patient["hr"],
                            "bp": patient["bp"],
                            "temp": patient["temp"]
                        }
                        
                        if previous_snapshots.get(patient_id):
                            prev_data = previous_snapshots[patient_id]
                            tamper_alert = tamper_detector.detect_tamper(
                                patient_id, prev_data, current_data
                            )
                            
                            if tamper_alert["is_tampered"]:
                                print(f"🚨 TAMPER ALERT for {patient_id}: {tamper_alert.get('reason') or tamper_alert.get('changes')}")
                        
                        previous_snapshots[patient_id] = current_data
                        updated = True
                    else:
                        print(f"🛡️  AI Threat Engine Blocked {ai_decision} vital update for patient {patient_id}. Classification: {classification}. Alerts: {alerts}")
                else:
                    # Packet quarantined or rejected! Database updates are blocked to prevent pollution
                    print(f"🛡️  Zero Trust Blocked {decision} vital update for patient {patient_id}. Reasons: {reasons}")
            
            if updated:
                write_data(patients)
                print(f"✅ Vitals updated for {len(patients)} patients")
        
        except Exception as e:
            print(f"⚠️  Vitals update error: {e}")
            time.sleep(5)

# Start background thread
vital_thread = threading.Thread(target=auto_update_vitals, daemon=True)
vital_thread.start()
print("🔄 Vitals update thread started")

# ============================================
# FRONTEND ROUTES
# ============================================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/patient/<pid>")
def patient_page(pid):
    return render_template("patient.html")

# ============================================
# API ROUTES - PATIENT DATA
# ============================================

@app.route("/api/patients")
def get_patients():
    """Get all patients with stats"""
    patients = read_data()
    stats = patient_generator.get_statistics()
    
    # Inject real-time blockchain integrity status dynamically
    for patient in patients:
        pid = patient.get("id")
        if pid:
            tamper_info = blockchain_manager.verify_patient_integrity(pid)
            patient["tampered"] = tamper_info.get("is_tampered", False)
            
    return jsonify({
        "patients": patients,
        "statistics": stats
    })

@app.route("/api/patient/<pid>")
def get_patient(pid):
    """Get single patient with full history and blockchain"""
    patients = read_data()
    for p in patients:
        if p["id"] == pid:
            blockchain_data = blockchain_manager.get_patient_chain(pid)
            tampering_info = blockchain_manager.verify_patient_integrity(pid)
            p["tampered"] = tampering_info.get("is_tampered", False)
            
            return jsonify({
                "patient": p,
                "blockchain": blockchain_data,
                "tampering": tampering_info,
                "history": tamper_detector.get_patient_tampering_history(pid)
            })
    return jsonify({"error": "not found"}), 404

@app.route("/api/update_patient", methods=["POST"])
@app.route("/update_patient", methods=["POST"])
def update_patient():
    data = request.json
    patients = read_data()
    
    for p in patients:
        if p["id"] == data["id"]:
            if "history" not in p:
                p["history"] = []
            
            old_data = {
                "hr": p.get("hr"),
                "bp": p.get("bp"),
                "temp": p.get("temp")
            }
            
            p["hr"] = data.get("hr", p.get("hr"))
            p["bp"] = data.get("bp", p.get("bp"))
            p["temp"] = data.get("temp", p.get("temp"))
            p["lastUpdated"] = datetime.utcnow().isoformat()
            
            p["history"].append({
                **old_data,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            tampering_result = tamper_detector.detect_tampering(
                p["id"],
                {"hr": p.get("hr"), "bp": p.get("bp"), "temp": p.get("temp")},
                old_data
            )
            
            blockchain_manager.record_health_data(p["id"], {
                "hr": p.get("hr"),
                "bp": p.get("bp"),
                "temp": p.get("temp")
            })
            
            write_data(patients)
            
            return jsonify({
                "success": True,
                "patient": p,
                "tampering_detected": tampering_result,
                "blockchain_valid": blockchain_manager.blockchains[p["id"]].verify_integrity()
            })
    
    return jsonify({"error": "Patient not found"}), 404

@app.route("/api/add_patient", methods=["POST"])
def add_patient():
    """Add new patient"""
    data = request.json
    patients = read_data()
    
    new_patient = {
        **data,
        "id": data.get("id", f"PS{len(patients) + 1000}"),
        "admissionDate": datetime.utcnow().isoformat(),
        "history": []
    }
    
    blockchain_manager.create_patient_blockchain(new_patient["id"])
    previous_snapshots[new_patient["id"]] = {
        "hr": new_patient.get("hr", 0),
        "bp": new_patient.get("bp", "0/0"),
        "temp": new_patient.get("temp", 0)
    }
    
    patients.append(new_patient)
    write_data(patients)
    
    return jsonify({"success": True, "patient": new_patient})

# ============================================
# BLOCKCHAIN & SECURITY ROUTES
# ============================================

@app.route("/api/blockchain/verify")
def verify_all_blockchains():
    """Verify all patient blockchains"""
    results = blockchain_manager.verify_all_patients()
    return jsonify(results)

@app.route("/api/blockchain/patient/<pid>")
def get_patient_blockchain(pid):
    """Get specific patient blockchain"""
    chain = blockchain_manager.get_patient_chain(pid)
    tampering = blockchain_manager.verify_patient_integrity(pid)
    
    return jsonify({
        "chain": chain,
        "tampering": tampering
    })

def publish_mqtt_alert(topic, message_dict):
    """Publish alert message to MQTT broker if connected"""
    global mqtt_connected
    if mqtt_connected:
        try:
            mqtt_client.publish(topic, json.dumps(message_dict))
            print(f"📡 MQTT Alert Published on {topic}: {message_dict}")
        except Exception as e:
            print(f"⚠️  Failed to publish MQTT alert: {e}")

@app.route("/api/blockchain/tamper", methods=["POST"])
def tamper_blockchain():
    """Simulates zero-trust defensive blocking of database tampering attempts"""
    data = request.json or {}
    patient_id = data.get("patient_id", "Unknown")
    
    alert_payload = {
        "patient_id": patient_id,
        "alert_type": "BLOCKCHAIN_TAMPER_ATTEMPT_BLOCKED",
        "timestamp": datetime.utcnow().isoformat(),
        "details": {
            "error": "Blockchain is immutable and protected. Tampering attempt BLOCKED by Zero-Trust self-defending engine!",
            "attacker_ip": request.remote_addr or "127.0.0.1",
            "action": "BLOCKED"
        }
    }
    
    # Log the blocked tampering attempt
    tamper_detector._log_tampering(alert_payload)
    publish_mqtt_alert("iot/hospital/alerts", alert_payload)
    
    print(f"🛡️ [SELF-DEFENSE SYSTEM] Blocked blockchain tampering attempt for patient {patient_id}!")
    
    return jsonify({
        "success": False,
        "error": "Blockchain is protected under Layer 9 Autonomous Governance. Tampering attempt BLOCKED by Zero-Trust self-defending engine!"
    })

@app.route("/api/tamper/history")
def get_tampering_logs():
    """Get all tampering logs"""
    return jsonify({
        "logs": tamper_detector.get_tampering_logs()
    })

@app.route("/api/tamper/patient/<pid>")
def get_patient_tamper_history(pid):
    """Get tampering history for patient"""
    history = tamper_detector.get_patient_tampering_history(pid)
    report = tamper_detector.export_report(pid)
    
    return jsonify({
        "history": history,
        "report": report
    })

@app.route("/api/anomalies/check", methods=["POST"])
def check_anomalies():
    """Check vital signs for anomalies"""
    data = request.json
    patient_id = data.get("patient_id")
    
    anomaly_result = tamper_detector.check_anomaly(
        patient_id,
        {
            "hr": data.get("hr"),
            "bp": data.get("bp"),
            "temp": data.get("temp")
        }
    )
    
    return jsonify(anomaly_result)

# ============================================
# STATISTICS & ANALYTICS
# ============================================

@app.route("/api/statistics")
def get_statistics():
    """Get overall statistics"""
    stats = patient_generator.get_statistics()
    health_metrics = blockchain_manager.get_blockchain_health_metrics()
    
    return jsonify({
        **stats,
        "blockchain_status": {
            "total_blockchains": health_metrics["total_blockchains"],
            "total_blocks": health_metrics["total_blocks"],
            "tampered_records": health_metrics["tampered_blockchains"],
            "invalid_block_count": health_metrics["invalid_block_count"],
            "suspicious_blocks": health_metrics["suspicious_blocks"],
            "suspicious_transaction_rate_percent": health_metrics["suspicious_transaction_rate_percent"],
            "integrity_score": health_metrics["blockchain_health_score_percent"]
        },
        "cloud_status": {
            "metrics": cloud_security_gateway.threat_metrics
        }
    })

# ============================================
# ZERO TRUST SECURITY ENDPOINTS (LAYER 2)
# ============================================

@app.route("/api/security/registry")
def get_security_registry():
    """Exposes device registry database"""
    return jsonify(zero_trust_validator.device_registry)

@app.route("/api/security/audit_logs")
def get_security_audit_logs():
    """Exposes security logs"""
    try:
        with open(zero_trust_validator.AUDIT_LOG_PATH or "data/processed/security_audit_log.json", "r") as f:
            logs = json.load(f)
        return jsonify(logs)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/security/quarantine")
def get_security_quarantine():
    """Exposes quarantined packets"""
    try:
        with open(zero_trust_validator.QUARANTINE_PATH or "data/processed/quarantine_log.json", "r") as f:
            logs = json.load(f)
        return jsonify(logs)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/security/attack", methods=["POST"])
def trigger_security_attack():
    """Trigger a mock attack on a patient's device"""
    data = request.json
    pid = data.get("patient_id")
    attack_type = data.get("attack_type") # 'spoofing', 'replay', 'delay', 'forged_id', 'sig_mismatch', 'invalid_token', None
    
    if pid:
        patient_generator.inject_attack(pid, attack_type)
        return jsonify({"success": True, "message": f"Activated {attack_type} attack on patient {pid}"})
    return jsonify({"success": False, "error": "Missing patient_id"})

@app.route("/api/security/retrain", methods=["POST"])
def retrain_models():
    """Trigger AI Threat Analysis model retraining"""
    try:
        ai_threat_detector.train_models()
        return jsonify({"success": True, "message": "AI Threat Analysis models successfully retrained!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================
# CLOUD SECURITY & API GATEWAY ENDPOINTS (LAYER 5)
# ============================================

def get_client_ip():
    """Retrieve client IP address for rate limiting"""
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"

def authenticate_request() -> Tuple[bool, Dict[str, Any]]:
    """Helper to authenticate incoming requests via bearer JWT"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return False, {"error": "Missing or malformed Authorization header"}
    token = auth_header.split(" ")[1]
    return cloud_security_gateway.verify_jwt_token(token)

@app.route("/api/cloud/login", methods=["POST"])
def cloud_login():
    """Authenticates users and issues JWT authorization tokens"""
    # Rate Limiting Check
    client_ip = get_client_ip()
    if cloud_security_gateway.is_rate_limited(client_ip):
        cloud_security_gateway.log_cloud_event("ANONYMOUS", "None", "LOGIN", "API_GATEWAY", "BLOCKED", "Rate limit violation")
        return jsonify({"error": "Too many requests. Rate limit exceeded."}), 429
        
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")
    
    # Predefined credentials mapping for simulation
    credentials = {
        "dr_swati": ("secure_doc123", "Doctor"),
        "nurse_rohan": ("secure_nurse123", "Nurse"),
        "admin_system": ("secure_admin123", "Admin"),
        "researcher_bob": ("secure_research123", "Researcher")
    }
    
    if username in credentials and credentials[username][0] == password:
        role = credentials[username][1]
        token = cloud_security_gateway.generate_jwt_token(username, role)
        cloud_security_gateway.log_cloud_event(username, role, "LOGIN", "AUTH_SERVICE", "SUCCESS", "Logged in successfully")
        return jsonify({"success": True, "token": token, "role": role})
        
    cloud_security_gateway.log_cloud_event(username or "ANONYMOUS", "None", "LOGIN", "AUTH_SERVICE", "FAILURE", "Invalid credentials")
    return jsonify({"error": "Invalid username or password"}), 401

@app.route("/api/cloud/transmit", methods=["POST"])
def cloud_transmit():
    """Securely transmits verified blockchain records to the cloud data lake"""
    # 1. Rate Limiting
    client_ip = get_client_ip()
    if cloud_security_gateway.is_rate_limited(client_ip):
        cloud_security_gateway.log_cloud_event("ANONYMOUS", "None", "TRANSMIT", "API_GATEWAY", "BLOCKED", "Rate limit violation")
        return jsonify({"error": "Rate limit exceeded"}), 429
        
    # 2. Authentication
    is_authenticated, auth_data = authenticate_request()
    if not is_authenticated:
        cloud_security_gateway.log_cloud_event("ANONYMOUS", "None", "TRANSMIT", "API_GATEWAY", "FAILURE", auth_data.get("error", "Auth error"))
        return jsonify({"error": "Unauthorized: " + auth_data.get("error", "")}), 401
        
    username = auth_data.get("sub", "unknown")
    role = auth_data.get("role", "none")
    
    # 3. RBAC checks (Doctor, Nurse, Admin can transmit)
    if not cloud_security_gateway.verify_rbac(role, ["Doctor", "Nurse", "Admin"]):
        cloud_security_gateway.log_cloud_event(username, role, "TRANSMIT", "CLOUD_LAKE", "DENIED", "Insufficient privileges")
        return jsonify({"error": "Forbidden: Insufficient privileges"}), 403
        
    # 4. Request Validation and Sanitization
    data = request.json or {}
    is_clean, reason = cloud_security_gateway.validate_and_sanitize(data)
    if not is_clean:
        cloud_security_gateway.log_cloud_event(username, role, "TRANSMIT", "API_GATEWAY", "BLOCKED", f"Sanitization failure: {reason}")
        return jsonify({"error": f"Bad Request: Malicious or invalid payload ({reason})"}), 400
        
    patient_id = data.get("patient_id")
    if not patient_id:
        return jsonify({"error": "Missing patient_id"}), 400
        
    # 5. Cloud Revalidation (Step 8)
    block_hash = data.get("hash")
    prev_hash = data.get("previous_hash")
    block_index = data.get("index")
    
    if not block_hash or not prev_hash or block_index is None:
        cloud_security_gateway.log_cloud_event(username, role, "TRANSMIT", "CLOUD_VERIFY", "REJECTED", "Missing blockchain metadata")
        return jsonify({"error": "Cloud Integrity verification failed: Missing blockchain metadata"}), 400
        
    # Recalculate block hash to verify it wasn't altered in transit
    block_recalc_data = {
        "index": block_index,
        "timestamp": data.get("timestamp"),
        "patient_id": patient_id,
        "health_data": data.get("health_data"),
        "previous_hash": prev_hash,
        "nonce": data.get("nonce", 0),
        "validation_status": data.get("validation_status", "ACCEPT"),
        "trust_score": data.get("trust_score", 100.0),
        "label": data.get("label", "NORMAL")
    }
    
    block_string = json.dumps(block_recalc_data, sort_keys=True)
    recalculated_hash = hashlib.sha256(block_string.encode()).hexdigest()
    
    if recalculated_hash != block_hash:
        cloud_security_gateway.log_cloud_event(username, role, "TRANSMIT", "CLOUD_VERIFY", "FAILURE", f"Hash mismatch. Recalc: {recalculated_hash[:10]}... Recv: {block_hash[:10]}...")
        return jsonify({"error": "Cloud Integrity verification failed: Cryptographic block hash mismatch"}), 400
        
    # 6. End-to-End Encryption & Logical Partitioning (Step 6 & 9)
    vital_payload_str = json.dumps(data.get("health_data", {}))
    encrypted_vital_data = cloud_security_gateway.encrypt_payload(vital_payload_str)
    
    metadata_fields = {
        "block_index": block_index,
        "block_hash": block_hash,
        "previous_hash": prev_hash,
        "trust_score": data.get("trust_score"),
        "validation_status": data.get("validation_status"),
        "label": data.get("label"),
        "timestamp": data.get("timestamp")
    }
    
    success = cloud_security_gateway.save_to_cloud_lake(patient_id, encrypted_vital_data, metadata_fields)
    if success:
        cloud_security_gateway.log_cloud_event(username, role, "TRANSMIT", "CLOUD_LAKE", "SUCCESS", f"Committed Block #{block_index} for patient {patient_id}")
        return jsonify({"success": True, "message": "Successfully transmitted and committed block data to cloud."})
        
    return jsonify({"error": "Failed to store record in cloud database"}), 500

@app.route("/api/cloud/patient/<pid>", methods=["GET"])
def cloud_get_patient_records(pid):
    """Secure cloud route to retrieve patient records, enforcing role-based anonymization"""
    client_ip = get_client_ip()
    if cloud_security_gateway.is_rate_limited(client_ip):
        return jsonify({"error": "Rate limit exceeded"}), 429
        
    is_authenticated, auth_data = authenticate_request()
    if not is_authenticated:
        return jsonify({"error": "Unauthorized: " + auth_data.get("error", "")}), 401
        
    username = auth_data.get("sub", "unknown")
    role = auth_data.get("role", "none")
    
    if not cloud_security_gateway.verify_rbac(role, ["Doctor", "Nurse", "Admin", "Researcher"]):
        return jsonify({"error": "Forbidden: Insufficient privileges"}), 403
        
    records = cloud_security_gateway.read_from_cloud_lake(pid)
    decrypted_records = []
    
    for r in records:
        try:
            decrypted_vitals = json.loads(cloud_security_gateway.decrypt_payload(r["encrypted_data"]))
            decrypted_records.append({
                "timestamp": r["timestamp"],
                "health_data": decrypted_vitals,
                "metadata": r["metadata"]
            })
        except Exception as e:
            print(f"⚠️  Decryption error: {e}")
            
    if role == "Researcher":
        anonymized_records = []
        for r in decrypted_records:
            anonymized_records.append({
                "timestamp": r["timestamp"],
                "health_data": r["health_data"],
                "metadata": {
                    "block_index": r["metadata"].get("block_index"),
                    "trust_score": r["metadata"].get("trust_score"),
                    "validation_status": r["metadata"].get("validation_status"),
                    "label": r["metadata"].get("label")
                }
            })
        cloud_security_gateway.log_cloud_event(username, role, "READ_PATIENT_ANONYMIZED", f"PATIENT_{pid}", "SUCCESS")
        return jsonify({
            "patient_id": hashlib.sha256(pid.encode()).hexdigest()[:12],
            "role": role,
            "anonymized": True,
            "records": anonymized_records
        })
        
    patients = read_data()
    patient_name = "Unknown Patient"
    patient_age = "N/A"
    for p in patients:
        if p["id"] == pid:
            patient_name = p["name"]
            patient_age = p["age"]
            break
            
    cloud_security_gateway.log_cloud_event(username, role, "READ_PATIENT_FULL", f"PATIENT_{pid}", "SUCCESS")
    return jsonify({
        "patient_id": pid,
        "name": patient_name,
        "age": patient_age,
        "role": role,
        "anonymized": False,
        "records": decrypted_records
    })

@app.route("/api/cloud/backup/simulate_disaster", methods=["POST"])
def simulate_cloud_disaster():
    """Simulates zero-day file corruption or deletion of the cloud data lake"""
    is_authenticated, auth_data = authenticate_request()
    if not is_authenticated or auth_data.get("role") != "Admin":
        return jsonify({"error": "Forbidden: Requires Admin privileges"}), 403
        
    try:
        with open(DATA_LAKE_PATH, "w") as f:
            f.write("{ CORRUPTED_FILE_DATA_NULL }")
            
        cloud_security_gateway.log_cloud_event(auth_data.get("sub"), "Admin", "CORRUPT_DATA_LAKE", "DATA_LAKE", "SUCCESS", "Triggered database corruption simulation")
        return jsonify({"success": True, "message": "Simulated cloud disaster: Healthcare Data Lake is now corrupted!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/cloud/backup/recover", methods=["POST"])
def recover_cloud_disaster():
    """Triggers the disaster recovery standby failover mechanism"""
    is_authenticated, auth_data = authenticate_request()
    if not is_authenticated or auth_data.get("role") != "Admin":
        return jsonify({"error": "Forbidden: Requires Admin privileges"}), 403
        
    success = cloud_security_gateway.simulate_failover()
    if success:
        return jsonify({"success": True, "message": "Disaster recovery failover successful! Standby backup restored."})
    return jsonify({"success": False, "error": "Failover recovery failed"}), 500

@app.route("/api/cloud/backup/status", methods=["GET"])
def get_backup_status():
    """Exposes backups metrics and database integrity status"""
    is_corrupted = False
    try:
        with open(DATA_LAKE_PATH, "r") as f:
            json.load(f)
    except:
        is_corrupted = True
        
    return jsonify({
        "data_lake_path": DATA_LAKE_PATH,
        "backup_path": BACKUP_PATH,
        "is_corrupted": is_corrupted,
        "total_backups_created": cloud_security_gateway.threat_metrics["total_backups_created"],
        "failover_occurrences": cloud_security_gateway.threat_metrics["failover_occurrences"]
    })

@app.route("/api/cloud/threat_observability", methods=["GET"])
def get_threat_observability():
    """Exposes rate limiting, JWT failures, and threat logs for monitoring"""
    try:
        with open(AUDIT_LOG_PATH, "r") as f:
            logs = json.load(f)
    except:
        logs = []
        
    return jsonify({
        "metrics": cloud_security_gateway.threat_metrics,
        "recent_audit_trail": logs[-15:]
    })

@app.route("/metrics", methods=["GET"])
def prometheus_metrics():
    """Exposes plain-text Prometheus exporter metrics"""
    try:
        # Gather metrics
        patients = read_data()
        total_patients = len(patients)
        
        trust_scores = [p.get("trust_score", 100.0) for p in patients if "trust_score" in p]
        avg_trust_score = sum(trust_scores) / len(trust_scores) if trust_scores else 100.0
        
        health = blockchain_manager.get_blockchain_health_metrics()
        total_blocks = health.get("total_blocks", 0)
        health_score = health.get("blockchain_health_score_percent", 100.0)
        tampered_chains = health.get("tampered_blockchains", 0)
        
        threats = cloud_security_gateway.threat_metrics
        
        lines = []
        
        lines.append("# HELP iomt_patients_total Total registered patients.")
        lines.append("# TYPE iomt_patients_total gauge")
        lines.append(f"iomt_patients_total {total_patients}")
        
        lines.append("# HELP iomt_trust_score_average Moving average trust score across active patients.")
        lines.append("# TYPE iomt_trust_score_average gauge")
        lines.append(f"iomt_trust_score_average {avg_trust_score:.2f}")
        
        lines.append("# HELP iomt_blockchain_blocks_total Total blocks committed to patient blockchains.")
        lines.append("# TYPE iomt_blockchain_blocks_total counter")
        lines.append(f"iomt_blockchain_blocks_total {total_blocks}")
        
        lines.append("# HELP iomt_blockchain_health_score_percent Current blockchain consensus health percentage.")
        lines.append("# TYPE iomt_blockchain_health_score_percent gauge")
        lines.append(f"iomt_blockchain_health_score_percent {health_score:.2f}")
        
        lines.append("# HELP iomt_blockchain_tampered_total Number of currently tampered patient chains.")
        lines.append("# TYPE iomt_blockchain_tampered_total gauge")
        lines.append(f"iomt_blockchain_tampered_total {tampered_chains}")
        
        lines.append("# HELP iomt_requests_total Total number of HTTP requests processed.")
        lines.append("# TYPE iomt_requests_total counter")
        for (method, endpoint), count in REQUEST_COUNTS.items():
            lines.append(f'iomt_requests_total{{method="{method}",endpoint="{endpoint}"}} {count}')
            
        lines.append("# HELP iomt_threats_blocked_total Security threat metrics blocked by cloud gateway.")
        lines.append("# TYPE iomt_threats_blocked_total counter")
        for threat_type, count in threats.items():
            lines.append(f'iomt_threats_blocked_total{{type="{threat_type}"}} {count}')
            
        return Response("\n".join(lines) + "\n", mimetype="text/plain")
    except Exception as e:
        app.logger.error(f"Error serving metrics: {e}")
        return Response(f"error: {str(e)}\n", status=500, mimetype="text/plain")

@app.route("/api/chaos/trigger", methods=["POST"])
def chaos_trigger():
    """Forces simulated chaos events (crash, CPU leak) for K8s orchestration verification"""
    # Verify Admin Role
    is_authenticated, auth_data = authenticate_request()
    if not is_authenticated:
        return jsonify({"error": "Unauthorized: JWT missing or invalid"}), 401
    if auth_data.get("role") != "Admin":
        return jsonify({"error": "Forbidden: Requires Admin privileges"}), 403
        
    data = request.json or {}
    chaos_type = data.get("type", "crash")
    
    if chaos_type == "crash":
        cloud_security_gateway.log_cloud_event(auth_data.get("sub"), "Admin", "CHAOS_TRIGGER", "CONTAINER", "SUCCESS", "Triggered container crash simulation")
        print("💥 CHAOS INJECTION: Simulating container crash! Exiting...")
        
        # Spawn exit thread to return HTTP response first
        def exit_later():
            time.sleep(0.5)
            # Use os._exit to bypass clean teardowns (simulate hard crash)
            import os
            os._exit(1)
        threading.Thread(target=exit_later).start()
        return jsonify({"success": True, "message": "Crash injected. Container will exit in 500ms."})
        
    elif chaos_type == "cpu_leak":
        cloud_security_gateway.log_cloud_event(auth_data.get("sub"), "Admin", "CHAOS_TRIGGER", "CPU", "SUCCESS", "Triggered CPU leakage simulation")
        print("🔥 CHAOS INJECTION: Simulating CPU leak/load spike...")
        
        def cpu_spike():
            start_time = time.time()
            # Loop intensively for 15 seconds to trigger autoscaling conditions
            while time.time() - start_time < 15:
                _ = 100 * 100
        threading.Thread(target=cpu_spike).start()
        return jsonify({"success": True, "message": "CPU load spike injected for 15 seconds."})
        
    return jsonify({"error": "Invalid chaos type"}), 400

# ============================================
# LAYER 7 API ROUTES
# ============================================

@app.route("/api/patient/<pid>/twin", methods=["GET"])
def get_patient_twin(pid):
    """Retrieves 10-step virtual patient twin forecasts and deterioration index"""
    patients = read_data()
    patient_info = None
    for p in patients:
        if p["id"] == pid:
            patient_info = p
            break
            
    if not patient_info:
        return jsonify({"error": f"Patient {pid} not found"}), 404
        
    history = replay_manager.get_replay(pid)
    
    # Check if septic is active
    septic_res = septic_checker.check_septic_behavior(history)
    is_septic = septic_res.get("alert_triggered", False)
    
    # Initialize twin if needed
    if pid not in patient_twins:
        bp_str = patient_info.get("bp", "120/80")
        try:
            bps, bpd = map(float, bp_str.split("/"))
        except Exception:
            bps, bpd = 120.0, 80.0
            
        patient_twins[pid] = DigitalPatientTwin(
            patient_id=pid,
            baseline_hr=float(patient_info.get("hr", 75.0)),
            baseline_temp=float(patient_info.get("temp", 37.0)),
            baseline_bp_sys=bps,
            baseline_bp_dia=bpd
        )
        
    twin = patient_twins[pid]
    projections = twin.generate_projections(history, steps=10, is_septic=is_septic)
    
    # Current deterioration index
    bp_str = patient_info.get("bp", "120/80")
    try:
        bps, bpd = map(float, bp_str.split("/"))
    except Exception:
        bps, bpd = 120.0, 80.0
    current_det = twin.calculate_deterioration_index(
        float(patient_info.get("hr", 75.0)),
        float(patient_info.get("temp", 37.0)),
        bps,
        bpd
    )
    
    return jsonify({
        "patient_id": pid,
        "current_vitals": {
            "hr": patient_info.get("hr"),
            "bp": patient_info.get("bp"),
            "temp": patient_info.get("temp"),
            "condition": patient_info.get("condition"),
            "deterioration_index": round(current_det, 1)
        },
        "projections": projections,
        "clinical_support": septic_res
    })

@app.route("/api/patient/<pid>/replay", methods=["GET"])
def get_patient_replay(pid):
    """Retrieves step-by-step forensic replay history (up to last 50 points)"""
    replay_data = replay_manager.get_replay(pid)
    return jsonify({
        "patient_id": pid,
        "replay_data": replay_data
    })

@app.route("/api/patient/<pid>/knowledge_graph", methods=["GET"])
def get_patient_knowledge_graph(pid):
    """Generates explainable healthcare relationship nodes and edges"""
    patients = read_data()
    patient_info = None
    for p in patients:
        if p["id"] == pid:
            patient_info = p
            break
            
    if not patient_info:
        return jsonify({"error": f"Patient {pid} not found"}), 404
        
    block_history = blockchain_manager.get_patient_chain(pid)
    anomalies = tamper_detector.get_patient_tampering_history(pid)
    
    alerts = []
    for a in anomalies:
        changes_desc = ", ".join([f"{k} changed" for k in a.get("changes", {}).keys()])
        alerts.append({
            "message": f"Data Tampering Detected: {changes_desc or 'vitals anomaly'}",
            "category": "Security",
            "severity": a.get("severity", "HIGH"),
            "timestamp": a.get("timestamp")
        })
        
    replay_data = replay_manager.get_replay(pid)
    septic_res = septic_checker.check_septic_behavior(replay_data)
    if septic_res.get("alert_triggered"):
        alerts.append({
            "message": "Septic Alert: Continuous HR/Temp elevation and BP decay",
            "category": "Clinical",
            "severity": "CRITICAL",
            "timestamp": datetime.utcnow().isoformat()
        })
    elif septic_res.get("septic_risk_score", 0.0) > 30.0:
        alerts.append({
            "message": "Clinical Warning: Elevated septic risk factors",
            "category": "Clinical",
            "severity": "WARNING",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    graph = knowledge_graph_generator.generate_graph(
        patient_id=pid,
        patient_info=patient_info,
        block_history=block_history,
        alerts=alerts,
        device_registry=zero_trust_validator.device_registry
    )
    return jsonify(graph)

@app.route("/api/security/device/isolate", methods=["POST"])
def isolate_device():
    """Isolates a compromised MQTT device in the registry (Admin only)"""
    is_authenticated, auth_data = authenticate_request()
    if not is_authenticated:
        return jsonify({"error": "Unauthorized: JWT missing or invalid"}), 401
    if auth_data.get("role") != "Admin":
        return jsonify({"error": "Forbidden: Requires Admin privileges"}), 403
        
    data = request.json or {}
    device_id = data.get("device_id")
    reason = data.get("reason", "Autonomous security response isolation")
    
    if not device_id:
        return jsonify({"error": "Missing device_id parameter"}), 400
        
    success = zero_trust_validator.isolate_device(device_id, reason)
    if success:
        return jsonify({"success": True, "message": f"Device {device_id} successfully isolated."})
    return jsonify({"error": f"Device {device_id} not found in registry"}), 404

@app.route("/api/security/device/activate", methods=["POST"])
def activate_device_route():
    """Restores an isolated/suspended MQTT device in the registry (Admin only)"""
    is_authenticated, auth_data = authenticate_request()
    if not is_authenticated:
        return jsonify({"error": "Unauthorized: JWT missing or invalid"}), 401
    if auth_data.get("role") != "Admin":
        return jsonify({"error": "Forbidden: Requires Admin privileges"}), 403
        
    data = request.json or {}
    device_id = data.get("device_id")
    
    if not device_id:
        return jsonify({"error": "Missing device_id parameter"}), 400
        
    success = zero_trust_validator.activate_device(device_id)
    if success:
        return jsonify({"success": True, "message": f"Device {device_id} successfully activated."})
    return jsonify({"error": f"Device {device_id} not found in registry"}), 404

@app.route("/api/patient/<pid>/override", methods=["POST"])
def record_clinician_override(pid):
    """Logs clinician override details for feedback and continuous learning"""
    is_authenticated, auth_data = authenticate_request()
    if not is_authenticated:
        return jsonify({"error": "Unauthorized: JWT missing or invalid"}), 401
    if auth_data.get("role") not in ["Doctor", "Admin"]:
        return jsonify({"error": "Forbidden: Requires Doctor or Admin privileges"}), 403
        
    data = request.json or {}
    record_index = data.get("record_index")
    original_decision = data.get("original_decision")
    overridden_decision = data.get("overridden_decision")
    notes = data.get("notes", "")
    
    if record_index is None or not original_decision or not overridden_decision:
        return jsonify({"error": "Missing override details"}), 400
        
    entry = feedback_manager.record_override(
        clinician_id=auth_data.get("sub", "unknown_clinician"),
        patient_id=pid,
        record_index=int(record_index),
        original_decision=original_decision,
        overridden_decision=overridden_decision,
        notes=notes
    )
    return jsonify({"success": True, "override": entry})

@app.route("/api/patient/<pid>/anonymized_research", methods=["GET"])
def get_anonymized_research(pid):
    """Exports patient data logs stripped of direct identifier tokens for research"""
    is_authenticated, auth_data = authenticate_request()
    if not is_authenticated:
        return jsonify({"error": "Unauthorized: JWT missing or invalid"}), 401
    if auth_data.get("role") not in ["Doctor", "Admin", "Researcher"]:
        return jsonify({"error": "Forbidden: Insufficient privileges"}), 403
        
    replay_data = replay_manager.get_replay(pid)
    anonymized = research_exporter.export_data(pid, replay_data)
    return jsonify({
        "patient_id_anonymized": f"SUBJ_{hashlib.sha256(pid.encode()).hexdigest()[:8].upper()}",
        "records": anonymized
    })

# ============================================
# LAYER 8 GLOBAL FEDERATION & TRUST ROUTES
# ============================================

@app.route("/global_dashboard")
def global_dashboard():
    """Serves the Global Command and Intelligence Center view"""
    return render_template("global_dashboard.html")

@app.route("/api/federated/status", methods=["GET"])
def get_federated_status():
    """Returns the current status of the global federated ecosystem"""
    nodes_info = {}
    for nid, node in federated_network.nodes.items():
        nodes_info[nid] = {
            "name": node.name,
            "is_authority": node.is_authority,
            "dataset_size": len(node.local_dataset_y),
            "anomaly_threshold": node.anomaly_threshold
        }
    
    return jsonify({
        "nodes": nodes_info,
        "global_model": {
            "weights": federated_network.global_model.weights.tolist(),
            "bias": federated_network.global_model.bias,
            "latest_loss": federated_network.training_history[-1]["global_loss"] if federated_network.training_history else None
        },
        "training_history": federated_network.training_history,
        "threat_registry": federated_network.threat_registry,
        "global_device_registry": federated_network.global_device_registry,
        "policy_threat_index": federated_network.policy_threat_index,
        "digital_twin": federated_network.twin_stats
    })

@app.route("/api/federated/train", methods=["POST"])
def trigger_federated_train():
    """Triggers a cooperative training round using FedAvg"""
    is_authenticated, auth_data = authenticate_request()
    if not is_authenticated:
        return jsonify({"error": "Unauthorized: JWT missing or invalid"}), 401
    if auth_data.get("role") not in ["Doctor", "Admin", "Researcher"]:
        return jsonify({"error": "Forbidden: Insufficient privileges"}), 403
        
    data = request.json or {}
    epochs = int(data.get("epochs", 5))
    lr = float(data.get("lr", 0.001))
    
    round_details = federated_network.run_federated_round(epochs=epochs, learning_rate=lr)
    return jsonify({
        "success": True,
        "round_details": round_details
    })

@app.route("/api/federated/threats", methods=["POST"])
def report_global_threat():
    """Publishes security threat indicators globally"""
    is_authenticated, auth_data = authenticate_request()
    if not is_authenticated:
        return jsonify({"error": "Unauthorized: JWT missing or invalid"}), 401
    if auth_data.get("role") not in ["Doctor", "Admin"]:
        return jsonify({"error": "Forbidden: Insufficient privileges"}), 403
        
    data = request.json or {}
    threat_id = data.get("threat_id", f"THREAT_{int(time.time())}")
    reported_by = data.get("reported_by", "Unknown Hospital")
    description = data.get("description", "IoMT telemetry spoofing signature detected")
    signature = data.get("signature", {})
    
    threat_record = federated_network.publish_threat(threat_id, reported_by, description, signature)
    return jsonify({
        "success": True,
        "threat": threat_record,
        "new_policy_sensitivity": federated_network.policy_threat_index
    })

@app.route("/api/federated/consensus/verify", methods=["POST"])
def verify_consensus_block():
    """Simulates Proof of Authority block signature gathering"""
    data = request.json or {}
    proposer = data.get("proposer", "Hospital Alpha")
    block_data = data.get("block_data", {})
    
    if not block_data:
        return jsonify({"error": "Missing block_data"}), 400
        
    consensus_res = federated_network.propose_and_verify_block(proposer, block_data)
    return jsonify(consensus_res)

@app.route("/api/federated/privacy/query", methods=["POST"])
def query_privacy_preserving():
    """Returns anonymized metrics using Differential Privacy or Homomorphic Encryption"""
    data = request.json or {}
    query_type = data.get("type", "dp") # 'dp' or 'he'
    
    patients = read_data()
    heart_rates = [float(p.get("hr", 72.0)) for p in patients if p.get("hr") is not None]
    
    if not heart_rates:
        heart_rates = [72.0, 75.0, 80.0, 68.0, 74.0] # Fallbacks
        
    if query_type == "dp":
        epsilon = float(data.get("epsilon", 1.0))
        true_mean, dp_mean = federated_network.get_population_average_hr_with_dp(heart_rates, epsilon=epsilon)
        return jsonify({
            "query_type": "Differential Privacy",
            "epsilon": epsilon,
            "true_mean": true_mean,
            "anonymized_mean": dp_mean,
            "total_records_processed": len(heart_rates)
        })
        
    elif query_type == "he":
        # Convert heart rates to integers for modular encryption arithmetic
        if "values" in data:
            int_hrs = [int(v) for v in data["values"]]
        else:
            int_hrs = [int(round(hr)) for hr in heart_rates[:5]] # Limit to 5 records for demonstration
        he_res = federated_network.perform_homomorphic_aggregation(int_hrs)
        return jsonify({
            "query_type": "Homomorphic Encryption (Paillier)",
            "aggregation": he_res
        })
        
    return jsonify({"error": "Invalid query type"}), 400

@app.route("/api/federated/digital_twin", methods=["GET", "POST"])
def get_digital_twin_metrics():
    """Returns simulated status of global digital twin infrastructure"""
    if request.method == "POST":
        # Simulate clock tick / updates
        stats = federated_network.update_digital_twin_metrics()
    else:
        stats = federated_network.twin_stats
    return jsonify(stats)

@app.route("/api/federated/device/sync", methods=["POST"])
def sync_device_trust():
    """Synchronizes device local trust reputation globally"""
    is_authenticated, auth_data = authenticate_request()
    if not is_authenticated:
        return jsonify({"error": "Unauthorized: JWT missing or invalid"}), 401
        
    data = request.json or {}
    device_id = data.get("device_id")
    local_score = float(data.get("local_score", 100.0))
    
    if not device_id:
        return jsonify({"error": "Missing device_id"}), 400
        
    sync_status = federated_network.synchronize_trust_score(device_id, local_score)
    return jsonify({
        "success": True,
        "device_id": device_id,
        "sync_status": sync_status
    })


# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Server error"}), 500

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=True, host="0.0.0.0", port=port)
    