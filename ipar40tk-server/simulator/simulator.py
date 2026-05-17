from logging import config
import time
from mqtt_publisher import publish, publish_vibration
import machine_model as model

def simulate_machine(machine_id, stop_event, config):
    try:
        while not stop_event.is_set():
            try:
                rpm_mode = config["rpm_mode"]
                wear = config["wear"]
                load = config["load"]
                fault = config["fault"]
                fault_intensity = config["fault_intensity"]
                wear_rate = config["wear_rate"]

                rpm = model.get_rpm_value(rpm_mode)

                temp = model.temperature(rpm, wear, load)
                cur = model.current(rpm, wear, load, fault)

                publish(f"factory/{machine_id}/temperature/mlx90614/tempC", temp)
                publish(f"factory/{machine_id}/speed/m0c70t3/rpm", rpm)
                publish(f"factory/{machine_id}/current/zmct103c/amp", cur)

                signal_x = model.vibration_sequence(rpm, wear, load, "vibX", fault, fault_intensity)
                signal_y = model.vibration_sequence(rpm, wear, load, "vibY", fault, fault_intensity)
                signal_z = model.vibration_sequence(rpm, wear, load, "vibZ", fault, fault_intensity)

                for chunk in signal_x:
                    publish_vibration(
                        f"factory/{machine_id}/vibration/mpu9250/vibX",
                        chunk
                    )

                for chunk in signal_y:
                    publish_vibration(
                        f"factory/{machine_id}/vibration/mpu9250/vibY",
                        chunk
                    )

                for chunk in signal_z:
                    publish_vibration(
                        f"factory/{machine_id}/vibration/mpu9250/vibZ",
                        chunk
                    )

            except Exception as e:
                print(f"[SIM ERROR] {machine_id}: {e}")

            time.sleep(1)
            wear += wear_rate
            wear = min(wear, 1.0)
            config["wear"] = wear
    except Exception as e:
        print(f"[FATAL THREAD ERROR] {machine_id}: {e}")