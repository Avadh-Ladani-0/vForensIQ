import json
import random
from datetime import datetime, timedelta

# Parameters
start_date = datetime.strptime("2025-12-01", "%Y-%m-%d")
end_date = datetime.strptime("2025-12-07", "%Y-%m-%d")
time_delta = end_date - start_date
camera_ids = [f"CAM_{i:02}" for i in range(1, 11)]
event_types = ["person_entry", "person_exit", "car_entry", "car_exit", "crowd"]
camera_locations = ["Platform_1", "Platform_2", "Main_hall", "Reception", "Gate_01", "Gate_02", "Gate_03"]
records_count = 100000

dataset = []
for _ in range(records_count):
    # Randomize timestamp within range
    random_seconds = random.randint(0, int(time_delta.total_seconds()))
    timestamp = start_date + timedelta(seconds=random_seconds)
    
    event_type = random.choice(event_types)
    
    if event_type == "crowd":
        head_count = random.randint(1, 50)
        object_id = None
        camera_location = random.choice(["Platform_1", "Platform_2", "Main_hall", "Reception"])
    else:
        head_count = 0
        object_id = str(random.randint(1, 1000))
        if event_type in ["car_entry", "car_exit"]:
            camera_location = random.choice(["Gate_01", "Gate_02", "Gate_03"])
        else:
            camera_location = random.choice(camera_locations)
    
    # Randomize data fields
    record = {
        "timestamp": timestamp.isoformat(),
        "camera_id": random.choice(camera_ids),
        "event_type": event_type,
        "object_id": object_id,
        "confidence": round(random.uniform(0.8, 0.99), 2),
        "camera_location": camera_location,
        "head_count": head_count
    }
    dataset.append(record)
    
# Save to a JSON file
file_name = "logs/entry_exit_fire.json"
with open(file_name, "w") as json_file:
    json.dump(dataset, json_file, indent=2)
print(f"Dataset with {records_count} records has been generated and saved to {file_name}.")