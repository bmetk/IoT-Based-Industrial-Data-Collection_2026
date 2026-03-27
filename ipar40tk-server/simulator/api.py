from fastapi import FastAPI
import threading
from simulator import simulate_machine

app = FastAPI()

machines = {}
lock = threading.Lock()

# Start machine simulation in a separate thread for each machine ID
@app.post("/start/{machine_id}")
def start_machine(machine_id: str):

    with lock:
        if machine_id in machines:
            return {"status": "already running"}

        stop_event = threading.Event()

        config = {
            "rpm_mode": "low",
            "wear": 0.0
        }

        thread = threading.Thread(
            target=simulate_machine,
            args=(machine_id, stop_event, config),
            daemon=True
        )

        thread.start()

        machines[machine_id] = {
            "thread": thread,
            "stop_event": stop_event,
            "config": config
        }

    return {"status": "started", "machine": machine_id}

# Stop machine simulation for a given machine ID
@app.post("/stop/{machine_id}")
def stop_machine(machine_id: str):

    with lock:
        if machine_id not in machines:
            return {"status": "not running"}

        machines[machine_id]["stop_event"].set()
        del machines[machine_id]

    return {"status": "stopped", "machine": machine_id}

# Update simulation configuration for a given machine ID
@app.post("/config/{machine_id}")
def update_config(machine_id: str, rpm_mode: str,  wear: float = 0.0):

    with lock:
        if machine_id not in machines:
            return {"status": "not running"}

        machines[machine_id]["config"]["rpm_mode"] = rpm_mode
        machines[machine_id]["config"]["wear"] = wear

    return {
        "status": "updated",
        "rpm_mode": rpm_mode,
        "wear": wear
    }