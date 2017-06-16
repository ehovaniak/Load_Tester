from tkinter import *
import matplotlib.pyplot as plt
import numpy as np
import datetime
import time
import serial
import serial.tools.list_ports
import itertools
import csv
import tkinter.filedialog

class Application(Frame):
    def __init__(self, master=None):
        self.device = None
        self.good_connection = self.establish_connection()

        if self.good_connection == True:
            Frame.__init__(self, master)
            self.master.grid()
            self.master.title("Load Line Tester")
            self.master.resizable(width=False, height=False)
            self.master.geometry('400x700')

            for r in range(2):
                self.master.rowconfigure(r, weight=1)
            for c in range(1):
                self.master.columnconfigure(c, weight=1)

            self.resistor_discrete = [200.0, 400.0, 800.0, 1604.0, 3196.0, 6396.0, 12788.7, 25575.0, 51150.0]
            self.busTimes = [140, 204, 332, 588, 1100, 2116, 4156, 8244]
            self.shuntTimes = [140, 204, 332, 588, 1100, 2116, 4156, 8244]
            self.numAvgs = [1, 4, 16, 64, 128, 256, 512, 1024]
            self.voltageLSB = 0.00125
            self.maxCal = 32768
            self.res_list = self.resistor_options()
            self.steps = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

            self.create_commands_dict()
            self.create_variables()
            #self.get_board_default()

            self.make_frames()
            self.config_autoFrame()
            self.config_debugFrame()

    def create_variables(self):
        self.deviceCal = IntVar()
        self.deviceAvgs = IntVar()
        self.deviceShuntTime = IntVar()
        self.deviceBusTime = IntVar()
        self.deviceBusVolt = DoubleVar()
        self.deviceShuntCurrent = DoubleVar()

        self.filename = StringVar()

        self.boardRev = StringVar()
        self.boardRev.set('Rev 0')
        #self.get_device(self.commands['GET FW VERSION'])

        self.appVersion = StringVar()
        self.appVersion.set('1.0')

        self.sliderControl = IntVar()
        self.sliderControl.set(len(self.res_list) - 1)
        self.resValue = DoubleVar()
        self.deviceRes = DoubleVar()
        self.get_device(self.commands['GET DEVICE RES'])
        self.resValue.set(self.deviceRes.get())

        self.busTimeVar = IntVar()
        self.get_device(self.commands['GET VBUS TIME'])
        self.busTimeVar.set(self.deviceBusTime.get())

        self.shuntTimeVar = IntVar()
        self.get_device(self.commands['GET VSHUNT TIME'])
        self.shuntTimeVar.set(self.deviceShuntTime.get())

        #self.shuntTimeVar.set(self.shuntTimes[0])

        self.numAvgsVar = IntVar()
        self.get_device(self.commands['GET NUM AVGS'])
        self.numAvgsVar.set(self.deviceAvgs.get())

        self.cal = IntVar()
        self.get_device(self.commands['GET CAL REG'])
        self.cal.set(self.deviceCal.get())

        self.shuntRes = DoubleVar()
        self.get_device(self.commands['GET SHUNT'])

        self.maxI = DoubleVar()
        self.maxI.set(self.calculate_maxI(self.cal.get()))
        self.currentLSB = self.maxI.get() / (2**15)

        self.loggingEnable = IntVar()
        self.loggingEnable.set(0)

        self.stepSize = IntVar()
        self.stepSize.set(1)

        self.delayTime = DoubleVar()
        self.delayTime.set(0.1)

    def calculate_maxI(self, cal):
        maxI = (0.00512 * (2 ** 15)) / (cal * self.shuntRes.get())
        maxI = round(maxI, 3)
        return maxI

    def create_commands_dict(self):
        self.commands = dict()
        self.commands['GET FW VERSION'] = '1F'
        self.commands['GET SHUNT'] = '1S'
        self.commands['SET DEVICE RES'] = '3R'
        self.commands['GET DEVICE RES'] = '4R'
        self.commands['SET CAL REG'] = '5C'
        self.commands['GET CAL REG'] = '6C'
        self.commands['SET NUM AVGS'] = '5A'
        self.commands['GET NUM AVGS'] = '6A'
        self.commands['SET VBUS TIME'] = '5B'
        self.commands['GET VBUS TIME'] = '6B'
        self.commands['SET VSHUNT TIME'] = '5S'
        self.commands['GET VSHUNT TIME'] = '6S'
        self.commands['GET VBUS'] = '60'
        self.commands['GET VSHUNT'] = '61'
        self.commands['GET ISHUNT'] = '62'
        self.commands['GET VBUS VSHUNT'] = '63'
        self.commands['GET VBUS ISHUNT'] = '64'

    def establish_connection(self):
        ports = serial.tools.list_ports.comports()
        status = False
        for port in ports:
            if 'LLT' in port[2]:
                p = port[0]
                index = port[2].index('LLT')
                sn = port[2][index:-1]
                status = True
                break

        if status == False:
            print('No Load Line Tester Connected!')
            return status

        self.device = serial.Serial()
        self.device.port = p
        self.device.baudrate = 230400
        self.device.parity = serial.PARITY_NONE
        self.device.stopbits = serial.STOPBITS_ONE
        self.device.bytesize = serial.EIGHTBITS
        self.device.timeout = 0.5
        self.device.write_timeout = 0.5
        self.deviceSN = StringVar()
        self.deviceSN.set('0001')
        #self.deviceSN.set(sn)

        try:
            self.device.open()
        except serial.SerialException:
            print('Error opening port!')
            return False
        time.sleep(0.1)

        self.device.setDTR(False)
        time.sleep(0.1)
        self.device.setDTR(True)
        time.sleep(0.1)
        self.device.setDTR(False)
        time.sleep(0.1)

        self.device.flushInput()
        print("Connected to '%s'" % (self.deviceSN.get()))

        return status

    def resistor_options(self):
        binary = itertools.product([0, 1], repeat=len(self.resistor_discrete))
        binary = list(binary)
        values = []
        for i in range(1, len(binary)):
            value = 0.0
            for j in range(len(self.resistor_discrete)):
                value += (1.0 / self.resistor_discrete[j]) * binary[i][j]
            value = 1.0 / value
            values.append(value)

        values.append(np.float("inf"))

        return sorted(values)

    def get_connection_status(self):
        return self.good_connection

    def calculate_res(self, state):
        value = 0.0
        for i in range(len(self.resistor_discrete)):
            value += (1.0 / self.resistor_discrete[i]) * int(state[i])

        if value == 0.0:
            return np.float("inf")

        return 1.0 / value

    def make_frames(self):
        self.autoFrame = Frame(self.master, bd=2, relief=GROOVE)
        self.autoFrame.grid(row=0, column=0, sticky=W+E+N+S)
        self.debugFrame = Frame(self.master, bd=2, relief=GROOVE)
        self.debugFrame.grid(row=1, column=0, sticky=W+E+N+S)

        for r in range(10):
            self.autoFrame.rowconfigure(r, weight=1)
            self.debugFrame.rowconfigure(r, weight=1)
        for c in range(10):
            self.autoFrame.columnconfigure(c, weight=1)
            self.debugFrame.columnconfigure(c, weight=1)

    def config_autoFrame(self):
        self.filenameLabel = Label(self.autoFrame, text='Filename:')
        self.filenameLabel.grid(row=7, column=0)
        self.filenameEntry = Entry(self.autoFrame, textvariable=self.filename, bg='white', state=DISABLED)
        self.filenameEntry.grid(row=7, column=1)

        self.title = Label(self.autoFrame, text='Variable Load Testing Utility', bg='orange', width=400)
        self.title.place(relx=0.5, rely=0.1, anchor=CENTER)

        self.boardRevLabel1 = Label(self.autoFrame, textvariable=self.boardRev, bg='white')
        self.boardRevLabel1.grid(row=4, column=1)
        self.boardRevLabel2 = Label(self.autoFrame, text='Board Rev:')
        self.boardRevLabel2.grid(row=3, column=1)

        self.boardSNLabel = Label(self.autoFrame, text='Board SN:')
        self.boardSNLabel.grid(row=3, column=0)
        self.boardSNLabel = Label(self.autoFrame, textvariable=self.deviceSN, bg='white')
        self.boardSNLabel.grid(row=4, column=0)

        self.appVersionLabel1 = Label(self.autoFrame, text='App Version:')
        self.appVersionLabel1.grid(row=3, column=2)
        self.appVersionLabel2 = Label(self.autoFrame, textvariable=self.appVersion, bg='white')
        self.appVersionLabel2.grid(row=4, column=2)

        self.shuntResLabel = Label(self.autoFrame, text="Shunt (Ohms):")
        self.shuntResLabel.grid(row=3, column=3)
        self.shuntResLabelVal = Label(self.autoFrame, textvariable=self.shuntRes, bg='white')
        self.shuntResLabelVal.grid(row=4, column=3)

        self.loggingEnableLabel = Label(self.autoFrame, text="Logging:")
        self.loggingEnableLabel.grid(row=6, column=0)
        self.loggingEnableCheck = Checkbutton(self.autoFrame, variable=self.loggingEnable,
                                              command=self.enable_logging)
        self.loggingEnableCheck.grid(row=6, column=1)


        self.delayTimeLabel = Label(self.autoFrame, text="Delay Time (s): ")
        self.delayTimeLabel.grid(row=6, column=2)
        self.delayTimeEntry = Entry(self.autoFrame, textvariable=self.delayTime, bg='white')
        self.delayTimeEntry.grid(row=6, column=3)


        self.stepSizeLabel = Label(self.autoFrame, text="Step Size: ")
        self.stepSizeLabel.grid(row=7, column=2)
        self.stepSizeEntry = OptionMenu(self.autoFrame, self.stepSize, *self.steps)
        self.stepSizeEntry.grid(row=7, column=3)

        self.runTestButton = Button(self.autoFrame, text="Run Test", command=self.run_test)
        self.runTestButton.place(relx=0.5, rely=0.9, anchor=CENTER)

    def config_debugFrame(self):
        self.debugTitle = Label(self.debugFrame, text='Manual Settings', bg='white')
        self.debugTitle.place(relx=0.5, rely=0.05, anchor=CENTER)

        self.sliderResistor = Scale(self.debugFrame, from_=0, to=len(self.res_list) - 1, variable=self.sliderControl,
                                    orient=HORIZONTAL, showvalue=0, command=self.slider_update, length=400,
                                    sliderlength=15, takefocus=0)

        self.sliderResistor.grid(row=2, column=0, columnspan=3)

        self.rightButton = Button(self.debugFrame, text='+', command=self.go_right)
        self.rightButton.grid(row=3, column=2)
        self.leftButton = Button(self.debugFrame, text='-', command=self.go_left)
        self.leftButton.grid(row=3, column=0)
        self.sliderValue = Label(self.debugFrame, textvariable=self.resValue, relief=RAISED)
        self.sliderValue.grid(row=3, column=1)

        self.busTimeDrop = OptionMenu(self.debugFrame, self.busTimeVar, *self.busTimes)
        self.busTimeDrop.grid(row=6, column=0)
        self.busTimeLabel = Label(self.debugFrame, text='Bus Conversion (us):', bg='white')
        self.busTimeLabel.grid(row=5, column=0)

        self.shuntTimeDrop = OptionMenu(self.debugFrame, self.shuntTimeVar, *self.shuntTimes)
        self.shuntTimeDrop.grid(row=6, column=1)
        self.shuntTimeLabel = Label(self.debugFrame, text='Shunt Conversion (us):', bg='white')
        self.shuntTimeLabel.grid(row=5, column=1)

        self.numAvgsDrop = OptionMenu(self.debugFrame, self.numAvgsVar, *self.numAvgs)
        self.numAvgsDrop.grid(row=6, column=2)
        self.numAvgsLabel = Label(self.debugFrame, text='Num Averages:', bg='white')
        self.numAvgsLabel.grid(row=5, column=2)

        self.maxIEntry = Entry(self.debugFrame, textvariable=self.maxI, bg='white')
        self.maxIEntry.grid(row=7, column=1)
        self.maxILabel = Label(self.debugFrame, text="Max Current (A):")
        self.maxILabel.grid(row=7, column=0)
        self.calEntry = Entry(self.debugFrame, textvariable=self.cal, bg='white', state='readonly')
        self.calEntry.grid(row=8, column=1)
        self.calLabel = Label(self.debugFrame, text="Calibration Reg:")
        self.calLabel.grid(row=8, column=0)
        self.calButton = Button(self.debugFrame, text="Calculate Calibration", command=self.calculate_cal,
                                relief=RAISED)
        self.calButton.grid(row=8, column=2)

        self.updateDeviceButton = Button(self.debugFrame, text="Update Device", command=self.update_device,
                                         relief=RAISED)
        self.updateDeviceButton.grid(row=9, column=1)
        self.updateResistanceButton = Button(self.debugFrame, text="Set Resistance", command=self.set_res,
                                             relief=RAISED)
        self.updateResistanceButton.grid(row=4, column=1)

        self.getVbusIshuntButton = Button(self.debugFrame, text='Get VBus & Ishunt',
                                          command=lambda: self.get_device(self.commands['GET VBUS ISHUNT']))
        self.getVbusIshuntButton.grid(row=12, column=2)
        self.getVbusIshuntLabelV = Label(self.debugFrame, textvariable=self.deviceBusVolt, bg='white')
        self.getVbusIshuntLabelV.grid(row=12, column=0)
        self.getVbusIshuntLabelI = Label(self.debugFrame, textvariable=self.deviceShuntCurrent, bg='white')
        self.getVbusIshuntLabelI.grid(row=12, column=1)

        self.vbusLabel = Label(self.debugFrame, text='Bus (V):')
        self.vbusLabel.grid(row=11, column=0)
        self.currentLabel = Label(self.debugFrame, text='Current (A):')
        self.currentLabel.grid(row=11, column=1)

    def res_int_to_hex(self, num):
        hexRes = hex(num).upper()[2:]
        while len(hexRes) < 4:
            hexRes = '0' + hexRes
        newHexRes = ''
        for i in range(len(hexRes)):
            newHexRes = newHexRes + hex(~int(hexRes[i], 16) + 16).upper()[2:]
        binaryRes = bin(int(newHexRes, 16))[2:]
        binaryRes = list(binaryRes)
        for i in range(len(binaryRes)):
            if i < 7:
                binaryRes[i] = '0'
        byteLow = binaryRes[8:]
        byteHigh = binaryRes[0:8]
        newBinaryRes = byteHigh[::-1] + byteLow[::-1]
        newBinaryRes = ''.join(newBinaryRes)
        hexRes = hex(int(newBinaryRes, 2)).upper()[2:]
        while len(hexRes) < 4:
            hexRes = '0' + hexRes
        hexRes = self.commands['SET DEVICE RES'] + hexRes

        return hexRes

    def set_res(self):
        hexRes = self.res_int_to_hex(self.sliderControl.get())
        try:
            self.device.write(hexRes.encode('ASCII'))
        except serial.serialutil.SerialException:
            print('Device Disconnected!')
            return

        time.sleep(0.001)
        self.get_device(self.commands['GET DEVICE RES'])
        print('Requested Load (Ohms):\t\t%f' % (round(self.resValue.get(), 2)))
        print('Device Load (Ohms):\t\t\t%f' % (round(self.deviceRes.get(), 2)))
        print()

    def enable_logging(self):
        if self.loggingEnable.get() == 1:
            self.filenameEntry.config(state=NORMAL)
        else:
            self.filenameEntry.config(state=DISABLED)

    def run_test(self):
        plt.close('all')

        self.get_device(self.commands['GET VBUS ISHUNT'])

        data = []
        self.device.write((self.commands['SET DEVICE RES'] + '0000').encode('ASCII'))
        self.get_device(self.commands['GET DEVICE RES'])
        print('Device Load:\t\t%f' % (self.deviceRes.get()))
        for j in range(len(self.res_list) - 2, -1, -self.stepSize.get()):
            hexRes = self.res_int_to_hex(j)
            try:
                self.device.write(hexRes.encode('ASCII'))
                time.sleep(self.delayTime.get())
                self.get_device(self.commands['GET VBUS ISHUNT'])
                self.get_device(self.commands['GET DEVICE RES'])
                print('Device Load:\t\t%f' % (self.deviceRes.get()))
                #print(self.stepSize.get())
                #print(self.delayTime.get())
                temp = [self.deviceRes.get(), self.deviceBusVolt.get(), self.deviceShuntCurrent.get(), self.deviceAvgs.get(), self.deviceBusTime.get(), self.deviceShuntTime.get()]
                data.append(temp)
            except serial.serialutil.SerialException:
                print('Device Disconnected!')
                return

            #print(j)


        self.device.write((self.commands['SET DEVICE RES'] + '0000').encode('ASCII'))

        if self.loggingEnable.get() == 1 and len(data) > 0:
            if len(self.filename.get()) == 0:
                currentDateTime = datetime.datetime.now()
                hour = str(currentDateTime.hour)
                minute = str(currentDateTime.minute)
                second = str(currentDateTime.second)
                year = str(currentDateTime.year)
                day = str(currentDateTime.day)
                month = str(currentDateTime.month)

                if len(hour) < 2:
                    hour = '0' + hour
                if len(minute) < 2:
                    minute = '0' + minute
                if len(second) < 2:
                    second = '0' + second
                if len(day) < 2:
                    day = '0' + day
                if len(month) < 2:
                    month = '0' + month

                filename = 'Load_Test_' + month + day + year + '_' + hour + minute + second + '.csv'
            else:
                filename = self.filename.get() + '.csv'

            with open(filename, 'w', newline='') as file:
                logging = csv.writer(file, delimiter=',')
                logging.writerow(["Resistance (Ohms)", "VBus (V)", "IShunt (A)", "Averages", "VBus Conversion Time (us)", "IShunt Conversion Time (us)"])
                logging.writerows(data)

        if len(data) > 0:
            plt.figure("IV Characteristics")
            plt.title("IV Characteristics")
            temp1 = []
            temp2 = []
            for i in range(1, len(data)):
                temp1.append(data[i][1])
                temp2.append(data[i][2])
            plt.plot(temp1, temp2)
            plt.xlabel('Voltage (V)')
            plt.ylabel('Current (A)')
            plt.show()

    def slider_update(self, *args):
        if args[0] == str(len(self.res_list) - 1):
            self.resValue.set(np.float("inf"))
        else:
            self.resValue.set(round(self.res_list[int(args[0])], 2))

    def go_right(self):
        index = self.sliderControl.get()
        if index < len(self.res_list) - 1:
            index += 1
            self.sliderControl.set(index)
            if index == len(self.res_list) - 1:
                self.resValue.set(np.float("inf"))
            else:
                self.resValue.set(round(self.res_list[index], 2))

    def go_left(self):
        index = self.sliderControl.get()
        if index > 0:
            index -= 1
            self.sliderControl.set(index)
            self.resValue.set(round(self.res_list[index], 2))

    def calculate_cal(self):
        currentLSB = self.maxI.get() / (2**15)
        cal = int(0.00512 / (currentLSB * self.shuntRes.get()))
        if cal >= self.maxCal:
            maxIReset = self.calculate_maxI(self.cal.get())
            self.maxI.set(maxIReset)
            print('Calibration Register overflow! Max Current is too small!')
            print()
            return

        self.currentLSB = currentLSB
        self.cal.set(cal)

    def get_device(self, cmd):
        try:
            self.device.write(cmd.encode('ASCII'))
            read = self.device.readline().decode('ASCII')
        except serial.serialutil.SerialException:
            print('Device Disconnected!')
            return

        read = read.strip('\r\n')

        if read == '<< BAD COMMAND! >>':
            #print(cmd)
            print('<< BAD COMMAND! >>')
            return
        elif not len(read) > 0:
            print('Invalid Receipt! Check Device FW')
            return
        elif cmd == self.commands['GET FW VERSION']:
            self.boardRev.set(read)
        elif cmd == self.commands['GET SHUNT']:
            self.shuntRes.set(float(read))
        elif cmd == self.commands['GET VBUS ISHUNT']:
            read1 = read[0:4]
            read2 = read[5:]
            read1 = int(read1, 16)
            read2 = int(read2, 16)
            self.deviceBusVolt.set(read1 * self.voltageLSB)
            self.deviceShuntCurrent.set(read2 * self.currentLSB)
        else:
            read = int(read, 16)

            if cmd == self.commands['GET NUM AVGS']:
                self.deviceAvgs.set(read)
            elif cmd == self.commands['GET VBUS TIME']:
                self.deviceBusTime.set(read)
            elif cmd == self.commands['GET CAL REG']:
                self.deviceCal.set(read)
            elif cmd == self.commands['GET VSHUNT TIME']:
                self.deviceShuntTime.set(read)
            elif cmd == self.commands['GET VBUS']:
                self.deviceBusVolt.set(read * self.voltageLSB)
            elif cmd == self.commands['GET ISHUNT']:
                self.deviceShuntCurrent.set(read * self.currentLSB)
            elif cmd == self.commands['GET DEVICE RES']:
                binary = bin(read)[2:]
                while len(binary) < 16:
                    binary = '0' + binary
                binary = binary[0] + (binary[8:])[::-1]
                read = round(self.calculate_res(binary), 2)
                self.deviceRes.set(read)

    def update_device(self):
        cal = hex(self.cal.get()).upper()[2:]
        while len(cal) < 4:
            cal = '0' + cal
        cal = self.commands['SET CAL REG'] + cal

        avg = hex(self.numAvgsVar.get()).upper()[2:]
        while len(avg) < 4:
            avg = '0' + avg
        avg = self.commands['SET NUM AVGS'] + avg

        busTime = hex(self.busTimeVar.get()).upper()[2:]
        while len(busTime) < 4:
            busTime = '0' + busTime
        busTime = self.commands['SET VBUS TIME'] + busTime

        shuntTime = hex(self.shuntTimeVar.get()).upper()[2:]
        while len(shuntTime) < 4:
            shuntTime = '0' + shuntTime
        shuntTime = self.commands['SET VSHUNT TIME'] + shuntTime

        try:
            self.device.write(cal.encode('ASCII'))
            time.sleep(0.001)
            self.get_device(self.commands['GET CAL REG'])
            print('New Cal Register:\t\t\t\t%s' % self.cal.get())
            print('Device Cal Register:\t\t\t%s' % self.deviceCal.get())
            print()
            time.sleep(0.001)

            self.device.write(avg.encode('ASCII'))
            time.sleep(0.001)
            self.get_device(self.commands['GET NUM AVGS'])
            print('New Avg Setting:\t\t\t\t%d' % self.numAvgsVar.get())
            print('Device Avg Setting:\t\t\t\t%d' % self.deviceAvgs.get())
            print()
            time.sleep(0.001)

            self.device.write(busTime.encode('ASCII'))
            time.sleep(0.001)
            self.get_device(self.commands['GET VBUS TIME'])
            print('New Bus Conversion Time:\t\t%d' % self.busTimeVar.get())
            print('Device Bus Conversion Time:\t\t%d' % self.deviceBusTime.get())
            print()
            time.sleep(0.001)

            self.device.write(shuntTime.encode('ASCII'))
            time.sleep(0.001)
            self.get_device(self.commands['GET VSHUNT TIME'])
            print('New Shunt Conversion Time:\t\t%d' % self.shuntTimeVar.get())
            print('Device Shunt Conversion Time:\t%d' % self.deviceShuntTime.get())
            print()
        except serial.serialutil.SerialException:
            print('Device Disconnected!')
            return

    def callback(self):
        try:
            self.device.write((self.commands['SET DEVICE RES'] + '0000').encode('ASCII'))
            self.device.close()
            plt.close('all')
            self.master.destroy()
        except serial.serialutil.SerialException:
            self.device.close()
            plt.close('all')
            self.master.destroy()

if __name__ == "__main__":
    root = Tk()
    app = Application(master=root)
    root.protocol("WM_DELETE_WINDOW", app.callback)
    if app.get_connection_status() == True:
        app.mainloop()
    else:
        print('Program Terminated')