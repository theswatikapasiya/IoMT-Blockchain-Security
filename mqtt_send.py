"""
MQTT IoT Simulator
Simulates real IoMT devices sending patient data via MQTT
"""

import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import json
import time
import random
from blockchain.data_generator import patient_generator

# Configuration
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "iot/hospital/patients"
SEND_INTERVAL = 10  # seconds

# Get patient generator
generator = patient_generator

# Create first dataset if needed
try:
    all_patients = generator.get_all_patients()
    if len(all_patients) == 0:
        print("📊 Generating initial patient dataset...")
        generator.create_patient_dataset(20)
        all_patients = generator.get_all_patients()
except:
    print("📊 Generating initial patient dataset...")
    generator.create_patient_dataset(20)
    all_patients = generator.get_all_patients()

print(f"✅ Loaded {len(all_patients)} patients for simulation")

def on_mqtt_connect(client, userdata, flags, rc):
    """Callback for when MQTT client connects"""
    if rc == 0:
        print(f"✅ Connected to MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    else:
        print(f"❌ Connection failed with code: {rc}")

def on_mqtt_disconnect(client, userdata, rc):
    """Callback for when MQTT client disconnects"""
    if rc != 0:
        print(f"⚠️  Unexpected disconnection: {rc}")

def on_mqtt_publish(client, userdata, mid):
    """Callback for when message is published"""
    pass

def simulate_iot_stream():
    """
    Simulate continuous IoT data stream
    Real-world scenario: devices send updates every 10-30 seconds
    """
    print("\n🚀 Starting IoMT Data Stream Simulator...")
    print(f"📡 Broadcasting to: {MQTT_TOPIC}")
    print("Press Ctrl+C to stop\n")
    
    client = mqtt.Client()
    client.on_connect = on_mqtt_connect
    client.on_disconnect = on_mqtt_disconnect
    client.on_publish = on_mqtt_publish
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_start()
        
        sequence = 0
        
        while True:
            try:
                # Select random patient
                patient = random.choice(all_patients)
                
                # Get updated vitals (fully simulated device packet from Layer 1 engine)
                payload = generator.update_patient_vitals(patient["id"])
                payload["sequence"] = sequence
                
                # Publish to MQTT
                result = client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)
                
                if result.rc == 0:
                    print(f"📤 [{sequence}] {patient['id']:6} | HR: {payload['hr']:3}bpm | BP: {payload['bp']:7} | Temp: {payload['temp']}°C")
                    sequence += 1
                else:
                    print(f"❌ Failed to publish: {result.rc}")
                
                time.sleep(SEND_INTERVAL)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"⚠️  Error in stream: {e}")
                time.sleep(2)
        
        print("\n🛑 Stopping IoMT Stream...")
        client.loop_stop()
        client.disconnect()
        print("✅ MQTT Simulator stopped gracefully")
        
    except Exception as e:
        print(f"❌ MQTT Error: {e}")
        client.loop_stop()

def send_single_update(patient_id):
    """Send single patient update"""
    try:
        # Get patient
        patients = generator.get_all_patients()
        patient = next((p for p in patients if p["id"] == patient_id), None)
        
        if not patient:
            print(f"❌ Patient {patient_id} not found")
            return
        
        # Get updated vitals (fully simulated device packet from Layer 1 engine)
        payload = generator.update_patient_vitals(patient_id)
        
        publish.single(
            MQTT_TOPIC,
            json.dumps(payload),
            hostname=MQTT_BROKER,
            port=MQTT_PORT,
            qos=1
        )
        
        print(f"✅ Sent update for {patient['id']}: HR={payload['hr']}, BP={payload['bp']}, Temp={payload['temp']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "single":
        # Send single update
        patient_id = sys.argv[2] if len(sys.argv) > 2 else "PS1000"
        send_single_update(patient_id)
    else:
        # Stream mode (continuous)
        simulate_iot_stream()