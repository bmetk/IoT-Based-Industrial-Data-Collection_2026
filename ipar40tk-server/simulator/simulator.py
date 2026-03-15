import time
from mqtt_publisher import publish
import machine_model as model

def simulate_machine(machine_id):

    while True:

        temp = model.temperature()
        rpm = model.rpm()
        cur = model.current()
        vib = model.vibration()

        publish(f"factory/{machine_id}/temperature/mlx90614/tempC", temp)

        publish(f"factory/{machine_id}/speed/m0c70t3/rpm", rpm)

        publish(f"factory/{machine_id}/current/zmct103c/amp", cur)

        publish(f"factory/{machine_id}/vibration/mpu9250/vibX", vib)
        publish(f"factory/{machine_id}/vibration/mpu9250/vibY", vib)
        publish(f"factory/{machine_id}/vibration/mpu9250/vibZ", vib)

        time.sleep(1)