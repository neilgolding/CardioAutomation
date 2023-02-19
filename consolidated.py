import asyncio
import bitstruct
import struct
import warnings
warnings.simplefilter(action="ignore", category=FutureWarning)

from bleak import BleakClient

HR_MEAS = "00002A37-0000-1000-8000-00805F9B34FB"
TM_DATA = "00002acd-0000-1000-8000-00805f9b34fb"
Control_Mach = "00002ad9-0000-1000-8000-00805f9b34fb"
TM_Address = "57:4C:54:19:32:15"
Fenix_Address = "90:F1:57:79:0C:E3"

client_t_glob = None
prev_inc = 0
hval = 0
curinc = 0
incspd0 = 1000
incspd2 = 900
incspd4 = 800
incspd6 = 700
incspd8 = 600
curspd = 0
hr_high = 65
hr_low = 60

async def tm_data_handler(sender, data):
    """Simple notification handler for Heart Rate Measurement."""
    #print("Enter TM Data")
    global curinc
    global curspd
    (instspd_bit,
     avg_spd_bit,
     total_dist_bit,
     incl_bit,
     pos_elev_bit,
     inst_pace_bit,
     avg_pace_bit,
     eng_bit,
     hr_bit,
     met_bit,
     elapsed_time_bit,
     rem_time_bit,
     force_belt_bit) = bitstruct.unpack("b1b1b1b1b1b1b1b1b1b1b1b1b1<", data)
    curspd, = struct.unpack_from("<H", data, 2)

    tot_dist_val, = struct.unpack_from("<H", data, 4)
    curinc, = struct.unpack_from("<h", data, 7)

    #print(f"HR Value: {hr_val} instspd_bit {instspd_bit} avg_speed_bit {avg_spd_bit} total_dist_bit {total_dist_bit} incl_bit {incl_bit} pos_elev_bit {pos_elev_bit} inst_pace_bit {inst_pace_bit} Tot_Dist_Val {tot_dist_val} Inclination {inc_val}")


async def hr_val_handler(sender, data):
    """Simple notification handler for Heart Rate Measurement."""
    #print("HR Measurement raw = {0}: {1}".format(sender, data))
    global hval
    (hr_fmt,
     snsr_detect,
     snsr_cntct_spprtd,
     nrg_expnd,
     rr_int) = bitstruct.unpack("b1b1b1b1b1<", data)
    if hr_fmt:
        hval, = struct.unpack_from("<H", data, 1)
    else:
        hval, = struct.unpack_from("<B", data, 1)


async def tm_manager():
    while True:
        try:
            print("Trying to connect BLE to Treadmill")
            async with BleakClient(TM_Address) as clientT:
                connected = await clientT.is_connected()
                global client_t_glob
                client_t_glob = clientT
                print("Connected to Treadmill".format(connected))
                await clientT.start_notify(TM_DATA, tm_data_handler)
                while True:
                    await asyncio.sleep(1)
        except:
            print("Trying Treadmill connect again/ make sure it's on or restart Treadmill")

async def fenix_manager():
    while True:
        try:
            print("Try BLE Connection to Fenix")
            async with BleakClient(Fenix_Address, timeout=10) as clientF:
                connected = await clientF.is_connected()
                print("Connected to Fenix".format(connected))
                await clientF.start_notify(HR_MEAS, hr_val_handler)
                while True:
                    await asyncio.sleep(1)
        except:
            print ("Trying Fenix connect again - Virtual Run/ exit and re-enter")

async def HR_setter():
    global incspd0, incspd2, incspd4, incspd6, incspd8
    offs = 0
    if hval > hr_high:
        #decrease all speeds and current speed by .2
        offs = -20

    elif hval < hr_low:
        #increase all speeds and current by .2
        offs = 20

    incspd0 = incspd0 + offs
    incspd2 = incspd2 + offs
    incspd4 = incspd4 + offs
    incspd6 = incspd6 + offs
    incspd8 = incspd8 + offs
    asyncio.create_task(speed_setter())


async def speed_setter():
    #incline value is x10 and speed value is x100
    sset = 0
    if curinc == 0:
        sset = incspd0
    elif curinc == 20:
        sset = incspd2
    elif curinc == 40:
        sset = incspd4
    elif curinc == 60:
        sset = incspd6
    elif curinc == 80:
        sset = incspd8
    dta = struct.pack('<BH', 2, sset)
    await client_t_glob.write_gatt_char(Control_Mach, dta, True)
    print(f"Inc: {curinc} Speed: {sset} Hval: {hval}")

async def main():
    global prev_inc
    lhrtime = -waiter*60
    asyncio.create_task(tm_manager())
    asyncio.create_task(fenix_manager())
    while True:
        #print (f"Inc: {curinc} Speed: {curspd} Hval: {hval}")
        if curinc != prev_inc:
            asyncio.create_task(speed_setter())
            prev_inc = curinc
        if (hval > hr_high or hval < hr_low) and lhrtime > 30 and hval > 30:
            asyncio.create_task(HR_setter())
            lhrtime = 0
        await asyncio.sleep(1)
        if lhrtime <= 30:
            lhrtime = lhrtime + 1

hr_high = int(input ("set high HR: "))
hr_low = int(input ("set low HR: "))
waiter = int(input ("How long until start in mins: "))

asyncio.run(main())