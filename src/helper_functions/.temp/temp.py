from pathlib import Path
import pygame
import json
from engine.utils.functions.filesystem import read_json_file
from engine.utils.paths import TEMP_DIR
import playsound3
import time

# file_path = Path(r"D:\python\miraa-alternative\src\.temp\Backlight - Ado.json")
# file_path = Path(r"D:\python\miraa-alternative\src\.temp\Mela! - Ryokuoushoku Shakai.json")
file_path = Path(r"D:\python\miraa-alternative\src\.temp\Haikei Shounenyo - Hump Back.json")
# file_path = Path(r"/Users/marb/PycharmProjects/miraa-alternative/src/.ssh_copy_over/花になって - Be a flower - Ryokuoushoku Shakai.json")
# file_path = Path(r"/Users/marb/PycharmProjects/miraa-alternative/src/.temp/sabotage - Ryokuoushoku Shakai.json")

pygame.mixer.init()
data = read_json_file(file_path)
sound = pygame.mixer.Sound(Path(TEMP_DIR / f"{data.get("pre_processing").get("audio_file")}"))
data = data.get("timestamps")
# file_path.write_text(json.dumps(data, indent=4))

sound.set_volume(0.65)
sound.play()

# playsound3.playsound(Path(r"D:\python\miraa-alternative\src\.temp\Ww8oxgqDQSs.wav"), block=False)
start_time = time.time()

last_seg_start = 0
try:
    while True:
        # if time.time() - start_time > data[0].get("end"):
        #     data.pop(0)

        if time.time() - start_time > data[0].get("start") and last_seg_start != data[0].get("start"):
            last_seg_start = data[0].get("start")
            print(data[0]["line"])
            data.pop(0)

        # print(time.time() - start_time)
        time.sleep(0.05)
        # print(time.time() - start_time)
except IndexError:
    print("end of lyrics")
    while True:
        time.sleep(1)



# import torch
#
# print(f"CUDA Available: {torch.cuda.is_available()}")
#
# print(f"GPU Count: {torch.cuda.device_count()}")
#
# if torch.cuda.is_available():
#     print(f"Current Device Name: {torch.cuda.get_device_name(0)}")