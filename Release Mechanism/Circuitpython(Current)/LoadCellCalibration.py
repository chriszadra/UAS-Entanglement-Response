#List of different calibration weights you wish to use
masses = [0.5,1,5,10]



import time
import board
import busio
import digitalio
from cedargrove_nau7802 import NAU7802
import numpy as np
i2c = busio.I2C(board.SCL, board.SDA)
LoadCell = NAU7802(i2c)
LoadCell.gain = 1

print("LOAD CELL CALIBRATION ROUTINE")
print("Remove all weight from the hook")
time.sleep(3)
print("Taking 0kg reading")
zeroMass = 0
for i in range(10):
    time.sleep(0.1)
    zeroMass += LoadCell.read()*0.1

ivals = [zeroMass]

for i in masses:
    print("Place ",str(i),"kg mass on the hook")
    time.sleep(10)
    print("Taking",str(i),"kg measurment")
    ival = 0
    for i in range(10):
        time.sleep(0.15)
        ival += LoadCell.read()*0.1
    ivals = ivals+[ival]
    
LA = 0
for i in range(len(masses)):
    print(str(masses[i]),":",ivals[i])
    LA += ((masses[i]*9.81)/ivals[i])*(1/len(masses))

LB = zeroMass

print("Calibration numbers: ")
print("LA: ",LA)
print("LB: ",LB)
print("Modify LA, LB in the code.py script at the root of the device to update the values")



#VVVRuns the same code as the main script to let you see if the values are accurate
def LoadtoLoadN(Load):
    LoadN = (Load/LA)-LB
    return LoadN

if not input("send any char to see live load data"):
    while True:
        print(LoadCell.read())
        time.sleep(0.1)

