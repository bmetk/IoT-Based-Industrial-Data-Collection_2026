from fastapi import FastAPI
import threading
from simulator import simulate_machine

app = FastAPI()

machines = {}
lock = threading.Lock()

# Start machine simulation in a separate thread for each machine ID
@app.post("/start/{machine_id}")
def start_machine(machine_id: str, rpm_mode: str = "low", wear: float = 0.0, load: str = "idle", fault: str = None, fault_intensity: float = 0.0, wear_rate: float = 0.002):

    with lock:
        if machine_id in machines:
            thread = machines[machine_id]["thread"]
            if thread.is_alive():
                return {"status": "already running"}
            else:
                del machines[machine_id]

        stop_event = threading.Event()

        config = {
            "rpm_mode": rpm_mode,
            "load": load,
            "wear": wear,
            "fault": fault,
            "fault_intensity": fault_intensity,
            "wear_rate": wear_rate
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
        thread = machines[machine_id]["thread"]

    thread.join(timeout=5)

    if thread.is_alive():
        return {"status": "failed to stop cleanly"}

    with lock:
        del machines[machine_id]

    return {"status": "stopped", "machine": machine_id}

# Update simulation configuration for a given machine ID
@app.post("/config/{machine_id}")
def update_config(machine_id: str, rpm_mode: str, load: str, wear: float = 0.0, fault: str = None, fault_intensity: float = 0.0, wear_rate: float = 0.0005):

    with lock:
        if machine_id not in machines:
            return {"status": "not running"}

        machines[machine_id]["config"]["rpm_mode"] = rpm_mode
        machines[machine_id]["config"]["wear"] = wear
        machines[machine_id]["config"]["load"] = load
        machines[machine_id]["config"]["fault"] = fault
        machines[machine_id]["config"]["fault_intensity"] = fault_intensity
        machines[machine_id]["config"]["wear_rate"] = wear_rate
    return {
        "status": "updated",
        "rpm_mode": rpm_mode,
        "wear": wear,
        "load": load,
        "fault": fault,
        "wear_rate": wear_rate
    }

@app.get("/status/{machine_id}")
def status(machine_id: str):
    if machine_id in machines:
        return {"running": True}
    return {"running": False}

@app.post("/reset/{machine_id}")
def reset(machine_id: str):
    with lock:
        if machine_id in machines:
            machines[machine_id]["config"]["wear"] = 0.0
            machines[machine_id]["config"]["fault"] = None
    return {"status": "reset"}