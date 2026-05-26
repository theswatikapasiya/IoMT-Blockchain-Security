"""
Layer 7 - Clinical Decision Support, Digital Twin, and Autonomous Response Tests
Verifies physiological twin projections, septic trend warnings, knowledge graphs,
forensic replay streams, and authenticated isolation endpoints.
"""

import unittest
import json
import time
from datetime import datetime
from blockchain.clinical_decision_support import (
    DigitalPatientTwin, SepticBehaviorChecker, HealthcareKnowledgeGraph,
    ForensicReplayManager, ClinicianFeedbackManager, AnonymizedResearchExporter
)
from blockchain.zero_trust import zero_trust_validator
from app import app, replay_manager, patient_twins, feedback_manager

class TestLayer7ClinicalDecision(unittest.TestCase):
    """Test suite for clinical support logic and Digital Twin representations"""

    def setUp(self):
        self.twin = DigitalPatientTwin("PS1000", baseline_hr=75.0, baseline_temp=37.0, baseline_bp_sys=120.0, baseline_bp_dia=80.0)
        self.septic_checker = SepticBehaviorChecker()
        self.replay_mgr = ForensicReplayManager(limit=5)
        self.graph_gen = HealthcareKnowledgeGraph()
        
    def test_deterioration_index(self):
        """Test calculation of patient deterioration index"""
        # Completely normal vitals should yield 0% deterioration
        det_normal = self.twin.calculate_deterioration_index(75.0, 37.0, 120.0, 80.0)
        self.assertEqual(det_normal, 0.0)
        
        # Highly abnormal vitals should increase the index
        det_high = self.twin.calculate_deterioration_index(130.0, 39.5, 80.0, 50.0)
        self.assertGreater(det_high, 50.0)
        self.assertEqual(det_high, 80.0) # calculated based on vital deviations
        
    def test_digital_twin_projections_normal(self):
        """Test digital twin projections under stable conditions"""
        history = [
            {"timestamp": "2026-05-26T20:00:00Z", "hr": 74.0, "temp": 36.9, "bp": "120/80"},
            {"timestamp": "2026-05-26T20:01:00Z", "hr": 75.0, "temp": 37.0, "bp": "121/80"},
            {"timestamp": "2026-05-26T20:02:00Z", "hr": 76.0, "temp": 37.0, "bp": "120/81"}
        ]
        projections = self.twin.generate_projections(history, steps=10, is_septic=False)
        
        self.assertEqual(len(projections["hr"]), 10)
        self.assertEqual(len(projections["temp"]), 10)
        self.assertEqual(len(projections["bp_sys"]), 10)
        self.assertEqual(len(projections["bp_dia"]), 10)
        self.assertEqual(len(projections["deterioration_index"]), 10)
        
    def test_digital_twin_projections_septic(self):
        """Test digital twin projections under septic conditions"""
        history = [
            {"timestamp": "2026-05-26T20:00:00Z", "hr": 85.0, "temp": 37.8, "bp": "115/75"},
            {"timestamp": "2026-05-26T20:01:00Z", "hr": 92.0, "temp": 38.3, "bp": "108/70"},
            {"timestamp": "2026-05-26T20:02:00Z", "hr": 99.0, "temp": 38.8, "bp": "98/62"}
        ]
        projections = self.twin.generate_projections(history, steps=10, is_septic=True)
        
        # HR should progressively approach targets (rising)
        self.assertGreater(projections["hr"][-1], 110.0)
        # Temp should rise
        self.assertGreater(projections["temp"][-1], 39.0)
        # BP Sys should decay (hypotension)
        self.assertLess(projections["bp_sys"][-1], 90.0)
        # Deterioration index should rise to critical
        self.assertGreater(projections["deterioration_index"][-1], 70.0)

    def test_septic_checker_normal(self):
        """Test septic checker on normal/stable trends"""
        history = [
            {"hr": 72.0, "temp": 36.8, "bp": "120/80"},
            {"hr": 73.0, "temp": 36.9, "bp": "121/80"},
            {"hr": 72.5, "temp": 36.8, "bp": "120/79"}
        ]
        res = self.septic_checker.check_septic_behavior(history)
        self.assertFalse(res["alert_triggered"])
        self.assertEqual(res["severity"], "NORMAL")
        self.assertLess(res["septic_risk_score"], 20.0)

    def test_septic_checker_critical(self):
        """Test septic checker on clinical septic deterioration trends"""
        # Trend: HR going up rapidly, Temp going up rapidly, BP going down rapidly
        history = [
            {"hr": 75.0, "temp": 36.8, "bp": "120/80"},
            {"hr": 85.0, "temp": 37.5, "bp": "112/72"},
            {"hr": 95.0, "temp": 38.2, "bp": "104/65"},
            {"hr": 105.0, "temp": 38.9, "bp": "96/58"},
            {"hr": 115.0, "temp": 39.5, "bp": "88/50"}
        ]
        res = self.septic_checker.check_septic_behavior(history)
        self.assertTrue(res["alert_triggered"])
        self.assertEqual(res["severity"], "CRITICAL")
        self.assertGreaterEqual(res["septic_risk_score"], 70.0)
        self.assertTrue(any("septic" in rec.lower() for rec in res["recommendations"]))

    def test_knowledge_graph(self):
        """Test relational knowledge graph output formatting and connections"""
        patient_info = {"name": "Varun Patel", "age": 45, "condition": "Critical"}
        block_history = [
            {"index": 0, "hash": "genesis_hash", "previous_hash": "0", "validation_status": "ACCEPT", "trust_score": 100.0, "label": "NORMAL"},
            {"index": 1, "hash": "block1_hash", "previous_hash": "genesis_hash", "validation_status": "ACCEPT", "trust_score": 98.0, "label": "NORMAL"}
        ]
        alerts = [
            {"message": "Suspicious vital drift", "category": "Security", "severity": "HIGH", "timestamp": "2026-05-26T20:00:00Z"}
        ]
        
        graph = self.graph_gen.generate_graph(
            patient_id="PS1000",
            patient_info=patient_info,
            block_history=block_history,
            alerts=alerts,
            device_registry=zero_trust_validator.device_registry
        )
        
        self.assertIn("nodes", graph)
        self.assertIn("links", graph)
        
        # Verify node IDs and labels exist
        node_ids = [n["id"] for n in graph["nodes"]]
        self.assertIn("patient_PS1000", node_ids)
        self.assertIn("block_PS1000_0", node_ids)
        self.assertIn("block_PS1000_1", node_ids)
        
        # Verify links relations mapping
        relationships = [l["relationship"] for l in graph["links"]]
        self.assertIn("has_record", relationships)
        self.assertIn("cryptographic_parent", relationships)

    def test_forensic_replay_limits(self):
        """Test circular buffering window bounds of the ForensicReplayManager"""
        for i in range(10):
            self.replay_mgr.add_record("PS1000", {"index": i, "hr": 70 + i})
            
        replay_history = self.replay_mgr.get_replay("PS1000")
        # Should be capped at limit = 5
        self.assertEqual(len(replay_history), 5)
        # Should contain the last 5 records (indices 5, 6, 7, 8, 9)
        self.assertEqual(replay_history[0]["index"], 5)
        self.assertEqual(replay_history[-1]["index"], 9)


class TestLayer7APIRoutes(unittest.TestCase):
    """Test suite for Flask secure REST endpoints in Layer 7"""

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        
        # Pre-seed patient data in replay buffer to avoid empty returns
        replay_manager.add_record("PS1000", {"timestamp": "2026-05-26T20:00:00Z", "hr": 72.0, "temp": 37.0, "bp": "120/80", "trust_score": 100.0, "validation_status": "ACCEPT", "label": "NORMAL"})
        replay_manager.add_record("PS1000", {"timestamp": "2026-05-26T20:01:00Z", "hr": 74.0, "temp": 37.0, "bp": "120/80", "trust_score": 100.0, "validation_status": "ACCEPT", "label": "NORMAL"})
        
    def get_jwt_token(self, username, password) -> str:
        """Helper to log in and get bearer token"""
        resp = self.app.post("/api/cloud/login", json={
            "username": username,
            "password": password
        })
        data = json.loads(resp.data)
        return data.get("token", "")

    def test_get_patient_twin_success(self):
        """Test retrieval of patient digital twin projections"""
        resp = self.app.get("/api/patient/PS1000/twin")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["patient_id"], "PS1000")
        self.assertIn("projections", data)
        self.assertIn("clinical_support", data)
        self.assertIn("hr", data["projections"])
        self.assertIn("temp", data["projections"])

    def test_get_patient_twin_not_found(self):
        """Test twin retrieval for non-existing patient ID returns 404"""
        resp = self.app.get("/api/patient/PS9999/twin")
        self.assertEqual(resp.status_code, 404)

    def test_get_replay(self):
        """Test retrieval of forensic replay buffer records"""
        resp = self.app.get("/api/patient/PS1000/replay")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["patient_id"], "PS1000")
        self.assertGreater(len(data["replay_data"]), 0)

    def test_get_knowledge_graph(self):
        """Test retrieval of explainable knowledge graph structure"""
        resp = self.app.get("/api/patient/PS1000/knowledge_graph")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("nodes", data)
        self.assertIn("links", data)

    def test_device_isolation_auth_missing(self):
        """Test isolation endpoint blocks requests missing authorization token"""
        resp = self.app.post("/api/security/device/isolate", json={"device_id": "ECG_100"})
        self.assertEqual(resp.status_code, 401)

    def test_device_isolation_auth_forbidden(self):
        """Test isolation endpoint blocks non-Admin doctor role (returns 403)"""
        doc_token = self.get_jwt_token("dr_swati", "secure_doc123")
        headers = {"Authorization": f"Bearer {doc_token}"}
        resp = self.app.post("/api/security/device/isolate", headers=headers, json={"device_id": "ECG_100"})
        self.assertEqual(resp.status_code, 403)

    def test_device_isolation_success_and_activation(self):
        """Test successful device isolation and subsequent reactivation by Admin"""
        admin_token = self.get_jwt_token("admin_system", "secure_admin123")
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Isolate device ECG_1000
        resp_iso = self.app.post("/api/security/device/isolate", headers=headers, json={
            "device_id": "ECG_1000",
            "reason": "Simulated compromise trigger"
        })
        self.assertEqual(resp_iso.status_code, 200)
        data_iso = json.loads(resp_iso.data)
        self.assertTrue(data_iso["success"])
        
        # Verify status in validator registry is indeed Isolated
        self.assertEqual(zero_trust_validator.device_registry["ECG_1000"]["status"], "Isolated")
        
        # Re-activate device ECG_1000
        resp_act = self.app.post("/api/security/device/activate", headers=headers, json={
            "device_id": "ECG_1000"
        })
        self.assertEqual(resp_act.status_code, 200)
        data_act = json.loads(resp_act.data)
        self.assertTrue(data_act["success"])
        
        # Verify status in validator registry restored to Active
        self.assertEqual(zero_trust_validator.device_registry["ECG_1000"]["status"], "Active")

    def test_clinician_override_and_anonymized_research(self):
        """Test logging clinician feedback overrides and fetching anonymized research streams"""
        doc_token = self.get_jwt_token("dr_swati", "secure_doc123")
        headers = {"Authorization": f"Bearer {doc_token}"}
        
        # Post override
        resp_over = self.app.post("/api/patient/PS1000/override", headers=headers, json={
            "record_index": 2,
            "original_decision": "QUARANTINE",
            "overridden_decision": "ACCEPT",
            "notes": "Verified correct sensor lead attachment"
        })
        self.assertEqual(resp_over.status_code, 200)
        data_over = json.loads(resp_over.data)
        self.assertTrue(data_over["success"])
        self.assertEqual(data_over["override"]["overridden_decision"], "ACCEPT")
        
        # Get anonymized research feed
        resp_anon = self.app.get("/api/patient/PS1000/anonymized_research", headers=headers)
        self.assertEqual(resp_anon.status_code, 200)
        data_anon = json.loads(resp_anon.data)
        self.assertTrue("patient_id_anonymized" in data_anon)
        self.assertFalse(any("PS1000" in rec.values() for rec in data_anon["records"]))
        
if __name__ == "__main__":
    unittest.main()



