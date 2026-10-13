import time
import board
import busio
import digitalio
import Jon_rfm95
import struct
import displayio
import terminalio
from i2cdisplaybus import I2CDisplayBus
import adafruit_ssd1306
import adafruit_framebuf


#Manual Switches
#Left Switch Hook; Right Switch Chute
hookSwitch = digitalio.DigitalInOut(board.A0)
hookSwitch.direction = digitalio.Direction.INPUT
hookSwitch.pull = digitalio.Pull.UP
drougeSwitch = digitalio.DigitalInOut(board.A1)
drougeSwitch.direction = digitalio.Direction.INPUT
drougeSwitch.pull = digitalio.Pull.UP

#GUI Buttons
ButtonA = digitalio.DigitalInOut(board.D9)
ButtonA.direction = digitalio.Direction.INPUT
ButtonA.pull = digitalio.Pull.UP
ButtonB = digitalio.DigitalInOut(board.D6)
ButtonB.direction = digitalio.Direction.INPUT
ButtonB.pull = digitalio.Pull.UP
ButtonC = digitalio.DigitalInOut(board.D5)
ButtonC.direction = digitalio.Direction.INPUT
ButtonC.pull = digitalio.Pull.UP

#Screen setup
displayio.release_displays()
i2c = board.I2C()  # uses board.SCL and board.SDA
display = adafruit_ssd1306.SSD1306_I2C(128,32,i2c, addr=0x3C)
display.fill(0)  # Clear the display
display.text("Controller Ready", 18, 16, 1)
display.show()



def splashScreen():
    print(time.monotonic())
    display.fill(0)  # Clear the display
    display.text("Hook: "+str(not hookSwitch.value)+"\nDrouge: "+str(not drougeSwitch.value)+"\nForce:"+Telem, 45, 0, 1)
    display.text("A:XX", 0, 0, 1)
    display.text("B:Menu", 0, 12, 1)
    display.text("C:XX", 0, 25, 1)
    display.fill_rect(39, 0, 1, 32, 1)
    display.show()
    print(time.monotonic())

def dropHook():
    print("Dropping Hook")
    Radio.send(b'h', keep_listening=True)
    
def dropDrouge():
    print("Dropping Drouge")
    Radio.send(b'd', keep_listening=True)
    

def subMenu(title,options):
    subMenuSelect = 0
    display.fill(0)
    display.text(title,15,0,1)
    display.text(str(options[(subMenuSelect-1)%(len(options))]), 0, 8, 1)
    display.text(str(options[(subMenuSelect)%(len(options))]), 5, 16, 1)
    display.text(str(options[(subMenuSelect+1)%(len(options))]), 0, 24, 1)
    display.show()
    time.sleep(0.5)
    while(ButtonB.value):
        if(not ButtonA.value):
            subMenuSelect -=1
            display.fill(0)
            display.text(title,15,0,1)
            display.text(str(options[(subMenuSelect-1)%(len(options))]), 0, 8, 1)
            display.text(str(options[(subMenuSelect)%(len(options))]), 5, 16, 1)
            display.text(str(options[(subMenuSelect+1)%(len(options))]), 0, 24, 1)
            display.show()
        if(not ButtonC.value):
            subMenuSelect +=1
            display.fill(0)
            display.text(title,15,0,1)
            display.text(str(options[(subMenuSelect-1)%(len(options))]), 0, 8, 1)
            display.text(">"+str(options[(subMenuSelect)%(len(options))]), 5, 16, 1)
            display.text(str(options[(subMenuSelect+1)%(len(options))]), 0, 24, 1)
            display.show()
    time.sleep(0.15)
    return options[(subMenuSelect)%(len(options))]

menuSelect = 0
menuItems = ["Drop Force[N]","Drop Tollerence","Moving AVG LEN","Calibrate Loadcell","Toggle Timeout","TimeoutLength[s]","Toggle Telemetry","Exit"]
currentSettings = [50, 200, 10, None, None, 5, None, None]
optionItems = [list(range(0,150)),list(range(0,200)),list(range(0,20)),["Calibrate"],["Disable","Enable"],list(range(2,30)),["Disable","Enable"],[1]]
def menu():
    Radio.send('u,4,D',keep_listening=True)
    time.sleep(0.5)
    menuSelect = 0
    display.fill(0)
    display.text("Menu",50,0,1)
    display.text(menuItems[(menuSelect-1)%(len(menuItems))]+str(currentSettings[(menuSelect-1)%(len(menuItems))]), 0, 8, 1)
    display.text(">"+menuItems[(menuSelect)%(len(menuItems))]+str(currentSettings[(menuSelect)%(len(menuItems))]), 4, 16, 1)
    display.text(menuItems[(menuSelect+1)%(len(menuItems))]+str(currentSettings[(menuSelect+1)%(len(menuItems))]), 0, 24, 1)
    display.show()
    while(not((menuSelect%(len(menuItems)) == len(menuItems)-1) and (not ButtonB.value))):
        if(not ButtonA.value):
            menuSelect -=1
            display.fill(0)
            display.text("Menu",50,0,1)
            display.text(menuItems[(menuSelect-1)%(len(menuItems))]+str(currentSettings[(menuSelect-1)%(len(menuItems))]), 0, 8, 1)
            display.text(">"+menuItems[(menuSelect)%(len(menuItems))]+str(currentSettings[(menuSelect)%(len(menuItems))]), 4, 16, 1)
            display.text(menuItems[(menuSelect+1)%(len(menuItems))]+str(currentSettings[(menuSelect+1)%(len(menuItems))]), 0, 24, 1)
            display.show()
        if(not ButtonC.value):
            menuSelect +=1
            display.fill(0)
            display.text("Menu",50,0,1)
            display.text(menuItems[(menuSelect-1)%(len(menuItems))]+str(currentSettings[(menuSelect-1)%(len(menuItems))]), 0, 8, 1)
            display.text(">"+menuItems[(menuSelect)%(len(menuItems))]+str(currentSettings[(menuSelect)%(len(menuItems))]), 4, 16, 1)
            display.text(menuItems[(menuSelect+1)%(len(menuItems))]+str(currentSettings[(menuSelect+1)%(len(menuItems))]), 0, 24, 1)
            display.show()
        if(not ButtonB.value and not((menuSelect%(len(menuItems)) == len(menuItems)-1))):
            valueToSend = str(subMenu(menuItems[(menuSelect)%(len(menuItems))],optionItems[(menuSelect)%(len(menuItems))]))
            Radio.send('u,'+str((menuSelect)%(len(menuItems)))+","+valueToSend,keep_listening=True)
            currentSettings[(menuSelect)%(len(menuItems))] = valueToSend
            #print("Sent packet:",'u,'+str((menuSelect)%(len(menuItems)))+","+str(subMenu(menuItems[(menuSelect)%(len(menuItems))],optionItems[(menuSelect)%(len(menuItems))])))
            display.fill(0)
            display.text("Menu",50,0,1)
            display.text(menuItems[(menuSelect-1)%(len(menuItems))]+str(currentSettings[(menuSelect-1)%(len(menuItems))]), 0, 8, 1)
            display.text(">"+menuItems[(menuSelect)%(len(menuItems))]+str(currentSettings[(menuSelect)%(len(menuItems))]), 4, 16, 1)
            display.text(menuItems[(menuSelect+1)%(len(menuItems))]+str(currentSettings[(menuSelect+1)%(len(menuItems))]), 0, 24, 1)
            display.show()
            time.sleep(0.25)
    Radio.send('u,4,E',keep_listening=True)

    splashScreen()


#Radio setup
RADIO_FREQ_MHZ=912.34
#The DIO pin is used to tell when a packet has been received
RadioDIO0 = digitalio.DigitalInOut(board.RFM_IO0)
RadioDIO0.direction = digitalio.Direction.INPUT

CS = digitalio.DigitalInOut(board.RFM_CS)
RESET = digitalio.DigitalInOut(board.RFM_RST)
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
Radio = Jon_rfm95.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)

#Radio(LORA) settings
Radio.spreading_factor = 9
Radio.signal_bandwidth = 500000
Radio.coding_rate = 6
Radio.receive()

#RADIO TIMEOUT PULSE FREQUENCY (make value greater then 1 seconds)
timeoutPeriod = 5e9 #nanoseconds

Telem = ""

#Times for bad and fake asynco stuff
keepAliveTime = 0
hookSwitchTime = 0
drougeSwitchTime = 0

splashScreen()
while(True):
    #Manual Switches
    if not hookSwitch.value:
        if hookSwitchTime+(0.5e9)<time.monotonic_ns():
            dropHook()
            splashScreen()
            hookSwitchTime = time.monotonic_ns()
            keepAliveTime = time.monotonic_ns()
    if not drougeSwitch.value:
        if drougeSwitchTime+(0.5e9)<time.monotonic_ns():
            dropDrouge()
            splashScreen()
            drougeSwitchTime = time.monotonic_ns()
            keepAliveTime = time.monotonic_ns()

    if keepAliveTime+(timeoutPeriod-2e9)<time.monotonic_ns():
        Radio.send("t",keep_listening=True)#t is the char used as the keepalive symbol, nothing other then reseting the radio counter should happen when this is sent
        keepAliveTime = time.monotonic_ns()

    if RadioDIO0.value:
        Telem = str(Radio.getLastPacket().decode('utf-8'))
        print(Telem)
        splashScreen()

    if not ButtonB.value:
        menu()
        #changeMode("normal")

