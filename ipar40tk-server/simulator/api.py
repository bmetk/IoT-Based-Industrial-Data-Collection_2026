from fastapi import FastAPI
import threading
from simulator import simulate_machine

app = FastAPI()

machines = {}

@app.post("/start/{machine_id}")
def start_machine(machine_id: str):

    if machine_id in machines:
        return {"status": "already running"}

    stop_event = threading.Event()

    thread = threading.Thread(
        target=simulate_machine,
        args=(machine_id, stop_event),
        daemon=True
    )

    thread.start()

    machines[machine_id] = {
        "thread": thread,
        "stop_event": stop_event
    }

    return {"status": "started", "machine": machine_id}


@app.post("/stop/{machine_id}")
def stop_machine(machine_id: str):

    if machine_id not in machines:
        return {"status": "not running"}

    machines[machine_id]["stop_event"].set()

    del machines[machine_id]

    return {"status": "stopped", "machine": machine_id}