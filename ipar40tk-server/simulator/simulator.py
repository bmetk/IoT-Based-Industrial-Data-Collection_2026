import time
from mqtt_publisher import publish
import machine_model as model

def simulate_machine(machine_id, stop_event, config):

    while not stop_event.is_set():

        rpm_mode = config["rpm_mode"]
        wear = config["wear"]

        rpm = model.get_rpm_value(rpm_mode)

        temp = model.temperature(rpm, wear)
        cur = model.current(rpm, wear)

        publish(f"factory/{machine_id}/temperature/mlx90614/tempC", temp)
        publish(f"factory/{machine_id}/speed/m0c70t3/rpm", rpm)
        publish(f"factory/{machine_id}/current/zmct103c/amp", cur)

        publish(f"factory/{machine_id}/vibration/mpu9250/vibX", model.vibration(rpm, wear))
        publish(f"factory/{machine_id}/vibration/mpu9250/vibY", model.vibration(rpm, wear))
        publish(f"factory/{machine_id}/vibration/mpu9250/vibZ", model.vibration(rpm, wear))

        time.sleep(1)