"""
Layer 8 - Federated Intelligence, Global Trust Fabric, and Autonomous Self-Evolving Ecosystem Tests
Verifies federated AI parameter aggregation, Proof of Authority consensus signatures,
homomorphic arithmetic correctness, differential privacy Laplacian noise limits,
and Layer 8 API endpoints.
"""

import os
import sys
import json
import unittest
import numpy as np
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from blockchain.federated_network import federated_network, PaillierKeyPair, FederatedModel
from blockchain.cloud_gateway import cloud_security_gateway

class TestLayer8FederatedSystems(unittest.TestCase):
    """Test suite for Layer 8 federated algorithms and mathematical operations"""
    
    def setUp(self):
        self.network = federated_network
        self.paillier = PaillierKeyPair()
        
    def test_paillier_homomorphic_cryptosystem(self):
        """Test encryption, decryption and homomorphic addition properties of Paillier implementation"""
        val1 = 45
        val2 = 80
        
        # 1. Encrypt inputs
        c1 = self.paillier.encrypt(val1)
        c2 = self.paillier.encrypt(val2)
        
        self.assertNotEqual(c1, val1)
        self.assertNotEqual(c2, val2)
        
        # 2. Decrypt inputs
        dec1 = self.paillier.decrypt(c1)
        dec2 = self.paillier.decrypt(c2)
        
        self.assertEqual(dec1, val1)
        self.assertEqual(dec2, val2)
        
        # 3. Homomorphic Addition (Multiply ciphertexts)
        c_sum = self.paillier.homomorphic_add(c1, c2)
        dec_sum = self.paillier.decrypt(c_sum)
        
        self.assertEqual(dec_sum, val1 + val2)
        
    def test_federated_learning_averaging(self):
        """Test Federated Learning parameter convergence over simulated FedAvg steps"""
        # Save initial parameters
        init_weights = self.network.global_model.weights.copy()
        init_bias = self.network.global_model.bias
        
        # Run training round
        round_data = self.network.run_federated_round(epochs=2, learning_rate=0.005)
        
        self.assertEqual(round_data["round"], len(self.network.training_history))
        self.assertIn("global_loss", round_data)
        
        # Ensure parameters evolved (weights changed)
        self.assertFalse(np.array_equal(self.network.global_model.weights, init_weights))
        self.assertNotEqual(self.network.global_model.bias, init_bias)
        
    def test_proof_of_authority_block_consensus(self):
        """Test Proof of Authority consensus verification rules on simulated block inputs"""
        # Case 1: Compliant physiologic telemetry proposed
        block_normal = {
            "index": 1,
            "health_data": {"hr": 75.0, "temp": 37.0},
            "timestamp": datetime.utcnow().isoformat()
        }
        res_normal = self.network.propose_and_verify_block("Hospital Alpha", block_normal)
        
        self.assertTrue(res_normal["consensus_reached"])
        self.assertEqual(res_normal["status"], "COMMITTED")
        self.assertGreaterEqual(res_normal["signatures_gathered"], 2)
        
        # Case 2: Impossible physiological metrics proposed (Rejected by authorities)
        block_anomalous = {
            "index": 2,
            "health_data": {"hr": 999.0, "temp": 12.0}, # Impossible HR and Temp
            "timestamp": datetime.utcnow().isoformat()
        }
        res_anom = self.network.propose_and_verify_block("Hospital Alpha", block_anomalous)
        
        self.assertFalse(res_anom["consensus_reached"])
        self.assertEqual(res_anom["status"], "REJECTED")
        self.assertEqual(res_anom["signatures_gathered"], 0)
        
    def test_differential_privacy_noise(self):
        """Test Differential Privacy noise addition bounds on population statistics"""
        hrs = [72.0, 75.0, 80.0, 68.0, 74.0, 95.0, 110.0, 60.0]
        
        # Epsilon = 1.0 (Higher privacy, more noise)
        true_mean_1, dp_mean_1 = self.network.get_population_average_hr_with_dp(hrs, epsilon=1.0)
        
        # Epsilon = 5.0 (Lower privacy, less noise)
        true_mean_5, dp_mean_5 = self.network.get_population_average_hr_with_dp(hrs, epsilon=5.0)
        
        self.assertEqual(true_mean_1, true_mean_5)
        
        # Noisy averages should be numeric floats
        self.assertIsInstance(dp_mean_1, float)
        self.assertIsInstance(dp_mean_5, float)
        
    def test_global_threat_propagation_policy_thresholds(self):
        """Test that threat reports propagate and lower node anomaly sensitivity bounds"""
        init_threat_index = self.network.policy_threat_index
        init_sensitivities = [node.anomaly_threshold for node in self.network.nodes.values()]
        
        # Report threat
        self.network.publish_threat(
            threat_id="TEST_THREAT_01",
            reported_by="Hospital Alpha",
            description="Replay Attack test",
            signature={"hr": 140, "temp": 39.5}
        )
        
        # Threat index should rise
        self.assertGreater(self.network.policy_threat_index, init_threat_index)
        
        # Thresholds should adaptively decrease (more sensitive)
        for idx, node in enumerate(self.network.nodes.values()):
            self.assertLessEqual(node.anomaly_threshold, init_sensitivities[idx])


class TestLayer8APIRoutes(unittest.TestCase):
    """Test suite for Layer 8 Flask REST APIs and authorization guards"""
    
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        
    def get_jwt_token(self, username, role) -> str:
        return cloud_security_gateway.generate_jwt_token(username, role)
        
    def test_get_federated_status(self):
        """Test endpoint exposing global federated status metrics"""
        resp = self.app.get("/api/federated/status")
        self.assertEqual(resp.status_code, 200)
        
        data = json.loads(resp.data)
        self.assertIn("nodes", data)
        self.assertIn("global_model", data)
        self.assertIn("training_history", data)
        self.assertIn("threat_registry", data)
        self.assertIn("digital_twin", data)
        
    def test_post_federated_train_unauthorized(self):
        """Test training route rejects requests lacking JWT or having invalid role"""
        # Case 1: No auth
        resp_no_auth = self.app.post("/api/federated/train", json={"epochs": 2})
        self.assertEqual(resp_no_auth.status_code, 401)
        
        # Case 2: Insufficient role (Nurse cannot run federated model aggregation)
        nurse_token = self.get_jwt_token("nurse_rohan", "Nurse")
        headers = {"Authorization": f"Bearer {nurse_token}"}
        resp_nurse = self.app.post("/api/federated/train", json={"epochs": 2}, headers=headers)
        self.assertEqual(resp_nurse.status_code, 403)
        
    def test_post_federated_train_success(self):
        """Test Doctor/Admin role can successfully trigger cooperative learning rounds"""
        doc_token = self.get_jwt_token("dr_swati", "Doctor")
        headers = {"Authorization": f"Bearer {doc_token}"}
        
        resp = self.app.post("/api/federated/train", json={"epochs": 2, "lr": 0.002}, headers=headers)
        self.assertEqual(resp.status_code, 200)
        
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertIn("round_details", data)
        
    def test_post_report_threat(self):
        """Test reporting a threat signature requires permissions and triggers propagation"""
        admin_token = self.get_jwt_token("admin_system", "Admin")
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        resp = self.app.post("/api/federated/threats", json={
            "reported_by": "Diagnostic Beta",
            "description": "ECG drift malicious injection",
            "signature": {"hr": 140, "temp": 39.0}
        }, headers=headers)
        
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertIn("threat", data)
        
    def test_post_consensus_verify(self):
        """Test route for Proof of Authority block verification"""
        resp = self.app.post("/api/federated/consensus/verify", json={
            "proposer": "Diagnostic Beta",
            "block_data": {
                "index": 12,
                "health_data": {"hr": 80.0, "temp": 36.9},
                "previous_hash": "some_hash"
            }
        })
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("consensus_reached", data)
        self.assertIn("signatures_gathered", data)
        
    def test_privacy_preserving_queries(self):
        """Test Differential Privacy and Homomorphic Encryption query response structures"""
        # Case 1: DP Query
        resp_dp = self.app.post("/api/federated/privacy/query", json={
            "type": "dp",
            "epsilon": 1.2
        })
        self.assertEqual(resp_dp.status_code, 200)
        data_dp = json.loads(resp_dp.data)
        self.assertEqual(data_dp["query_type"], "Differential Privacy")
        self.assertIn("anonymized_mean", data_dp)
        
        # Case 2: HE Query
        resp_he = self.app.post("/api/federated/privacy/query", json={
            "type": "he",
            "values": [72, 75, 80, 68]
        })
        self.assertEqual(resp_he.status_code, 200)
        data_he = json.loads(resp_he.data)
        self.assertEqual(data_he["query_type"], "Homomorphic Encryption (Paillier)")
        self.assertIn("aggregation", data_he)
        self.assertEqual(data_he["aggregation"]["true_sum"], sum([72, 75, 80, 68]))
        
    def test_digital_twin_telemetry(self):
        """Test GET and POST actions for digital twin metrics"""
        # GET status
        resp_get = self.app.get("/api/federated/digital_twin")
        self.assertEqual(resp_get.status_code, 200)
        data_get = json.loads(resp_get.data)
        self.assertIn("routing_latency_ms", data_get)
        
        # POST tick
        resp_post = self.app.post("/api/federated/digital_twin")
        self.assertEqual(resp_post.status_code, 200)
        data_post = json.loads(resp_post.data)
        self.assertIn("active_pods", data_post)
        
    def test_sync_device_trust(self):
        """Test device reputation global sync route"""
        admin_token = self.get_jwt_token("admin_system", "Admin")
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        resp = self.app.post("/api/federated/device/sync", json={
            "device_id": "ECG_1000",
            "local_score": 85.0
        }, headers=headers)
        
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["device_id"], "ECG_1000")
        self.assertIn("sync_status", data)

if __name__ == "__main__":
    unittest.main()
