import time
import board
import busio
import digitalio
from cedargrove_nau7802 import NAU7802
i2c = busio.I2C(board.SCL, board.SDA)
LoadCell = NAU7802(i2c)
LoadCell.gain = 1
loadLimit = 90
loadTolerance = 5
counter = 0
while(True):
    Load = LoadCell.read()*0.0061-43
    if Load > loadLimit:
        counter += 1
    else:
        counter=0
    if counter > loadTolerance:
            print("Load exceeded limit: ", Load)
    print(counter, Load)
    time.sleep(0.1)