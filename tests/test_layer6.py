"""
Layer 6 Automated DevOps, Kubernetes Orchestration, Observability, and Chaos Verification Test Suite
Tests plain-text Prometheus metrics exporter, chaos endpoints, RBAC triggers,
Dockerfiles existence, Kubernetes configuration syntax, and compose specifications.
"""

import os
import sys
import json
import yaml
import unittest
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from blockchain.cloud_gateway import cloud_security_gateway


class TestLayer6DevOpsInfrastructure(unittest.TestCase):
    
    def setUp(self):
        # Flask test client
        self.client = app.test_client()

    def test_01_metrics_endpoint_format(self):
        """Verify plain-text Prometheus exporter metrics route exists and returns compliant format"""
        print("\n☸️  Running Layer 6 Test: Prometheus Metrics Exporter...")
        
        # Hit metrics route
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/plain")
        
        content = response.data.decode("utf-8")
        
        # Verify standard HELP and TYPE comments exist
        self.assertIn("# HELP iomt_patients_total", content)
        self.assertIn("# TYPE iomt_patients_total", content)
        
        self.assertIn("# HELP iomt_trust_score_average", content)
        self.assertIn("# TYPE iomt_trust_score_average", content)
        
        self.assertIn("# HELP iomt_blockchain_health_score_percent", content)
        self.assertIn("# TYPE iomt_blockchain_health_score_percent", content)
        
        self.assertIn("# HELP iomt_blockchain_blocks_total", content)
        self.assertIn("# TYPE iomt_blockchain_blocks_total", content)
        
        # Verify metric keys are outputted
        self.assertIn("iomt_patients_total", content)
        self.assertIn("iomt_trust_score_average", content)
        self.assertIn("iomt_blockchain_health_score_percent", content)
        self.assertIn("iomt_blockchain_blocks_total", content)
        self.assertIn("iomt_blockchain_tampered_total", content)
        print("   Prometheus plain-text scraping endpoint verified compliant.")

    def test_02_chaos_trigger_auth_guard(self):
        """Verify chaos trigger API denies access to anonymous or non-admin roles"""
        print("\n☸️  Running Layer 6 Test: Chaos Auth Guards...")
        
        # Case 1: Anonymous request
        response_anon = self.client.post("/api/chaos/trigger", json={"type": "crash"})
        self.assertEqual(response_anon.status_code, 401)
        
        # Case 2: Nurse role (Forbidden)
        token_nurse = cloud_security_gateway.generate_jwt_token("nurse_rohan", "Nurse")
        headers_nurse = {"Authorization": f"Bearer {token_nurse}"}
        response_nurse = self.client.post("/api/chaos/trigger", json={"type": "crash"}, headers=headers_nurse)
        self.assertEqual(response_nurse.status_code, 403)
        
        # Case 3: Researcher role (Forbidden)
        token_research = cloud_security_gateway.generate_jwt_token("researcher_bob", "Researcher")
        headers_research = {"Authorization": f"Bearer {token_research}"}
        response_research = self.client.post("/api/chaos/trigger", json={"type": "crash"}, headers=headers_research)
        self.assertEqual(response_research.status_code, 403)
        print("   Role-Based access validation blocked unauthorized chaos triggers.")

    @patch("os._exit")
    def test_03_chaos_trigger_crash_simulation(self, mock_exit):
        """Verify Admin role can simulate pod crash (mocking os._exit to prevent test crash)"""
        print("\n☸️  Running Layer 6 Test: Crash Chaos Trigger...")
        
        token_admin = cloud_security_gateway.generate_jwt_token("admin_system", "Admin")
        headers_admin = {"Authorization": f"Bearer {token_admin}"}
        
        # Hit trigger crash
        response = self.client.post("/api/chaos/trigger", json={"type": "crash"}, headers=headers_admin)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        self.assertIn("Crash injected", response.get_json()["message"])
        
        # Wait a short moment to let thread run (mocked os._exit shouldn't kill process)
        import time
        time.sleep(0.6)
        
        self.assertTrue(mock_exit.called)
        self.assertEqual(mock_exit.call_args[0][0], 1)
        print("   Crash simulation correctly invoked exit sequence (os._exit(1)).")

    def test_04_chaos_trigger_cpu_spike(self):
        """Verify Admin role can trigger dynamic CPU load spikes"""
        print("\n☸️  Running Layer 6 Test: CPU Leak Chaos Trigger...")
        
        token_admin = cloud_security_gateway.generate_jwt_token("admin_system", "Admin")
        headers_admin = {"Authorization": f"Bearer {token_admin}"}
        
        # Hit trigger CPU spike
        response = self.client.post("/api/chaos/trigger", json={"type": "cpu_leak"}, headers=headers_admin)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        self.assertIn("CPU load spike injected", response.get_json()["message"])
        print("   CPU leak simulation successfully initiated background CPU spikes.")

    def test_05_kubernetes_specs_yaml_syntax(self):
        """Verify YAML validation and configuration files syntax of Kubernetes manifests"""
        print("\n☸️  Running Layer 6 Test: Kubernetes YAML Syntax...")
        
        k8s_files = ["k8s-deployment.yaml", "k8s-configmap.yaml", "k8s-secret.yaml"]
        
        for filename in k8s_files:
            self.assertTrue(os.path.exists(filename), f"{filename} does not exist!")
            with open(filename, "r") as f:
                try:
                    # YAML can have multiple documents separated by ---
                    docs = yaml.safe_load_all(f)
                    for doc in docs:
                        if doc:
                            self.assertIsInstance(doc, dict)
                except yaml.YAMLError as e:
                    self.fail(f"YAML parsing failed on {filename}: {e}")
                    
        print("   Kubernetes deployment, secret, and configmap YAML files validated.")

    def test_06_dockerfiles_and_compose_existence(self):
        """Verify Dockerfiles and Docker Compose files are present and valid"""
        print("\n☸️  Running Layer 6 Test: Containerization Configurations...")
        
        self.assertTrue(os.path.exists("Dockerfile"))
        self.assertTrue(os.path.exists("Dockerfile.mqtt"))
        self.assertTrue(os.path.exists("docker-compose.yml"))
        
        # Verify docker-compose.yml is valid YAML
        with open("docker-compose.yml", "r") as f:
            try:
                compose_data = yaml.safe_load(f)
                self.assertIn("services", compose_data)
                self.assertIn("backend", compose_data["services"])
                self.assertIn("simulator", compose_data["services"])
                self.assertIn("mqtt-broker", compose_data["services"])
            except yaml.YAMLError as e:
                self.fail(f"docker-compose.yml is not a valid YAML: {e}")
                
        print("   Dockerfile configurations and compose configurations verified.")


if __name__ == "__main__":
    unittest.main()
