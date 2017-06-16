This repository contains schematics, layout, software, and other data pertaining a siimple load 
testing board I had designed for IV characterization.

This is one of the earliest boards I have designed and manufactured. Load is distrubuted through a 
10-step resistor ladder network. My original implementation adjusts the resistor ladder in a binary 
fashion, allowing for a constant linear increase in current to be drawn from the load. The current 
and voltage are measured by the INA226 IC. Data is managed and transferred over USB to the host 
computer.

I wrote a compaion Python applicaton to interface with the board to adjust load settings manually. I 
also wrote a test function in the app. The test would vary the load from least to greatest and take 
measurements with each load change. Upon completion, the app would plot this data as an IV curve and 
display to the user. The data could also be saved to a .CSV file if desired.
