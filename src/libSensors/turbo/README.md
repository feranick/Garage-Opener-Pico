#Installation

Choose the board you plan to use. From the corresponding folder, copy the libSensor.mpy in the /lib folder.

#Compilation

RP2040:

`mpy-cross -march=armv6m libSensors.py`

RP2355:
`mpy-cross -march=armv7esm libSensors.py`
