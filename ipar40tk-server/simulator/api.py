from fastapi import FastAPI
import threading
from simulator import simulate_machine

app = FastAPI()

machines = {}

@app.post("/start/{machine_id}")

def start_machine(machine_id: str):

    if machine_id in machines:
        return {"status": "already running"}

    thread = threading.Thread(
        target=simulate_machine,
        args=(machine_id,),
        daemon=True
    )

    thread.start()

    machines[machine_id] = thread

    return {"status": "started", "machine": machine_id}


@app.post("/stop/{machine_id}")

def stop_machine(machine_id: str):

    return {"status": "not implemented"}