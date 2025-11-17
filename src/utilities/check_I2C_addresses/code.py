import board
import busio
import time

# Use the same pins you are using in your function
# Example for a Pico: GP21 for SCL, GP20 for SDA
I2C_SCL_PIN = board.GP17 
I2C_SDA_PIN = board.GP16

i2c = busio.I2C(I2C_SCL_PIN, I2C_SDA_PIN)

while not i2c.try_lock():
    pass

print("I2C addresses found:")
print([hex(device_address) for device_address in i2c.scan()])

i2c.unlock()
