from pathlib import Path
import json
from engine.utils.functions.filesystem import read_json_file
import playsound3
import time

file_path = Path(r"D:\python\miraa-alternative\src\.temp\test.json")

data = read_json_file(file_path)
file_path.write_text(json.dumps(data, indent=4))

segements = data.get("segments")
print(segements)

playsound3.playsound(Path(r"D:\python\miraa-alternative\src\.temp\aRDURmIYBZ4.wav"), block=False)
start_time = time.time()

last_seg_start = 0

while True:
    if time.time() - start_time > segements[0].get("end"):
        segements.pop(0)

    if time.time() - start_time > segements[0].get("start") and last_seg_start != segements[0].get("start"):
        last_seg_start = segements[0].get("start")
        print(segements[0]["text"])

    # print(time.time() - start_time)
    time.sleep(0.05)

# import torch
#
# print(f"CUDA Available: {torch.cuda.is_available()}")
#
# print(f"GPU Count: {torch.cuda.device_count()}")
#
# if torch.cuda.is_available():
#     print(f"Current Device Name: {torch.cuda.get_device_name(0)}")