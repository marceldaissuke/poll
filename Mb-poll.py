import dash
from dash import html, dcc, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import serial.tools.list_ports
from pymodbus.client.serial import ModbusSerialClient
from pymodbus.exceptions import ModbusException
import time
import signal
import sys
import os
import logging
import traceback
from datetime import datetime
import csv
import base64
import io
import plotly.graph_objects as go
from collections import deque
import plotly.io as pio
import pandas as pd
from dash.exceptions import PreventUpdate

#version of the github
#version = 0.1.0 functional

# Set up logging
#log_filename = f"modbus_viewer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        #logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ModbusRTUViewer")

MODBUS_CONFIG = {
    'baudrate': 19200,
    'parity': 'N',
    'stopbits': 2,
    'bytesize': 8,
    'timeout': 1,
    'unit_id': 1
}

# Example register map - now includes register type
# Valid types: 'Holding', 'Input', 'Coil', 'Discrete_input

# Example register map - now includes register type and bit definitions
REGISTER_MAP = {
    # Address: {'name': 'Description', 'type': 'Function', 'multiplier': k, 'unit': ''},
    0: {'name': 'Motor control mode', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    1: {'name': 'Motor base frequency', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    2: {'name': 'Motor base voltage', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    3: {'name': 'Motor rated current', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    4: {'name': 'Motor power factor', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    5: {'name': 'Max output current', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    6: {'name': 'Max output frequency', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    7: {'name': 'Min output frequency', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    8: {'name': 'Enable reverse speed', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    9: {'name': 'Speed derating mode', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    10: {'name': 'Skip frequency: set 1', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    11: {'name': 'Skip frequency: band 1', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    12: {'name': 'Speed profile: frequency 1', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    13: {'name': 'Speed profile: frequency 2', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    14: {'name': 'Speed profile: frequency 3', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    15: {'name': 'Speed profile: acceleration 1', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    16: {'name': 'Speed profile: acceleration 2', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    17: {'name': 'Speed profile: acceleration 3', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    18: {'name': 'Speed profile: acceleration 4', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    19: {'name': 'Speed profile: delay 1', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    20: {'name': 'Speed profile: delay 2', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    21: {'name': 'Speed profile: delay 3', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    22: {'name': 'Speed profile: start mode', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    23: {'name': 'Speed profile: deceleration', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    24: {'name': 'Switching frequency', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    25: {'name': 'Switching frequency derating', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    26: {'name': 'Relay configuration', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    27: {'name': 'Enable motor overtemperature alarm (PTC)', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    28: {'name': 'Motor overtemperature alarm delay', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    29: {'name': 'Data communication fault timeout', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    30: {'name': 'Data communication baudrate', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    31: {'name': 'Data communication parity and stop bits', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    32: {'name': 'Base address', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    33: {'name': 'Stop mode', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    34: {'name': 'Flying restart', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    35: {'name': 'V/f boost voltage', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    36: {'name': 'V/f frequency adjustment', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    37: {'name': 'V/f voltage adjustment', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    38: {'name': 'Reserved HR38', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    39: {'name': 'Reserved HR39', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    40: {'name': 'Reserved HR40', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    41: {'name': 'Reserved HR41', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    42: {'name': 'Reserved HR42', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    43: {'name': 'Reserved HR43', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    44: {'name': 'Reserved HR44', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    45: {'name': 'Motor magnetising current', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    46: {'name': 'Stator resistance', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    47: {'name': 'Rotor resistance', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    48: {'name': 'Stator inductance Ld', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    49: {'name': 'Leakage factor', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    50: {'name': 'Stator inductance Lq', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    51: {'name': 'Magnetising time', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    52: {'name': 'Reserved HR52', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    53: {'name': 'Regeneration current limit', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    54: {'name': 'Overvoltage control current limit', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    55: {'name': 'Speed loop Kp', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    56: {'name': 'Speed loop Ti', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    57: {'name': 'Starting current', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    58: {'name': 'Frequency for starting current', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    60: {'name': 'Reserved HR60', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    61: {'name': 'Reserved HR61', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    62: {'name': 'Reserved HR62', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    63: {'name': 'Reserved HR63', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    64: {'name': 'Reserved HR64', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    65: {'name': 'Crankcase heater current', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    66: {'name': 'Safety torque off alarm auto reset on drive standby', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    67: {'name': 'Skip frequency set point 2', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    68: {'name': 'Skip frequency band 2', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    69: {'name': 'Skip frequency set point 3', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    70: {'name': 'Skip frequency band 3', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    71: {'name': 'Reserved HR71', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    72: {'name': 'Reserved HR72', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    73: {'name': 'Reserved HR73', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    74: {'name': 'Reserved HR74', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    75: {'name': 'Reserved HR75', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    76: {'name': 'Extended functions', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    77: {'name': 'Inductance saturation factor', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    78: {'name': 'Reserved HR78', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    79: {'name': 'Reserved HR79', 'type': 'Holding', 'multiplier': 1, 'unit': ''},
    # Input registers from 35-50 (Measurements)
    1035: {'name': 'U Output current measurement', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    1036: {'name': 'V Output current measurement', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    1037: {'name': 'W Output current measurement', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    1038: {'name': 'DC BUS voltage measurement', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    1039: {'name': 'DC BUS current measurement', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    1040: {'name': 'DC BUS power measurement', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    1041: {'name': 'Reserved IR41', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    1042: {'name': 'Reserved IR42', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    1043: {'name': 'Reserved IR43', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    1044: {'name': 'Reserved IR44', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    1045: {'name': 'Reserved IR45', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    1046: {'name': 'Reserved IR46', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    1047: {'name': 'Reserved IR47', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    1048: {'name': 'Reserved IR48', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    1050: {'name': 'Reserved IR50', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    # Input registers from 104-175 (Status and Info)
    104: {'name': '0: Stop', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    105: {'name': 'see doc', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    106: {'name': 'Drive status registers (bitfield see doc.)', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    107: {'name': 'Speed status registers (bitfield see doc.)', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    108: {'name': 'Motor equivalent frequency [0.1Hz]', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    109: {'name': 'Actual current of the motor [0.1A]', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    110: {'name': 'Current power of the motor [0.01KW]', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    111: {'name': 'Voltage applied to the motor (phase to phase)', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    112: {'name': 'Reserved IR112', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    113: {'name': 'DC bus voltage', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    114: {'name': 'Drive temperature', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    115: {'name': 'Drive life time', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    116: {'name': 'Drive run time', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    117: {'name': 'Drive run time after last alarm', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    118: {'name': 'Total energy supplied to the motor [0.1kWh]', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    119: {'name': 'Total energy supplied to the motor', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    120: {'name': 'Drive network address', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    121: {'name': 'Network address set by the drive dipswitches', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    122: {'name': 'Communication error info', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    123: {'name': 'UART error counter', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    124: {'name': 'PWM switching frequency', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    125: {'name': 'Pre-ramp output frequency reference', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    126: {'name': 'Post-ramp output frequency reference', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    127: {'name': 'Reserved IR127', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    128: {'name': 'Reserved IR128', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    129: {'name': 'Reserved IR129', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    130: {'name': 'Reserved IR130', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    131: {'name': 'Reserved IR131', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    132: {'name': 'Rotor frequency', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    133: {'name': 'Reserved IR133', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    134: {'name': 'DC bus ripple', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    135: {'name': 'Reserved IR135', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    136: {'name': 'Reserved IR136', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    137: {'name': 'Alarm log 1', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    138: {'name': 'Alarm log 2', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    139: {'name': 'Alarm log 3', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    140: {'name': 'Alarm log 4', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    141: {'name': 'Bootloader version', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    142: {'name': 'Firmware version', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    143: {'name': 'Firmware checksum', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    144: {'name': 'Motor control version', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    145: {'name': 'Serial number 1', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    146: {'name': 'Serial number 2', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    147: {'name': 'Serial number 3', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    148: {'name': 'Serial number 4', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    149: {'name': 'Hardware identification', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    150: {'name': 'Reserved IR150', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    151: {'name': 'Reserved IR151', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    152: {'name': 'Reserved IR152', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    153: {'name': 'Motor Overload Accumulator', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    154: {'name': 'Drive Overload Accumulator', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    155: {'name': 'Reserved IR155', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    156: {'name': 'Reserved IR156', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    157: {'name': 'Reserved IR157', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    158: {'name': 'Reserved IR158', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    159: {'name': 'Reserved IR159', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    160: {'name': 'Reserved IR160', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    161: {'name': 'Reserved IR161', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    162: {'name': 'Reserved IR162', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    163: {'name': 'Reserved IR163', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    164: {'name': 'Reserved IR164', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    165: {'name': 'Reserved IR165', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    166: {'name': 'Reserved IR166', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    167: {'name': 'Reserved IR167', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    168: {'name': 'Reserved IR168', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    169: {'name': 'Reserved IR169', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    170: {'name': 'Reserved IR170', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    171: {'name': 'Reserved IR171', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    172: {'name': 'Reserved IR172', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    173: {'name': 'Reserved IR173', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    174: {'name': 'Reserved IR174', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    175: {'name': 'Reserved IR175', 'type': 'Input', 'multiplier': 1, 'unit': ''},
    # Discrete inputs (alarms)
    2001: {'name': 'Alarm01: Overcurrent', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2002: {'name': 'Alarm02: Motor overload', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2003: {'name': 'Alarm03: Overvoltage', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2004: {'name': 'Alarm04: Undervoltage', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2005: {'name': 'Alarm05: Drive overtemperature', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2006: {'name': 'Alarm06: Drive undertemperature', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2007: {'name': 'Alarm07: Hardware Overcurrent', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2008: {'name': 'Alarm08: Motor overtemperature (PTC)', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2009: {'name': 'Alarm09: IGBT fault', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2010: {'name': 'Alarm10: CPU Error', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2011: {'name': 'Alarm11: Factory default done', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2012: {'name': 'Alarm12: DC bus ripple too large', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2013: {'name': 'Alarm13: Data communication fault', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2014: {'name': 'Alarm14: Drive thermistor fault', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2015: {'name': 'Alarm15: Auto-tuning fault', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2016: {'name': 'Alarm16: Safe Torque Off', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2017: {'name': 'Alarm17: Motor phase loss', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2018: {'name': 'Alarm18: InternAlarm fan fault', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2019: {'name': 'Alarm19: StAlarml', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2020: {'name': 'Alarm20: PFC fault', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2021: {'name': 'Alarm21: Input power supply overvoltage', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2022: {'name': 'Alarm22: Input power supply undervoltage', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2023: {'name': 'Alarm23: STO circuit fault', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2024: {'name': 'Alarm24: STO circuit fault', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2025: {'name': 'Alarm25: Ground fault (only for single-phase)', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2026: {'name': 'Alarm26: ADC conversion sync fault', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2027: {'name': 'Alarm27: Hw synchronisation fault', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2028: {'name': 'Alarm28: Drive overload', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2029: {'name': 'Alarm29: Inverter microcontroller safety drive stopped', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2098: {'name': 'Alarm98: Drive unexpected re-start', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2099: {'name': 'Alarm99: Drive unexpected stop', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2101: {'name': 'Alarm101: U,V,W currents measure fault', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2102: {'name': 'Alarm102: UnbAlarmanced U,V,W currents', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2103: {'name': 'Alarm103: Overcurrent or ground fault', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2104: {'name': 'Alarm104: STO input open', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2105: {'name': 'Alarm105: STO internAlarm circuit fault', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2106: {'name': 'Alarm106: Power supply loss', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2107: {'name': 'Alarm107: Motor drivers error', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2108: {'name': 'Alarm108: Reserved', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2109: {'name': 'Alarm109: Data communication fault', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2110: {'name': 'Alarm110: Compressor stAlarml', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2111: {'name': 'Alarm111: DC bus overcurrent', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2112: {'name': 'Alarm112: DC bus current measure error', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2113: {'name': 'Alarm113: DCbus voltage out of range', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2114: {'name': 'Alarm114: DCbus voltage measure error', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2115: {'name': 'Alarm115: Power supply undervoltage', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2116: {'name': 'Alarm116: Power supply voltage measure error', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2201: {'name': 'Alarm201: DCbus overload', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2202: {'name': 'Alarm202: DCbus load measure error', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2203: {'name': 'Alarm203: Drive overtemperature', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2204: {'name': 'Alarm204: Drive undertemperature', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2205: {'name': 'Alarm205: Temperature probe fault', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2206: {'name': 'Alarm206: Cpu sync error', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2207: {'name': 'Alarm207: InvAlarmid Safety data set', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2208: {'name': 'Alarm208: Reserved', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2209: {'name': 'Alarm209: Control circuit error', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2210: {'name': 'Alarm210: Reserved', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2211: {'name': 'Alarm211: Reserved', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2212: {'name': 'Alarm212: Reserved', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2213: {'name': 'Alarm213: Reserved', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2214: {'name': 'Alarm214: Reserved', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2215: {'name': 'Alarm215: Reserved', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},
    2216: {'name': 'Alarm216: Reserved', 'type': 'Discrete_input', 'multiplier': 1, 'unit': ''},


}   

# Define bit meanings for registers
BIT_DEFINITIONS = {
 #Address: {  0: "Bit 0", ..)
0:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
1:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
2:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
3:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
4:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
5:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
6:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
7:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
8:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
9:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
10:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
11:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
12:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
13:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
14:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
15:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
16:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
17:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
18:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
19:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
20:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
21:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
22:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
23:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
24:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
25:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
26:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
27:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
28:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
29:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
30:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
31:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
32:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
33:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
34:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
35:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
36:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
37:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
38:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
39:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
40:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
41:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
42:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
43:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
44:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
45:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
46:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
47:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
48:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
49:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
50:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
51:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
52:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
53:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
54:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
55:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
56:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
57:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
58:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
60:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
61:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
62:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
63:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
64:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
65:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
66:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
67:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
68:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
69:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
70:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
71:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
72:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
73:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
74:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
75:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
76:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
77:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
78:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
79:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
76:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
76:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
22:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
22:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
76:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
104:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
105:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
106:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
107:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
108:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
109:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
110:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
111:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
112:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
113:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
114:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
115:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
116:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
117:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
118:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
119:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
120:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
121:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
122:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
123:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
124:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
125:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
126:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
127:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
128:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
129:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
130:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
131:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
132:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
133:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
134:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
135:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
136:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
137:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
138:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
139:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
140:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
141:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
142:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
143:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
144:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
145:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
146:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
147:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
148:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
149:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
150:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
151:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
152:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
153:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
154:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
155:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
156:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
157:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
158:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
159:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
160:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
161:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
162:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
163:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
164:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
165:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
166:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
167:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
168:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
169:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
170:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
171:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
172:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
173:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
174:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
175:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
35:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
36:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
37:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
38:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
39:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
40:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
41:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
42:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
43:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
44:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
45:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
46:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
47:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
48:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
49:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
50:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
51:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
52:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
1:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
2:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
3:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
4:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
5:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
6:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
7:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
8:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
9:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
10:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
11:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
12:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
13:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
14:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
15:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
16:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
17:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
18:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
19:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
20:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
21:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
22:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
23:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
24:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
25:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
26:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
27:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
28:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
29:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
98:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
99:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
101:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
102:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
103:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
104:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
105:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
106:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
107:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
108:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
109:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
110:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
111:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
112:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
113:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
114:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
115:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
116:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
201:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
202:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
203:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
204:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
205:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
206:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
207:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
208:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
209:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
210:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
211:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
212:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
213:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
214:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
215:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
216:  {0: '',1: '',2: '',3: '',4: '',5: '',6: '',7: '',8: '',9: '',10: '',11: '',12: '',13: '',14: '',15: '' },
}
# Settings for bit definitions display
BIT_DISPLAY_SETTINGS = {
22: {"show_bits": True},
0:  {'show_bits' :False},
1:  {'show_bits' :False},
2:  {'show_bits' :False},
3:  {'show_bits' :False},
4:  {'show_bits' :False},
5:  {'show_bits' :False},
6:  {'show_bits' :False},
7:  {'show_bits' :False},
8:  {'show_bits' :False},
9:  {'show_bits' :False},
10:  {'show_bits' :False},
11:  {'show_bits' :False},
12:  {'show_bits' :False},
13:  {'show_bits' :False},
14:  {'show_bits' :False},
15:  {'show_bits' :False},
16:  {'show_bits' :False},
17:  {'show_bits' :False},
18:  {'show_bits' :False},
19:  {'show_bits' :False},
20:  {'show_bits' :False},
21:  {'show_bits' :False},
22:  {'show_bits' :False},
23:  {'show_bits' :False},
24:  {'show_bits' :False},
25:  {'show_bits' :False},
26:  {'show_bits' :False},
27:  {'show_bits' :False},
28:  {'show_bits' :False},
29:  {'show_bits' :False},
30:  {'show_bits' :False},
31:  {'show_bits' :False},
32:  {'show_bits' :False},
33:  {'show_bits' :False},
34:  {'show_bits' :False},
35:  {'show_bits' :False},
36:  {'show_bits' :False},
37:  {'show_bits' :False},
38:  {'show_bits' :False},
39:  {'show_bits' :False},
40:  {'show_bits' :False},
41:  {'show_bits' :False},
42:  {'show_bits' :False},
43:  {'show_bits' :False},
44:  {'show_bits' :False},
45:  {'show_bits' :False},
46:  {'show_bits' :False},
47:  {'show_bits' :False},
48:  {'show_bits' :False},
49:  {'show_bits' :False},
50:  {'show_bits' :False},
51:  {'show_bits' :False},
52:  {'show_bits' :False},
53:  {'show_bits' :False},
54:  {'show_bits' :False},
55:  {'show_bits' :False},
56:  {'show_bits' :False},
57:  {'show_bits' :False},
58:  {'show_bits' :False},
60:  {'show_bits' :False},
61:  {'show_bits' :False},
62:  {'show_bits' :False},
63:  {'show_bits' :False},
64:  {'show_bits' :False},
65:  {'show_bits' :False},
66:  {'show_bits' :False},
67:  {'show_bits' :False},
68:  {'show_bits' :False},
69:  {'show_bits' :False},
70:  {'show_bits' :False},
71:  {'show_bits' :False},
72:  {'show_bits' :False},
73:  {'show_bits' :False},
74:  {'show_bits' :False},
75:  {'show_bits' :False},
76:  {'show_bits' :False},
77:  {'show_bits' :False},
78:  {'show_bits' :False},
79:  {'show_bits' :False},
76:  {'show_bits' :False},
76:  {'show_bits' :False},
22:  {'show_bits' :False},
22:  {'show_bits' :False},
76:  {'show_bits' :False},
104:  {'show_bits' :False},
105:  {'show_bits' :False},
106:  {'show_bits' :False},
107:  {'show_bits' :False},
108:  {'show_bits' :False},
109:  {'show_bits' :False},
110:  {'show_bits' :False},
111:  {'show_bits' :False},
112:  {'show_bits' :False},
113:  {'show_bits' :False},
114:  {'show_bits' :False},
115:  {'show_bits' :False},
116:  {'show_bits' :False},
117:  {'show_bits' :False},
118:  {'show_bits' :False},
119:  {'show_bits' :False},
120:  {'show_bits' :False},
121:  {'show_bits' :False},
122:  {'show_bits' :False},
123:  {'show_bits' :False},
124:  {'show_bits' :False},
125:  {'show_bits' :False},
126:  {'show_bits' :False},
127:  {'show_bits' :False},
128:  {'show_bits' :False},
129:  {'show_bits' :False},
130:  {'show_bits' :False},
131:  {'show_bits' :False},
132:  {'show_bits' :False},
133:  {'show_bits' :False},
134:  {'show_bits' :False},
135:  {'show_bits' :False},
136:  {'show_bits' :False},
137:  {'show_bits' :False},
138:  {'show_bits' :False},
139:  {'show_bits' :False},
140:  {'show_bits' :False},
141:  {'show_bits' :False},
142:  {'show_bits' :False},
143:  {'show_bits' :False},
144:  {'show_bits' :False},
145:  {'show_bits' :False},
146:  {'show_bits' :False},
147:  {'show_bits' :False},
148:  {'show_bits' :False},
149:  {'show_bits' :False},
150:  {'show_bits' :False},
151:  {'show_bits' :False},
152:  {'show_bits' :False},
153:  {'show_bits' :False},
154:  {'show_bits' :False},
155:  {'show_bits' :False},
156:  {'show_bits' :False},
157:  {'show_bits' :False},
158:  {'show_bits' :False},
159:  {'show_bits' :False},
160:  {'show_bits' :False},
161:  {'show_bits' :False},
162:  {'show_bits' :False},
163:  {'show_bits' :False},
164:  {'show_bits' :False},
165:  {'show_bits' :False},
166:  {'show_bits' :False},
167:  {'show_bits' :False},
168:  {'show_bits' :False},
169:  {'show_bits' :False},
170:  {'show_bits' :False},
171:  {'show_bits' :False},
172:  {'show_bits' :False},
173:  {'show_bits' :False},
174:  {'show_bits' :False},
175:  {'show_bits' :False},
35:  {'show_bits' :False},
36:  {'show_bits' :False},
37:  {'show_bits' :False},
38:  {'show_bits' :False},
39:  {'show_bits' :False},
40:  {'show_bits' :False},
41:  {'show_bits' :False},
42:  {'show_bits' :False},
43:  {'show_bits' :False},
44:  {'show_bits' :False},
45:  {'show_bits' :False},
46:  {'show_bits' :False},
47:  {'show_bits' :False},
48:  {'show_bits' :False},
49:  {'show_bits' :False},
50:  {'show_bits' :False},
51:  {'show_bits' :False},
52:  {'show_bits' :False},
1:  {'show_bits' :False},
2:  {'show_bits' :False},
3:  {'show_bits' :False},
4:  {'show_bits' :False},
5:  {'show_bits' :False},
6:  {'show_bits' :False},
7:  {'show_bits' :False},
8:  {'show_bits' :False},
9:  {'show_bits' :False},
10:  {'show_bits' :False},
11:  {'show_bits' :False},
12:  {'show_bits' :False},
13:  {'show_bits' :False},
14:  {'show_bits' :False},
15:  {'show_bits' :False},
16:  {'show_bits' :False},
17:  {'show_bits' :False},
18:  {'show_bits' :False},
19:  {'show_bits' :False},
20:  {'show_bits' :False},
21:  {'show_bits' :False},
22:  {'show_bits' :False},
23:  {'show_bits' :False},
24:  {'show_bits' :False},
25:  {'show_bits' :False},
26:  {'show_bits' :False},
27:  {'show_bits' :False},
28:  {'show_bits' :False},
29:  {'show_bits' :False},
98:  {'show_bits' :False},
99:  {'show_bits' :False},
101:  {'show_bits' :False},
102:  {'show_bits' :False},
103:  {'show_bits' :False},
104:  {'show_bits' :False},
105:  {'show_bits' :False},
106:  {'show_bits' :False},
107:  {'show_bits' :False},
108:  {'show_bits' :False},
109:  {'show_bits' :False},
110:  {'show_bits' :False},
111:  {'show_bits' :False},
112:  {'show_bits' :False},
113:  {'show_bits' :False},
114:  {'show_bits' :False},
115:  {'show_bits' :False},
116:  {'show_bits' :False},
201:  {'show_bits' :False},
202:  {'show_bits' :False},
203:  {'show_bits' :False},
204:  {'show_bits' :False},
205:  {'show_bits' :False},
206:  {'show_bits' :False},
207:  {'show_bits' :False},
208:  {'show_bits' :False},
209:  {'show_bits' :False},
210:  {'show_bits' :False},
211:  {'show_bits' :False},
212:  {'show_bits' :False},
213:  {'show_bits' :False},
214:  {'show_bits' :False},
215:  {'show_bits' :False},
216:  {'show_bits' :False},
}

# Available options for dropdown menus
BAUDRATE_OPTIONS = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
PARITY_OPTIONS = [
    {'label': 'None (N)', 'value': 'N'},
    {'label': 'Even (E)', 'value': 'E'},
    {'label': 'Odd (O)', 'value': 'O'}
]
STOPBITS_OPTIONS = [1, 1.5, 2]
BYTESIZE_OPTIONS = [5, 6, 7, 8]

# Register type options
REGISTER_TYPE_OPTIONS = [
    {'label': 'Holding Register', 'value': 'Holding'},
    {'label': 'Input Register', 'value': 'Input'},
    {'label': 'Coil', 'value': 'Coil'},
    {'label': 'Discrete Input', 'value': 'Discrete_input'}
]

# Initialize variables
renamed_vars = {k: v['name'] for k, v in REGISTER_MAP.items()}
client = None

# Add these variables to the global section near the top of the file
last_read_duration = 0  # Track how long the last read operation took
min_polling_interval = 1  # Minimum polling interval in seconds
def load_register_map_from_csv(file_path):
    """
    Load register map from a CSV file.
    
    Expected CSV format:
    Address,Name,Type,Multiplier,Unit,BitDefinitions
    0,Virtual probe error,Discrete_input,1,,
    0,Virtual probe temperature (Sv),Input,0.1,°C,
    ...
    
    :param file_path: Path to the CSV file
    :return: Dictionary of register map in the format expected by the application
    """
    global BIT_DEFINITIONS
    
    # logger.info(f"Loading register map from CSV: {file_path}")
    register_map = {}
    
    if not os.path.exists(file_path):
        logger.error(f"CSV file not found: {file_path}")
        return register_map
    
    try:
        with open(file_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                try:
                    address = int(row['Address'])
                    name = row['Name']
                    reg_type = row['Type']
                    
                    # Handle multiplier (convert to float or default to 1)
                    try:
                        multiplier = float(row['Multiplier']) if 'Multiplier' in row else 1.0
                    except ValueError:
                        logger.warning(f"Invalid multiplier for address {address}, defaulting to 1.0")
                        multiplier = 1.0
                    
                    # Get unit if available
                    unit = row.get('Unit', '')
                    
                    # Validate register type
                    valid_types = ['Holding', 'Input', 'Coil', 'Discrete_input']
                    if reg_type not in valid_types:
                        logger.warning(f"Invalid register type '{reg_type}' for address {address}, defaulting to 'Holding'")
                        reg_type = 'Holding'
                    
                    # Add to register map
                    register_map[address] = {
                        'name': name,
                        'type': reg_type,
                        'multiplier': multiplier
                    }
                    
                    # Add unit if present
                    if unit:
                        register_map[address]['unit'] = unit
                    
                   # logger.debug(f"Added register {address}: {name} ({reg_type}, multiplier={multiplier}, unit={unit})")
                    
                    # Process bit definitions if present
                    if 'BitDefinitions' in row and row['BitDefinitions']:
                        # Initialize the bit definitions dictionary for this register if needed
                        if address not in BIT_DEFINITIONS:
                            BIT_DEFINITIONS[address] = {}
                        
                        # Parse the bit definitions
                        bit_defs = row['BitDefinitions'].split(';')
                        for bit_def in bit_defs:
                            if ':' in bit_def:
                                bit_pos, bit_desc = bit_def.split(':', 1)
                                try:
                                    bit_pos = int(bit_pos)
                                    BIT_DEFINITIONS[address][bit_pos] = bit_desc
                                   # logger.debug(f"Added bit definition for register {address}, bit {bit_pos}: {bit_desc}")
                                except ValueError:
                                    logger.warning(f"Invalid bit position '{bit_pos}' for register {address}")
                    
                except ValueError as e:
                    logger.error(f"Error parsing CSV row: {row}. Error: {str(e)}")
                    continue
                except KeyError as e:
                    logger.error(f"Missing required column in CSV: {str(e)}")
                    continue
                
        logger.info(f"Successfully loaded {len(register_map)} registers from CSV")
        return register_map
    
    except Exception as e:
        logger.error(f"Error loading register map from CSV: {str(e)}")
        logger.error(traceback.format_exc())
        return {}

# Add this function to measure reading time and calculate the optimal polling interval
def adjust_polling_interval(start_time):
    """
    Calculate the time it took to read all registers and adjust polling interval accordingly.
    
    :param start_time: The time when reading started
    :return: Suggested polling interval (read time + 1 second)
    """
    global last_read_duration
    
    # Calculate how long the read operation took
    end_time = time.time()
    read_duration = end_time - start_time
    
    # Update the last read duration
    last_read_duration = read_duration
    
    # Calculate suggested polling interval (read time + 1 second)
    suggested_interval = read_duration + min_polling_interval
    
    # Round up to nearest 0.1 second for better display
    suggested_interval = round(suggested_interval * 10) / 10
    
    # Cap at a minimum interval
    suggested_interval = max(suggested_interval, min_polling_interval)
    
    logger.debug(f"Read operation took {read_duration:.2f}s, suggested polling interval: {suggested_interval:.1f}s")
    return suggested_interval

# Detect pymodbus version to handle API differences
try:
    import pymodbus
    PYMODBUS_VERSION = pymodbus.__version__
    logger.info(f"Detected pymodbus version: {PYMODBUS_VERSION}")
    # Check major version
    MAJOR_VERSION = int(PYMODBUS_VERSION.split('.')[0])
    
    # Determine if we should use 'unit' or 'slave' parameter
    if MAJOR_VERSION >= 10:
        USE_UNIT_PARAMETER = True
        logger.info("Using 'unit' parameter for Modbus requests")
    else:
        USE_UNIT_PARAMETER = False
        logger.info("Using 'slave' parameter for Modbus requests")
except:
    logger.warning("Could not determine pymodbus version, defaulting to 'slave' parameter")
    USE_UNIT_PARAMETER = False

# Function to perform a modbus read with version compatibility
def read_modbus_register(client, address, unit_id, register_type="holding"):
    """
    Reads a Modbus register (holding, input, coil, or discrete input) with compatibility for different parameter names.

    :param client: Modbus client
    :param address: Register address
    :param unit_id: Modbus unit/slave ID
    :param register_type: "holding", "input", "coil", or "discrete_input"
    :return: Modbus response
    """
    try:
        if register_type not in ("Holding", "Input", "Coil", "Discrete_input"):
            raise ValueError("register_type must be 'Holding', 'Input', 'Coil', or 'Discrete_input'")

        # Select the appropriate read function based on register type
        if register_type == "Holding":
            read_func = client.read_holding_registers
        elif register_type == "Input":
            read_func = client.read_input_registers
        elif register_type == "Coil":
            read_func = client.read_coils
        elif register_type == "Discrete_input":
            read_func = client.read_discrete_inputs

        # Use the appropriate parameter (unit or slave) based on pymodbus version
        if USE_UNIT_PARAMETER:
            result = read_func(address=address, count=1, unit=unit_id)
        else:
            result = read_func(address=address, count=1, slave=unit_id)

        return result

    except Exception as e:
        logger.error(f"Error reading {register_type} register at {address}: {e}")
        logger.error(traceback.format_exc())
        raise

# Function to write a value to a Modbus register

def write_modbus_register(client, address, value, unit_id, register_type):
    """
    Writes a value to a Modbus register.
    :param client: Modbus client
    :param address: Register address
    :param value: Value to write
    :param unit_id: Modbus unit/slave ID
    :param register_type: "Holding" or "Coil"
    :return: Modbus response
    """
    try:
        if register_type not in ("Holding", "Coil"):
            raise ValueError("write register_type must be 'Holding' or 'Coil'")
        
        # Select the appropriate write function
        if register_type == "Holding":
            write_func = client.write_register
        elif register_type == "Coil":
            # Fix: Use write_coil (singular) not write_coils (plural)
            write_func = client.write_coil
            
            # For coils, ensure value is boolean
            value = bool(int(float(value)))
            
        # Use the appropriate parameter based on pymodbus version
        if USE_UNIT_PARAMETER:
            result = write_func(address=address, value=value, unit=unit_id)
        else:
            result = write_func(address=address, value=value, slave=unit_id)
        return result
    except Exception as e:
        logger.error(f"Error writing to {register_type} {address}: {str(e)}")
        return None

# --- Serial port detection ---
def list_serial_ports():
    try:
        ports = serial.tools.list_ports.comports()
        port_list = [{'label': f"{p.device} ({p.description})", 'value': p.device} for p in ports]
        
        # Log detailed information about each port for troubleshooting
        logger.info(f"Detected {len(port_list)} serial ports")
        if ports:
            for p in ports:
                logger.info(f"Port: {p.device}")
                logger.info(f"  Description: {p.description}")
                logger.info(f"  Hardware ID: {p.hwid}")
                logger.info(f"  USB Info: VID={p.vid if hasattr(p, 'vid') else 'N/A'} PID={p.pid if hasattr(p, 'pid') else 'N/A'}")
                logger.info(f"  Manufacturer: {p.manufacturer if hasattr(p, 'manufacturer') else 'N/A'}")
                logger.info(f"  Interface: {p.interface if hasattr(p, 'interface') else 'N/A'}")
        else:
            logger.warning("No serial ports detected. If using a USB converter, check if it's properly connected and drivers are installed.")
            
        return port_list
    except Exception as e:
        logger.error(f"Error detecting serial ports: {str(e)}")
        logger.error(traceback.format_exc())
        return []

# --- App Setup ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Modbus RTU Web Viewer"

# Check USB serial drivers and status
def check_usb_serial_status():
    try:
        # On macOS/Linux
        if os.path.exists('/dev'):
            logger.info("Checking USB devices in /dev directory")
            usb_devices = [d for d in os.listdir('/dev') if d.startswith(('tty.usb', 'ttyUSB', 'cu.usb'))]
            logger.info(f"Found USB TTY devices: {usb_devices}")
            
            # Check for potential USB device permission issues on Linux
            if os.name == 'posix' and os.uname().sysname == 'Linux':
                logger.info("Checking USB device permissions on Linux")
                for dev in usb_devices:
                    try:
                        device_path = f"/dev/{dev}"
                        stat_info = os.stat(device_path)
                        permissions = oct(stat_info.st_mode)[-3:]
                        logger.info(f"Device {device_path} permissions: {permissions}")
                        if permissions != '666' and permissions != '777' and permissions != '622':
                            logger.warning(f"Possible permission issue with {device_path} - permissions are {permissions}")
                    except Exception as e:
                        logger.error(f"Error checking permissions for {dev}: {str(e)}")
                        
        # On Windows
        elif os.name == 'nt':
            logger.info("Checking COM ports on Windows")
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DEVICEMAP\SERIALCOMM')
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    logger.info(f"Found COM port: {value} ({name})")
                    i += 1
                except WindowsError:
                    break
    except Exception as e:
        logger.error(f"Error checking USB serial status: {str(e)}")
        logger.error(traceback.format_exc())

# Run USB serial status check at startup
check_usb_serial_status()


app.layout = dbc.Container([
    html.H3("Modbus RS485 Viewer", className="mt-4 mb-3"),
    
    # Status indicators row at the top
    dbc.Row([
        dbc.Col(
            dbc.Button("Disconnect", id="disconnect-btn", color="danger", 
                       className="me-2", style={"display": "none"}),
            width="auto"
        ),
        dbc.Col(
            html.Div(id="port-status", className="mt-2"),
            width="auto"
        ),
    ], className="mb-3"),

    # Connection Settings Panel
    dbc.Card([
        dbc.CardHeader("Connection Settings"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col(html.Div("Device COM Port"), width=2),
                dbc.Col(
                    dcc.Dropdown(
                        id="com-port",
                        options=list_serial_ports(),
                        placeholder="Select a serial port",
                        className="form-control"
                    ), width=4
                ),
                dbc.Col(dbc.Button("🔄 Refresh", id="refresh-ports", color="secondary"), width="auto"),
                dbc.Col(dbc.Button("Connect", id="connect-btn", color="primary"), width="auto"),
                dbc.Col(html.Div(id="connection-status"), width=4),
            ], className="mb-3"),

            # Protocol Settings
            html.H6("Protocol Settings", className="mt-3"),
            dbc.Row([
                # Baudrate
                dbc.Col([
                    html.Label("Baudrate:"),
                    dcc.Dropdown(
                        id="baudrate-select",
                        options=[{'label': str(b), 'value': b} for b in BAUDRATE_OPTIONS],
                        value=MODBUS_CONFIG['baudrate'],
                        clearable=False
                    )
                ], width=2),
                
                # Parity
                dbc.Col([
                    html.Label("Parity:"),
                    dcc.Dropdown(
                        id="parity-select",
                        options=PARITY_OPTIONS,
                        value=MODBUS_CONFIG['parity'],
                        clearable=False
                    )
                ], width=2),
                
                # Stopbits
                dbc.Col([
                    html.Label("Stop Bits:"),
                    dcc.Dropdown(
                        id="stopbits-select",
                        options=[{'label': str(s), 'value': s} for s in STOPBITS_OPTIONS],
                        value=MODBUS_CONFIG['stopbits'],
                        clearable=False
                    )
                ], width=2),
                
                # Bytesize
                dbc.Col([
                    html.Label("Byte Size:"),
                    dcc.Dropdown(
                        id="bytesize-select",
                        options=[{'label': str(b), 'value': b} for b in BYTESIZE_OPTIONS],
                        value=MODBUS_CONFIG['bytesize'],
                        clearable=False
                    )
                ], width=2),
                
                # Timeout
                dbc.Col([
                    html.Label("Timeout (sec):"),
                    dcc.Input(
                        id="timeout-input",
                        type="number",
                        value=MODBUS_CONFIG['timeout'],
                        min=0.1,
                        step=0.1,
                        className="form-control"
                    )
                ], width=2),
                
                # Unit ID
                dbc.Col([
                    html.Label("Unit ID:"),
                    dcc.Input(
                        id="unit-id-input",
                        type="number",
                        value=MODBUS_CONFIG['unit_id'],
                        min=1,
                        max=247,
                        step=1,
                        className="form-control"
                    )
                ], width=2),
            ], className="mb-3"),
            
            
            dbc.Row([
                dbc.Col(html.Div("Polling Interval (sec):"), width=2),
                dbc.Col(dcc.Input(
                    id="poll-interval", 
                    value=10, 
                    type="number", 
                    min=1, 
                    step=1, 
                    className="form-control"), 
                    width=2
                ),
                dbc.Col(dbc.Button("Apply Settings", id="apply-settings-btn", color="info"), width="auto"),
                # Add a new column to display the suggested interval
                dbc.Col(html.Div(id="suggested-interval-display"), width=4),
            ], className="mb-2"),
            
            
            dbc.Row([
                dbc.Col(html.Div("Import Register Map from CSV:"), width=2),
                dbc.Col(
                    dcc.Upload(
                        id='upload-csv',
                        children=html.Div([
                            'Drag and Drop or ',
                            html.A('Select CSV File')
                        ]),
                        style={
                            'width': '100%',
                            'height': '60px',
                            'lineHeight': '60px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                            'margin': '10px'
                        },
                        multiple=False
                    ),
                    width=6
                ),
                dbc.Col(html.Div(id='csv-upload-status'), width=4),
            ], className="mb-3"),
    
            # Optional: Add a button to save the current register map to CSV
            dbc.Row([
                dbc.Col(html.Div("Export Register Map to CSV:"), width=2),
                dbc.Col(
                    dbc.Button("Download Current Register Map", id="export-csv-btn", color="secondary"),
                    width=3
                ),
                dbc.Col(html.Div(id="csv-export-status"), width=3),
                dbc.Col(dcc.Download(id="download-csv")),
            ], className="mb-3"),
            
        ])
    ], className="mb-4"),

    # Add this to the app layout, in the Register Management Card    
    # Register Management Panel
    dbc.Card([
        dbc.CardHeader("Register Management"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col(html.Div("Add Register:"), width=2),
                dbc.Col(dcc.Input(
                    id="new-register-addr", 
                    type="number", 
                    placeholder="Register Address", 
                    min=0, 
                    className="form-control"), 
                    width=2
                ),
                dbc.Col(dcc.Input(
                    id="new-register-name", 
                    type="text", 
                    placeholder="Register Name", 
                    className="form-control"), 
                    width=3
                ),
                dbc.Col(
                    dcc.Dropdown(
                        id="new-register-type",
                        options=REGISTER_TYPE_OPTIONS,
                        value="holding",
                        clearable=False,
                        placeholder="Register Type",
                        className="form-control"
                    ),
                    width=2
                ),
                dbc.Col(dbc.Button("Add", id="add-register-btn", color="success"), width="auto"),
            ], className="mb-3"),
            

            
            # Register type filter
            dbc.Row([
                dbc.Col(html.Div("Filter by Register Type:"), width=2),
                dbc.Col(
                    dcc.Dropdown(
                        id="register-type-filter",
                        options=[
                            {"label": "All Types", "value": "all"},
                            *REGISTER_TYPE_OPTIONS
                        ],
                        value="all",
                        clearable=False,
                        className="form-control"
                    ),
                    width=3
                ),
            ], className="mb-3"),
            
            # Add bit definition section
            html.Hr(),
            html.H5("Bit Definitions:"),
            dbc.Row([
                dbc.Col(html.Div("Register:"), width=1),
                dbc.Col(
                    dcc.Dropdown(
                        id="bit-register-select",
                        options=[{'label': f"{addr}: {reg['name']}", 'value': addr} 
                                for addr, reg in REGISTER_MAP.items()
                                if reg['type'] in ['Holding', 'Input']],
                        placeholder="Select register"
                    ),
                    width=3
                ),
                dbc.Col(html.Div("Show Bit Definitions:"), width=2),
                dbc.Col(
                    dbc.Switch(
                        id="show-bits-switch",
                        value=True,
                        className="me-2"
                    ),
                    width=1
                ),
            ], className="mb-3"),

            # Bit definition form
            dbc.Row([
                dbc.Col(html.Div("Bit Position:"), width=1),
                dbc.Col(
                    dcc.Input(
                        id="bit-position-input",
                        type="number",
                        min=0,
                        max=15,
                        placeholder="0-15"
                    ),
                    width=1
                ),
                dbc.Col(html.Div("Description:"), width=1),
                dbc.Col(
                    dcc.Input(
                        id="bit-description-input",
                        type="text",
                        placeholder="Bit meaning"
                    ),
                    width=3
                ),
                dbc.Col(
                    dbc.Button("Add Bit Definition", id="add-bit-def-btn", color="success"),
                    width=2
                ),
            ], className="mb-3"),

            # Display current bit definitions
            html.Div(id="bit-definitions-table"),
            # Add this as a new card after the Register Management Card
            # Graphing Panel
    
            dbc.Card([
                dbc.CardHeader("Register Graphing"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col(html.Div("Select Registers to Graph:"), width=2),
                        dbc.Col(
                            dcc.Dropdown(
                                id="graph-register-select",
                                options=[],  # Will be populated dynamically
                                multi=True,
                                placeholder="Select registers to graph"
                            ),
                            width=6
                        ),
                        dbc.Col(
                            dbc.Button("Clear Graph", id="clear-graph-btn", color="secondary", className="me-2"),
                            width=2
                        ),
                    ], className="mb-3"),
        
                    dbc.Row([
                        dbc.Col(
                            dcc.Graph(id="register-graph", style={"height": "400px"}),
                            width=12
                        )
                    ]),
        
                    # Add a new row for export buttons
                    dbc.Row([
                        dbc.Col(html.Div("Export Option:"), width=2),
                        dbc.Col(
                            dbc.Button("Export as CSV", id="export-graph-csv-btn", color="info", className="me-2"),
                            width=2
                        ),
                        dbc.Col(html.Div(id="export-status"), width=4),
                    ], className="mt-3")
                ])
            ], className="mb-4"),
            
            html.Hr(),
            html.H5("Live Register Values:"),
            html.Div(id="register-table"),
        ])
    ]),

    dcc.Interval(id="interval-component", interval=0, n_intervals=0, disabled=True),
    
    
    dcc.Download(id="download-graph-csv"),
    # Store current config in a dcc.Store component
    dcc.Store(id="current-config", data=MODBUS_CONFIG)
], fluid=True)  # Added fluid=True for better layout on all screen sizes



# --- Callbacks ---
@app.callback(
    Output("com-port", "options"),
    Input("refresh-ports", "n_clicks"),
    prevent_initial_call=True
)
def refresh_ports(n):
    logger.info("Refreshing serial port list")
    return list_serial_ports()


@app.callback(
    [Output("register-table", "children", allow_duplicate=True),
     Output("connection-status", "children", allow_duplicate=True)],
    Input({'type': 'coil-write-btn', 'index': dash.ALL}, 'n_clicks'),
    [State({'type': 'coil-write-btn', 'index': dash.ALL}, 'id'),
     State({'type': 'coil-switch', 'index': dash.ALL}, 'value'),
     State("current-config", "data")],
    prevent_initial_call=True
)
def write_coil_value(n_clicks, ids, values, config):
    global client
    
    if not n_clicks or not any(n_clicks):
        return dash.no_update, dash.no_update
    
    # Check if client is connected
    if not client or not client.is_socket_open():
        return dash.no_update, dbc.Alert("Not connected to device", color="danger")
    
    # Find the button that was clicked
    for i, clicks in enumerate(n_clicks):
        if clicks:
            register_index = ids[i]['index']
            new_value = values[i]
            
            # Verify this is a coil
            register_type = REGISTER_MAP[register_index]['type']
            if register_type != "Coil":
                continue
                
            logger.info(f"Writing coil value {new_value} to register {register_index}")
            
            try:
                # Convert bool to value
                coil_value = bool(new_value)
                
                # Write the value
                result = write_modbus_register(client, register_index, coil_value, config['unit_id'], register_type)
                
                if result and not hasattr(result, 'isError'):
                    return dash.no_update, dbc.Alert(f"Coil value {new_value} written to register {register_index}", color="success")
                else:
                    return dash.no_update, dbc.Alert(f"Failed to write to coil {register_index}", color="danger")
            except Exception as e:
                logger.error(f"Error writing to coil {register_index}: {str(e)}")
                return dash.no_update, dbc.Alert(f"Error: {str(e)}", color="danger")
    
    return dash.no_update, dash.no_update


@app.callback(
    [Output("csv-upload-status", "children"),
     Output("register-table", "children", allow_duplicate=True)],
    Input("upload-csv", "contents"),
    State("upload-csv", "filename"),
    prevent_initial_call=True
)
def update_from_csv_upload(contents, filename):
    global REGISTER_MAP, renamed_vars
    
    if contents is None:
        return dash.no_update, dash.no_update
    
    try:
        logger.info(f"Processing uploaded file: {filename}")
        
        # Check file extension
        if not filename.endswith('.csv'):
            logger.warning(f"Uploaded file is not a CSV: {filename}")
            return dbc.Alert("Please upload a CSV file.", color="warning"), dash.no_update
        
        # Decode the file contents
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Create a temporary file to store the uploaded content
        temp_file = os.path.join(os.getcwd(), 'temp_upload.csv')
        with open(temp_file, 'wb') as f:
            f.write(decoded)
        
        # Load the register map from the CSV
        new_register_map = load_register_map_from_csv(temp_file)
        
        # Clean up the temporary file
        try:
            os.remove(temp_file)
        except:
            logger.warning(f"Could not remove temporary file: {temp_file}")
        
        # Check if we got any registers
        if not new_register_map:
            logger.warning("No registers loaded from CSV")
            return dbc.Alert("No valid registers found in the CSV file.", color="warning"), dash.no_update
        
        # Update the register map and renamed vars
        REGISTER_MAP = new_register_map
        renamed_vars = {k: v['name'] for k, v in REGISTER_MAP.items()}
        
        logger.info(f"Successfully updated register map with {len(REGISTER_MAP)} registers from CSV")
        return dbc.Alert(f"Successfully loaded {len(REGISTER_MAP)} registers from CSV.", color="success"), dash.no_update
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error processing CSV upload: {error_msg}")
        logger.error(traceback.format_exc())
        return dbc.Alert(f"Error processing CSV: {error_msg}", color="danger"), dash.no_update
        
@app.callback(
    [Output("download-csv", "data"),
     Output("csv-export-status", "children")],
    Input("export-csv-btn", "n_clicks"),
    prevent_initial_call=True
)
def export_register_map_to_csv(n_clicks):
    if not n_clicks:
        return dash.no_update, dash.no_update
    
    try:
        logger.info("Exporting register map to CSV")
        
        # Create a string buffer
        csv_string = io.StringIO()
        fieldnames = ['Address', 'Name', 'Type', 'Multiplier', 'Unit', 'BitDefinitions']
        
        # Write CSV header and data
        writer = csv.DictWriter(csv_string, fieldnames=fieldnames)
        writer.writeheader()
        
        for address, register_info in sorted(REGISTER_MAP.items()):
            # Format bit definitions if they exist
            bit_defs_str = ""
            if address in BIT_DEFINITIONS:
                bit_defs = []
                for bit_pos, bit_desc in sorted(BIT_DEFINITIONS[address].items()):
                    bit_defs.append(f"{bit_pos}:{bit_desc}")
                bit_defs_str = ";".join(bit_defs)
            
            # Get unit or empty string if not present
            unit = register_info.get('unit', '')
            
            writer.writerow({
                'Address': address,
                'Name': register_info['name'],
                'Type': register_info['type'],
                'Multiplier': register_info.get('multiplier', 1),
                'Unit': unit,
                'BitDefinitions': bit_defs_str
            })
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"register_map_{timestamp}.csv"
        
        logger.info(f"Register map exported to {filename}")
        return dict(
            content=csv_string.getvalue(),
            filename=filename
        ), dbc.Alert("Export successful!", color="success")
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error exporting register map to CSV: {error_msg}")
        logger.error(traceback.format_exc())
        return dash.no_update, dbc.Alert(f"Error exporting CSV: {error_msg}", color="danger")
# Add this callback to handle writing values to holding registers
@app.callback(
    [Output("register-table", "children", allow_duplicate=True),
     Output("connection-status", "children", allow_duplicate=True)],
    Input({'type': 'write-btn', 'index': dash.ALL}, 'n_clicks'),
    [State({'type': 'write-btn', 'index': dash.ALL}, 'id'),
     State({'type': 'value-input', 'index': dash.ALL}, 'value'),
     State("current-config", "data")],
    prevent_initial_call=True
)
def write_holding_register_value(n_clicks, ids, values, config):
    global client
    
    if not n_clicks or not any(n_clicks):
        return dash.no_update, dash.no_update
    
    # Check if client is connected
    if not client or not client.is_socket_open():
        return dash.no_update, dbc.Alert("Not connected to device", color="danger")
    
    # Find the button that was clicked
    for i, clicks in enumerate(n_clicks):
        if clicks and values[i]:  # Only proceed if there's a value entered
            register_index = ids[i]['index']
            
            # Check if this is a holding register
            if register_index in REGISTER_MAP:
                register_type = REGISTER_MAP[register_index]['type']
                if register_type != "Holding":
                    continue
                    
                # Get the multiplier to convert back to raw value
                multiplier = REGISTER_MAP[register_index].get('multiplier', 1)
                
                try:
                    # Convert input value considering the multiplier
                    if multiplier != 0:
                        raw_value = int(float(values[i]) / multiplier)
                    else:
                        raw_value = int(float(values[i]))
                        
                    logger.info(f"Writing value {raw_value} to holding register {register_index}")
                    
                    # Write the value
                    result = write_modbus_register(client, register_index, raw_value, config['unit_id'], register_type)
                    
                    if result and not hasattr(result, 'isError'):
                        return dash.no_update, dbc.Alert(f"Value {values[i]} written to holding register {register_index}", color="success")
                    else:
                        return dash.no_update, dbc.Alert(f"Failed to write to holding register {register_index}", color="danger")
                except Exception as e:
                    logger.error(f"Error writing to holding register {register_index}: {str(e)}")
                    return dash.no_update, dbc.Alert(f"Error: {str(e)}", color="danger")
    
    return dash.no_update, dash.no_update
    
@app.callback(
    Output({'type': 'multiplier-input', 'index': dash.ALL}, 'value'),
    Input({'type': 'multiplier-input', 'index': dash.ALL}, 'value'),
    State({'type': 'multiplier-input', 'index': dash.ALL}, 'id'),
    prevent_initial_call=True
)
def update_register_multipliers(values, ids):
     # logger.debug(f"update_register_multipliers called with {len(values)} values")
    
    try:
        for val, id_dict in zip(values, ids):
            register_index = id_dict['index']
            logger.info(f"Updating register {register_index} multiplier to '{val}'")
            
            # Update the multiplier in REGISTER_MAP
            if register_index in REGISTER_MAP:
                if isinstance(REGISTER_MAP[register_index], dict):
                    REGISTER_MAP[register_index]['multiplier'] = val
                else:
                    # If it's still using the old format, convert to new format
                    REGISTER_MAP[register_index] = {'name': REGISTER_MAP[register_index], 'type': 'Holding', 'multiplier': val}
        
        return values
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error updating register multipliers: {error_msg}")
        logger.error(traceback.format_exc())
        return values  # Return original values in case of error    


@app.callback(
    [Output("connection-status", "children", allow_duplicate=True),
     Output("interval-component", "disabled", allow_duplicate=True),
     Output("disconnect-btn", "style", allow_duplicate=True),
     Output("port-status", "children", allow_duplicate=True)],
    Input("disconnect-btn", "n_clicks"),
    prevent_initial_call=True
)
def disconnect_modbus(n_clicks):
    global client
    logger.info("Disconnect button clicked")
    
    if client:
        try:
            logger.info("Closing Modbus connection")
            client.close()
            logger.info("Connection closed successfully")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error closing connection: {error_msg}")
            logger.error(traceback.format_exc())
        client = None
        logger.info("Client set to None")
    else:
        logger.warning("Disconnect called but client was already None")
    
    return [
        dbc.Alert("Disconnected", color="warning"),
        True,  # Disable interval
        {"display": "none"},  # Hide disconnect button
        ""  # Clear port status
    ]

@app.callback(
    Output("current-config", "data"),
    Input("apply-settings-btn", "n_clicks"),
    [State("baudrate-select", "value"),
     State("parity-select", "value"),
     State("stopbits-select", "value"),
     State("bytesize-select", "value"),
     State("timeout-input", "value"),
     State("unit-id-input", "value"),
     State("current-config", "data")],
    prevent_initial_call=True
)
def update_config(n_clicks, baudrate, parity, stopbits, bytesize, timeout, unit_id, current_config):
    if n_clicks:
        logger.info("Updating Modbus configuration")
        
        # Log the changes
        changes = []
        if current_config['baudrate'] != baudrate:
            changes.append(f"Baudrate: {current_config['baudrate']} -> {baudrate}")
        if current_config['parity'] != parity:
            changes.append(f"Parity: {current_config['parity']} -> {parity}")
        if current_config['stopbits'] != stopbits:
            changes.append(f"Stop Bits: {current_config['stopbits']} -> {stopbits}")
        if current_config['bytesize'] != bytesize:
            changes.append(f"Byte Size: {current_config['bytesize']} -> {bytesize}")
        if current_config['timeout'] != timeout:
            changes.append(f"Timeout: {current_config['timeout']} -> {timeout}")
        if current_config['unit_id'] != unit_id:
            changes.append(f"Unit ID: {current_config['unit_id']} -> {unit_id}")
            
        if changes:
            logger.info(f"Configuration changes: {', '.join(changes)}")
        else:
            logger.info("No configuration changes detected")
        
        # Update the config
        current_config.update({
            'baudrate': baudrate,
            'parity': parity,
            'stopbits': stopbits,
            'bytesize': bytesize,
            'timeout': timeout,
            'unit_id': unit_id
        })
        
        # If we have an active client, log a warning that reconnection is needed
        global client
        if client and client.is_socket_open():
            logger.warning("Configuration updated but client is still connected with old settings. Reconnect to apply changes.")
            
    return current_config


@app.callback(
    [Output("connection-status", "children"),
     Output("interval-component", "disabled"),
     Output("interval-component", "interval"),
     Output("disconnect-btn", "style"),
     Output("port-status", "children")],
    Input("connect-btn", "n_clicks"),
    [State("com-port", "value"),
     State("current-config", "data"),
     State("poll-interval", "value")],
    prevent_initial_call=True
)
def connect_modbus(n_clicks, port, config, poll_interval):
    global client
    logger.info(f"Attempting to connect to port {port} with config {config}")
    
    if not port:
        logger.warning("No port selected")
        return [
            dbc.Alert("Please select a serial port.", color="warning"), 
            True, 
            2000,
            {"display": "none"},
            ""
        ]

    # First, close any existing connection
    if client:
        try:
            logger.info("Closing existing connection")
            client.close()
        except Exception as e:
            logger.error(f"Error closing existing connection: {str(e)}")
            logger.error(traceback.format_exc())

    # Add a small delay to allow the port to be released
    time.sleep(0.5)
    
    # Check if the port physically exists before attempting to connect
    try:
        if os.name == 'posix':  # Linux/macOS
            if not os.path.exists(port):
                logger.error(f"Port {port} does not exist physically")
                return [
                    dbc.Alert(f"❌ Port {port} doesn't exist. USB device may be disconnected.", color="danger"), 
                    True, 
                    2000,
                    {"display": "none"},
                    ""
                ]
        # For Windows, we'll catch any issues in the connection attempt
    except Exception as e:
        logger.error(f"Error checking if port exists: {str(e)}")

    # Now try to connect
    try:
        logger.info(f"Creating ModbusSerialClient with settings: {config}")
        client = ModbusSerialClient(
            port=port,
            baudrate=config['baudrate'],
            parity=config['parity'],
            stopbits=config['stopbits'],
            bytesize=config['bytesize'],
            timeout=config['timeout']
        )
        
        # Try multiple times to connect (handle resource temporarily unavailable)
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.info(f"Connection attempt {attempt+1}/{max_attempts}")
                if client.connect():
                    # Successfully connected
                    interval_ms = poll_interval * 1000
                    port_info = f"Connected to {port} - {config['baudrate']} baud, {config['bytesize']}{config['parity']}{config['stopbits']}"
                    logger.info(f"Successfully connected: {port_info}")
                    return [
                        dbc.Alert("✅ Connected!", color="success"), 
                        False, 
                        interval_ms,
                        {"display": "block"},  # Show disconnect button
                        dbc.Alert(port_info, color="info")
                    ]
                else:
                    error_msg = None
                    if hasattr(client, 'last_error') and client.last_error:
                        error_msg = str(client.last_error)
                        logger.error(f"Connection error: {error_msg}")
                    
                    # If we've tried all attempts
                    if attempt == max_attempts - 1:
                        logger.error(f"Failed to connect after {max_attempts} attempts")
                        error_hint = ""
                        
                        # Provide specific hints based on error patterns
                        if error_msg:
                            if "Permission denied" in error_msg:
                                if os.name == 'posix' and os.uname().sysname == 'Linux':
                                    error_hint = " Check permissions or try: sudo chmod 666 " + port
                                else:
                                    error_hint = " Check if another program is using the port."
                            elif "Device not configured" in error_msg or "Resource busy" in error_msg:
                                error_hint = " Try unplugging and reconnecting the USB device."
                        
                        return [
                            dbc.Alert(f"❌ Could not connect to {port}.{error_hint}", color="danger"), 
                            True, 
                            2000,
                            {"display": "none"},  # Hide disconnect button
                            ""
                        ]
                    logger.warning(f"Connection attempt {attempt+1} failed, retrying in 1 second")
                    time.sleep(1)  # Wait before retrying
            except OSError as e:
                error_msg = str(e)
                logger.error(f"OS Error during connection attempt {attempt+1}: {error_msg}")
                logger.error(traceback.format_exc())
                
                # If it's the "Resource temporarily unavailable" error
                if "[Errno 35]" in error_msg and attempt < max_attempts - 1:
                    logger.info(f"Resource temporarily unavailable, waiting 1.5 seconds before retry")
                    time.sleep(1.5)  # Wait longer before retrying
                    continue
                elif "[Errno 16]" in error_msg:  # Device busy
                    logger.info("Device busy error, trying to reset port")
                    time.sleep(2)  # Wait longer
                    continue
                elif attempt == max_attempts - 1:
                    logger.error(f"Final attempt failed with OS Error: {error_msg}")
                    
                    # Provide helpful error messages for common issues
                    error_tip = ""
                    if "Permission denied" in error_msg:
                        if os.name == 'posix' and not os.uname().sysname == 'Darwin':  # Linux
                            error_tip = " Try running with sudo or add user to 'dialout' group."
                    elif "No such file or directory" in error_msg:
                        error_tip = " Device may have been disconnected."
                    elif "Resource busy" in error_msg or "Device or resource busy" in error_msg:
                        error_tip = " Another program may be using the port. Close other applications or try a different port."
                    
                    return [
                        dbc.Alert(f"❌ Error: {error_msg}.{error_tip}", color="danger"), 
                        True, 
                        2000,
                        {"display": "none"},  # Hide disconnect button
                        ""
                    ]
        
        # This is outside the for loop but still inside the try block
        logger.error("Connection failed after multiple attempts")
        return [
            dbc.Alert("❌ Connection failed after multiple attempts. Try different settings or restart the device.", color="danger"), 
            True, 
            2000,
            {"display": "none"},  # Hide disconnect button
            ""
        ]
                
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Exception during connection: {error_msg}")
        logger.error(traceback.format_exc())
        
        # Provide targeted troubleshooting advice
        additional_info = ""
        if "could not open port" in error_msg.lower():
            additional_info = " The port may not exist or could be in use by another application."
        elif "timeout" in error_msg.lower():
            additional_info = " Device is not responding. Check wiring and protocol settings."
        
        return [
            dbc.Alert(f"❌ Error: {error_msg}.{additional_info}", color="danger"), 
            True, 
            2000,
            {"display": "none"},  # Hide disconnect button
            ""
        ]


@app.callback(
    [Output("register-table", "children"),
     Output("connection-status", "children", allow_duplicate=True),
     Output("interval-component", "disabled", allow_duplicate=True),
     Output("poll-interval", "value", allow_duplicate=True),
     Output("suggested-interval-display", "children")],  # Added output for suggested interval display
    [Input("interval-component", "n_intervals"),
     Input("add-register-btn", "n_clicks"),
     Input("register-type-filter", "value")],
    [State("new-register-addr", "value"),
     State("new-register-name", "value"),
     State("new-register-type", "value"),
     State("current-config", "data"),
     State("poll-interval", "value")],
    prevent_initial_call=True
)
def update_table(n_intervals, add_clicks, register_type_filter, 
                 new_addr, new_name, new_type, config, current_poll_interval):
    global client, renamed_vars, REGISTER_MAP, last_read_duration
    
    # Start timing the read operation
    start_time = time.time()

    trigger_id = ctx.triggered_id if ctx.triggered else None
    #logger.debug(f"update_table called. Trigger: {trigger_id}, intervals: {n_intervals}")
    
    # Handle adding a new register
    if trigger_id == "add-register-btn" and new_addr is not None and new_name:
        logger.info(f"Adding new register - Address: {new_addr}, Name: {new_name}, Type: {new_type}")
        REGISTER_MAP[new_addr] = {'name': new_name, 'type': new_type}
        renamed_vars[new_addr] = new_name
    
    rows = []
    header = dbc.Row([
        dbc.Col("Register", width=1),
        dbc.Col("Name", width=3),
        dbc.Col("Type", width=1),
        #dbc.Col("Multiplier", width=1),
        dbc.Col("Value", width=4),
        dbc.Col("Actions", width=1)
    ], className="fw-bold mb-2 border-bottom pb-2")
  
    rows.append(header)

    # Empty suggested display (default)
    suggested_display = ""

    if not client:
        logger.warning("Modbus client not initialized")
        rows.append(html.Div([dbc.Alert("Client not initialized", color="danger")]))
        return [html.Div(rows), dash.no_update, dash.no_update, dash.no_update, suggested_display]

    # Check if client is still connected first
    if not client.is_socket_open():
        logger.warning("Socket not open, attempting to reconnect")
        try:
            # Try to reconnect
            if not client.connect():
                logger.error("Failed to reconnect to device")
                rows.append(dbc.Alert("Lost connection to device. Attempting to reconnect...", color="warning"))
                return [html.Div(rows), dbc.Alert("❌ Connection lost", color="danger"), True, dash.no_update, suggested_display]
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error during reconnection attempt: {error_msg}")
            logger.error(traceback.format_exc())
            rows.append(dbc.Alert(f"Connection error: {error_msg}", color="danger"))
            return [html.Div(rows), dbc.Alert("❌ Connection error", color="danger"), True, dash.no_update, suggested_display]

    # Now read registers since we know we're connected
    try:
        connection_errors = 0
        #logger.debug(f"Reading {len(REGISTER_MAP)} registers")
        
        # Filter registers by type if needed
        filtered_registers = REGISTER_MAP.items()
        if register_type_filter != "all":
            filtered_registers = [(addr, reg) for addr, reg in REGISTER_MAP.items() 
                                 if reg['type'] == register_type_filter]
        
        for address, register_info in sorted(filtered_registers):
            try:
                register_type = register_info['type']
                #logger.debug(f"Reading register {address} of type {register_type} with unit ID {config['unit_id']}")
                
                # Use our version-compatible read function
                result = read_modbus_register(client, address, config['unit_id'], register_type)
                
                if result and not result.isError():
                    # Handle different register types differently
                    if register_type in ['Holding', 'Input']:
                        value = result.registers[0]
                        
                        # If this register is selected for graphing, store its data
                        if address in GRAPH_DATA:
                            # Get register multiplier with default of 1 if not specified
                            register_multiplier = register_info.get('multiplier', 1) if isinstance(register_info, dict) else 1
                            # Apply multiplier to the value
                            scaled_value = value * register_multiplier
                            # Store timestamp and value
                            current_time = datetime.now()
                            GRAPH_DATA[address]['times'].append(current_time)
                            GRAPH_DATA[address]['values'].append(scaled_value)
                    
                            # Limit the number of data points
                            if len(GRAPH_DATA[address]['times']) > MAX_DATA_POINTS:
                                GRAPH_DATA[address]['times'].popleft()
                                GRAPH_DATA[address]['values'].popleft()
                    else:  # coil or discrete_input
                        value = "ON" if result.bits[0] else "OFF"
                    
                   # logger.debug(f"Register {address} value: {value}")
                else:
                    error_info = result.message if hasattr(result, 'message') else "Unknown error"
                    logger.warning(f"Error reading register {address}: {error_info}")
                    value = "⚠️ Error"
                    connection_errors += 1
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Exception reading register {address}: {error_msg}")
                logger.error(traceback.format_exc())
                value = "⚠️ Error"
                connection_errors += 1
                
            # Get register name
            register_name = register_info['name'] if isinstance(register_info, dict) else register_info
            
            # Get register multiplier with default of 1 if not specified
            register_multiplier = register_info.get('multiplier', 1) if isinstance(register_info, dict) else 1

            if register_type in ['Holding', 'Input']:
                # Apply multiplier to the displayed value for registers
                display_value = value if value == "⚠️ Error" else value * register_multiplier
    
                # Format the display value to limit decimal places
                formatted_display_value = value if value == "⚠️ Error" else f"{display_value:.2f}"
    
                # Get unit of measure (if available)
                unit = register_info.get('unit', '')
    
                # Format display with unit
                if unit:
                    value_with_unit = f"{formatted_display_value} {unit}"
                else:
                    value_with_unit = formatted_display_value
    
                # Add binary representation for integer values with bit descriptions
                bits_display = []
                if isinstance(value, int) and value != "⚠️ Error":
                    # Convert to binary and format as 16 bits
                    bits = format(value, '016b')
                    binary_display = f"{bits}"

                    # Check if we should show bit definitions
                    show_bits = address in BIT_DISPLAY_SETTINGS and BIT_DISPLAY_SETTINGS[address].get("show_bits", True)

                    # Add bit descriptions if available and enabled
                    if address in BIT_DEFINITIONS and show_bits:
                        # Create bit display with tooltips/descriptions
                        for i, bit in enumerate(reversed(bits)):  # Reverse to start from bit 0 (LSB)
                            bit_position = i
                            bit_value = bit == '1'
                
                            # Check if this bit has a definition
                            if bit_position in BIT_DEFINITIONS[address]:
                                bit_desc = BIT_DEFINITIONS[address][bit_position]
                    
                                # Style based on value
                                status_style = {'color': 'green', 'fontWeight': 'bold'} if bit_value else {'color': 'red', 'fontWeight': 'bold'}
                                status_text = "ON" if bit_value else "OFF"
                    
                                # Show all bits with definitions, regardless of value
                                bits_display.append(html.Div([
                                    html.Span(f"Bit {bit_position} {bit_desc}: "), 
                                    html.Span(f" {status_text}", style=status_style),
                                ], style={'fontSize': '14px', 'marginBottom': '2px'}))
                else:
                    binary_display = ""
    
                if register_type == 'Holding':
                    # For holding registers, include numeric input and write button
                    value_display = html.Div([
                        html.Div([
                            html.Span(f"Value: {value_with_unit}", 
                                     style={'fontFamily': 'monospace', 'fontSize': '18px'}),
                            html.Br(),          
                            html.Span(f"Binary: {binary_display}", 
                                     style={'fontFamily': 'monospace', 'fontSize': '14px'}),
                            # Add the bit descriptions if any
                            html.Div(bits_display) if bits_display else None,  
                        ], style={'marginBottom': '5px', 'width': '60%'}),
                            dcc.Input(
                                id={'type': 'value-input', 'index': address},
                                type="number",
                                value="",
                                className="form-control",
                                style={'width': '25%', 'display': 'inline-block'}
                            ),
                            dbc.Button(
                                "Write", 
                                id={'type': 'write-btn', 'index': address},
                                color="primary",
                                size="md",
                                className="ms-2",
                                style={'width': '15%', 'display': 'inline-block'}
                            )

                    ], style={'display': 'flex', 'alignItems': 'center', 'width': '100%'})
                else:  # Input registers (read-only)
                    value_display = html.Div([
                        html.Span(f"Value: {value_with_unit}", 
                                 style={'fontFamily': 'monospace', 'fontSize': '18px'}),
                        html.Br(),          
                        html.Span(f"Binary: {binary_display}", 
                                 style={'fontFamily': 'monospace', 'fontSize': '14px'}),
                        # Add the bit descriptions if any
                        html.Div(bits_display) if bits_display else None,
                    ], style={'width': '100%'})



            elif register_type == 'Coil':
                # For coils, use a toggle switch
                is_on = True if value == "ON" or value == True else False
                value_display = html.Div([
                    html.Div(f"{value}", style={'width': '45%', 'display': 'inline-block'}),
                    dbc.Switch(
                        id={'type': 'coil-switch', 'index': address},
                        value=is_on,
                        className="me-2",
                        style={'width': '40%', 'display': 'inline-block'}
                    ),
                    dbc.Button(
                        "Write", 
                        id={'type': 'coil-write-btn', 'index': address},
                        color="primary",
                        size="md",
                        className="ms-2",
                        style={'width': '15%', 'display': 'inline-block'}
                    ),
                ], style={'display': 'flex', 'alignItems': 'center', 'width': '100%'})
            else:  # For discrete inputs (read-only)
                # Just show value as text
                value_display = html.Div(value, style={'padding': '6px 0'})
            
            rows.append(
                dbc.Row([
                    dbc.Col(f"{address}", width=1),
                    dbc.Col(dcc.Input(
                        id={'type': 'name-input', 'index': address},
                        value=renamed_vars.get(address, register_name),
                        debounce=True,
                        className="form-control"
                    ), width=3),
                    dbc.Col(
                        dcc.Dropdown(
                            id={'type': 'type-dropdown', 'index': address},
                            options=REGISTER_TYPE_OPTIONS,
                            value=register_info['type'] if isinstance(register_info, dict) else "Holding",
                            clearable=False,
                            className="form-control"
                        ),
                        width=1
                    ),
                    #dbc.Col(register_multiplier, width=1),
                    dbc.Col(value_display, width=4),
                    dbc.Col(dbc.Button(
                        "🗑️", 
                        id={'type': 'delete-btn', 'index': address},
                        color="danger",
                        size="sm"
                    ), width=1)
                ], className="mb-2")
            )
        
        # If all registers failed, we likely have a connection issue
        if connection_errors == len(filtered_registers) and len(filtered_registers) > 0:
            logger.error(f"All {len(filtered_registers)} register reads failed - probable connection issue")
            return [html.Div(rows), dbc.Alert("❌ Communication errors", color="danger"), dash.no_update, dash.no_update, suggested_display]
            
    except ModbusException as e:
        error_msg = str(e)
        logger.error(f"Modbus exception during register reads: {error_msg}")
        logger.error(traceback.format_exc())
        rows.append(dbc.Alert(f"Modbus error: {error_msg}", color="danger"))
        # Don't disable interval - keep trying
        return [html.Div(rows), dbc.Alert(f"❌ Modbus error: {error_msg}", color="danger"), dash.no_update, dash.no_update, suggested_display]

    if connection_errors > 0:
        logger.warning(f"{connection_errors} out of {len(filtered_registers)} register reads failed")
    else:
        logger.debug("All register reads successful")
    
    # Calculate the suggested polling interval
    suggested_interval = adjust_polling_interval(start_time)
    
    # Format the suggested interval display with explanation
    if last_read_duration > 0:
        suggested_display = html.Div([
            html.Span(f"Last read time: {last_read_duration:.3f}s", className="me-2"),
            html.Span(f"Suggested interval: {suggested_interval:.1f}s", 
                      style={"fontWeight": "bold", "color": "blue"})
        ])
    
    # Check if we should update the polling interval
    if (last_read_duration == 0 or 
        abs(suggested_interval - current_poll_interval) / current_poll_interval > 0.1):
        return [html.Div(rows), dash.no_update, dash.no_update, suggested_interval, suggested_display]
    else:
        return [html.Div(rows), dash.no_update, dash.no_update, dash.no_update, suggested_display]

     
@app.callback(
    Output("interval-component", "interval", allow_duplicate=True),
    Input("poll-interval", "value"),
    prevent_initial_call=True
)
def update_polling_interval(poll_interval):
    """Update the polling interval when the value changes"""
    logger.info(f"Updating polling interval to {poll_interval}s")
    # Convert to milliseconds for the interval component
    interval_ms = max(poll_interval, min_polling_interval) * 1000
    return interval_ms

    

@app.callback(
    Output({'type': 'name-input', 'index': dash.ALL}, 'value'),
    Input({'type': 'name-input', 'index': dash.ALL}, 'value'),
    State({'type': 'name-input', 'index': dash.ALL}, 'id'),
    prevent_initial_call=True
)
def update_names(values, ids):
    # logger.debug(f"update_names called with {len(values)} values")
    
    try:
        for val, id_dict in zip(values, ids):
            register_index = id_dict['index']
            logger.info(f"Updating register {register_index} name to '{val}'")
            renamed_vars[register_index] = val
            
            # Update the name in REGISTER_MAP
            if register_index in REGISTER_MAP:
                if isinstance(REGISTER_MAP[register_index], dict):
                    REGISTER_MAP[register_index]['name'] = val
                else:
                    # If it's still using the old format, convert to new format
                    REGISTER_MAP[register_index] = {'name': val, 'type': 'Holding'}
        
        return values
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error updating register names: {error_msg}")
        logger.error(traceback.format_exc())
        return values  # Return original values in case of error

@app.callback(
    Output({'type': 'type-dropdown', 'index': dash.ALL}, 'value'),
    Input({'type': 'type-dropdown', 'index': dash.ALL}, 'value'),
    State({'type': 'type-dropdown', 'index': dash.ALL}, 'id'),
    prevent_initial_call=True
)
def update_register_types(values, ids):
     # logger.debug(f"update_register_types called with {len(values)} values")
    
    try:
        for val, id_dict in zip(values, ids):
            register_index = id_dict['index']
           # logger.info(f"Updating register {register_index} type to '{val}'")
            
            # Update the type in REGISTER_MAP
            if register_index in REGISTER_MAP:
                if isinstance(REGISTER_MAP[register_index], dict):
                    REGISTER_MAP[register_index]['type'] = val
                else:
                    # If it's still using the old format, convert to new format
                    REGISTER_MAP[register_index] = {'name': REGISTER_MAP[register_index], 'type': val}
        
        return values
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error updating register types: {error_msg}")
        logger.error(traceback.format_exc())
        return values  # Return original values in case of error

@app.callback(
    Output("register-table", "children", allow_duplicate=True),
    Input({'type': 'delete-btn', 'index': dash.ALL}, 'n_clicks'),
    State({'type': 'delete-btn', 'index': dash.ALL}, 'id'),
    prevent_initial_call=True
)
def delete_register(n_clicks, ids):
    global REGISTER_MAP, renamed_vars
    
    if not n_clicks or not any(n_clicks):
        return dash.no_update
    
    # Find the button that was clicked
    for i, clicks in enumerate(n_clicks):
        if clicks:
            register_index = ids[i]['index']
            logger.info(f"Deleting register {register_index}")
            
            # Remove the register from both dictionaries
            if register_index in REGISTER_MAP:
                del REGISTER_MAP[register_index]
            if register_index in renamed_vars:
                del renamed_vars[register_index]
    
    # Trigger a refresh of the table
    return dash.no_update

# Add this after the client variable definition
# Store time-series data for graphing
GRAPH_DATA = {}  # Dictionary to store graph data by register address
MAX_DATA_POINTS = 10000  # Maximum number of data points to keep for each register

@app.callback(
    Output("graph-register-select", "value", allow_duplicate=True),
    Input("graph-register-select", "value"),
    prevent_initial_call=True
)
def initialize_graph_data(selected_registers):
    """Initialize data structures when registers are selected for graphing"""
    global GRAPH_DATA
    
    if not selected_registers:
        return selected_registers
    
    # Make sure selected_registers is a list
    if not isinstance(selected_registers, list):
        selected_registers = [selected_registers]
    
    # Initialize data for newly selected registers
    for register in selected_registers:
        if register not in GRAPH_DATA:
            GRAPH_DATA[register] = {
                'times': deque(maxlen=MAX_DATA_POINTS),
                'values': deque(maxlen=MAX_DATA_POINTS)
            }
    
    return selected_registers

# Callback to add bit definitions
@app.callback(
    [Output("bit-definitions-table", "children"),
     Output("bit-position-input", "value"),
     Output("bit-description-input", "value")],
    Input("add-bit-def-btn", "n_clicks"),
    [State("bit-register-select", "value"),
     State("bit-position-input", "value"),
     State("bit-description-input", "value")],
    prevent_initial_call=True
)
def add_bit_definition(n_clicks, register, bit_position, description):
    global BIT_DEFINITIONS
    
    if not n_clicks or register is None or bit_position is None or not description:
        return update_bit_definitions_table(register), dash.no_update, dash.no_update
    
    # Initialize dictionary for this register if needed
    if register not in BIT_DEFINITIONS:
        BIT_DEFINITIONS[register] = {}
    
    # Add or update bit definition
    BIT_DEFINITIONS[register][bit_position] = description
    logger.info(f"Added bit definition for register {register}, bit {bit_position}: {description}")
    
    # Return updated table and clear inputs
    return update_bit_definitions_table(register), None, ""

# Helper function to create bit definitions table
def update_bit_definitions_table(register):
    if register is None or register not in BIT_DEFINITIONS:
        return html.Div("No bit definitions for this register")
    
    # Create table of current bit definitions
    rows = []
    header = dbc.Row([
        dbc.Col("Bit", width=1),
        dbc.Col("Description", width=5),
        dbc.Col("Actions", width=1)
    ], className="fw-bold mb-2")
    rows.append(header)
    
    for bit, desc in sorted(BIT_DEFINITIONS[register].items()):
        rows.append(dbc.Row([
            dbc.Col(f"{bit}", width=1),
            dbc.Col(desc, width=5),
            dbc.Col(
                dbc.Button(
                    "🗑️",
                    id={'type': 'delete-bit-btn', 'register': register, 'bit': bit},
                    color="danger",
                    size="sm"
                ),
                width=1
            )
        ], className="mb-1"))
    
    return html.Div(rows)

# Callback to update bit definitions dropdown when register map changes
@app.callback(
    Output("bit-register-select", "options"),
    [Input("register-table", "children"),
     Input("upload-csv", "contents")]
)
def update_bit_register_options(table_children, csv_upload):
    options = [{'label': f"{addr}: {reg['name']}", 'value': addr} 
               for addr, reg in REGISTER_MAP.items()
               if reg['type'] in ['Holding', 'Input']]
    return sorted(options, key=lambda x: x['value'])

# Callback to delete bit definitions
@app.callback(
    Output("bit-definitions-table", "children", allow_duplicate=True),
    Input({'type': 'delete-bit-btn', 'register': dash.ALL, 'bit': dash.ALL}, 'n_clicks'),
    State({'type': 'delete-bit-btn', 'register': dash.ALL, 'bit': dash.ALL}, 'id'),
    prevent_initial_call=True
)
def delete_bit_definition(n_clicks, ids):
    if not n_clicks or not any(n_clicks):
        return dash.no_update
    
    # Find which button was clicked
    for i, clicks in enumerate(n_clicks):
        if clicks:
            register = ids[i]['register']
            bit = ids[i]['bit']
            
            # Remove the bit definition
            if register in BIT_DEFINITIONS and bit in BIT_DEFINITIONS[register]:
                del BIT_DEFINITIONS[register][bit]
                logger.info(f"Deleted bit definition for register {register}, bit {bit}")
                
                # If no more definitions for this register, remove the register entry
                if not BIT_DEFINITIONS[register]:
                    del BIT_DEFINITIONS[register]
    
    # Return updated table for the currently selected register
    ctx_inputs = dash.callback_context.inputs
    triggered_id = list(ctx_inputs.keys())[0] if ctx_inputs else None
    
    if triggered_id:
        # Extract register from the ID of the clicked button
        import json
        id_dict = json.loads(triggered_id.split('.')[0])
        register = id_dict.get('register')
        return update_bit_definitions_table(register)
    
    return dash.no_update

# Callback to toggle bit definitions display
@app.callback(
    Output("show-bits-switch", "value"),
    [Input("show-bits-switch", "value"),
     Input("bit-register-select", "value")],
    prevent_initial_call=True
)
def toggle_bit_display(show_value, register):
    global BIT_DISPLAY_SETTINGS
    
    # Handle direct toggle by switch
    if ctx.triggered_id == "show-bits-switch" and register is not None:
        # Initialize settings for this register if needed
        if register not in BIT_DISPLAY_SETTINGS:
            BIT_DISPLAY_SETTINGS[register] = {}
            
        # Update the show_bits setting
        BIT_DISPLAY_SETTINGS[register]["show_bits"] = show_value
        logger.info(f"Set bit display for register {register} to {show_value}")
        
    # Handle register selection change
    elif ctx.triggered_id == "bit-register-select" and register is not None:
        # Return current setting or default to True
        if register in BIT_DISPLAY_SETTINGS:
            return BIT_DISPLAY_SETTINGS[register].get("show_bits", True)
        return True
        
    return show_value

@app.callback(
    Output("graph-register-select", "options"),
    [Input("register-table", "children"),
     Input("upload-csv", "contents")]
)
def update_graph_register_options(table_children, csv_upload):
    """Update the dropdown options for graphing based on current register map"""
    options = []
    
    # Only include Holding and Input registers (numerical values)
    for address, register_info in REGISTER_MAP.items():
        if register_info['type'] in ['Holding', 'Input']:
            options.append({
                'label': f"{address}: {register_info['name']}",
                'value': address
            })
    
    return sorted(options, key=lambda x: x['value'])

# Add this callback to update the graph with new data
@app.callback(
    Output("register-graph", "figure"),
    [Input("interval-component", "n_intervals"),
     Input("graph-register-select", "value"),
     Input("clear-graph-btn", "n_clicks")]
)
def update_graph(n_intervals, selected_registers, clear_clicks):
    """Update the graph with the latest data for selected registers"""
    global GRAPH_DATA
    
    # Initialize the figure
    fig = go.Figure()
    
    # Clear graph data if clear button was clicked
    if ctx.triggered_id == "clear-graph-btn" and clear_clicks:
        GRAPH_DATA = {}
        return fig
    
    # If no registers selected, return empty figure
    if not selected_registers:
        return fig
    
    # Make sure selected_registers is a list
    if not isinstance(selected_registers, list):
        selected_registers = [selected_registers]
    
    # Initialize data structures for registers if they don't exist
    for register in selected_registers:
        if register not in GRAPH_DATA:
            GRAPH_DATA[register] = {
                'times': deque(maxlen=MAX_DATA_POINTS),
                'values': deque(maxlen=MAX_DATA_POINTS)
            }
    
    # Remove data for registers no longer selected
    for register in list(GRAPH_DATA.keys()):
        if register not in selected_registers:
            del GRAPH_DATA[register]
    
    # Add a trace for each selected register
    for register in selected_registers:
        if register in GRAPH_DATA and len(GRAPH_DATA[register]['times']) > 0:
            register_name = REGISTER_MAP[register]['name'] if register in REGISTER_MAP else f"Register {register}"
            
            fig.add_trace(go.Scatter(
                x=list(GRAPH_DATA[register]['times']),
                y=list(GRAPH_DATA[register]['values']),
                mode='lines+markers',
                name=f"{register}: {register_name}"
            ))
    
    # Update layout
    fig.update_layout(
        title="Register Values Over Time",
        xaxis_title="Time",
        yaxis_title="Value",
        legend_title="Registers",
        margin=dict(l=40, r=40, t=40, b=40),
        hovermode="closest",
        height=400
    )
    
    return fig

# 5. Improved CSV export callback with better error handling
@app.callback(
    Output("download-graph-csv", "data"),
    Input("export-graph-csv-btn", "n_clicks"),  # Fixed button ID
    State("graph-register-select", "value"),
    prevent_initial_call=True
)
def export_graph_data_as_csv(n_clicks, selected_registers):
    # Keep existing function implementation
    # (Make sure to fix the PreventUpdate import if needed)
    if not n_clicks or not selected_registers:
        from dash.exceptions import PreventUpdate
        raise PreventUpdate
    
    try:
        # Make sure selected_registers is a list
        if not isinstance(selected_registers, list):
            selected_registers = [selected_registers]
        
        # Check if we have any data to export
        has_data = False
        for register in selected_registers:
            if register in GRAPH_DATA and len(GRAPH_DATA[register]['times']) > 0:
                has_data = True
                break
        
        if not has_data:
            logger.warning("No data to export to CSV")
            # Return a simple CSV with headers but no data
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return dict(
                content="No data available for selected registers",
                filename=f"modbus_data_empty_{timestamp}.txt",
                type="text/plain",
            )
        
        # Create a consolidated DataFrame with all register data
        data_dict = {"Timestamp": []}
        
        # Add data for each register
        for register in selected_registers:
            if register in GRAPH_DATA and len(GRAPH_DATA[register]['times']) > 0:
                register_name = f"{register}_{REGISTER_MAP[register]['name']}" if register in REGISTER_MAP else f"Register_{register}"
                
                # Convert times to strings to avoid JSON serialization issues
                formatted_times = [t.strftime('%Y-%m-%d %H:%M:%S.%f') for t in GRAPH_DATA[register]['times']]
                
                # Add formatted times and values to the data dictionary
                if not data_dict["Timestamp"]:
                    data_dict["Timestamp"] = formatted_times
                
                data_dict[register_name] = list(GRAPH_DATA[register]['values'])
        
        # Create a proper CSV string using pandas
        # Convert to DataFrame and then to CSV
        if data_dict["Timestamp"]:
            df = pd.DataFrame(data_dict)
            csv_string = df.to_csv(index=False)
            
            # Generate timestamp for filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"modbus_data_{timestamp}.csv"
            
            logger.info(f"Successfully created CSV with {len(df)} rows")
            
            return dict(
                content=csv_string,
                filename=filename,
                type="text/csv",
            )
        else:
            # Fallback if no timestamps were collected
            return dict(
                content="No timestamp data available for selected registers",
                filename="modbus_data_empty.txt",
                type="text/plain",
            )
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error exporting data as CSV: {error_msg}")
        logger.error(traceback.format_exc())
        # Return an error text file
        return dict(
            content=f"Error exporting data: {error_msg}",
            filename="export_error.txt",
            type="text/plain",
        )

# 6. Update the status callback to be more informative
@app.callback(
    Output("export-status", "children"),
    Input("export-graph-csv-btn", "n_clicks"),
    [State("graph-register-select", "value"),
     State("register-graph", "figure")],
    prevent_initial_call=True
)
def update_export_status(png_clicks, csv_clicks, selected_registers, figure):
    """Display status messages for export operations"""
    ctx_triggered = ctx.triggered_id if ctx.triggered else None
    
    if not ctx_triggered:
        return dash.no_update
    
    if ctx_triggered == "export-graph-csv-btn":  # Make sure this matches your button ID
        if not selected_registers:
            return dbc.Alert("No registers selected. Please select registers from the dropdown.", color="warning")
        
        # Check if we have any data to export
        has_data = False
        for register in selected_registers if isinstance(selected_registers, list) else [selected_registers]:
            if register in GRAPH_DATA and len(GRAPH_DATA[register]['times']) > 0:
                has_data = True
                break
        
        if not has_data:
            return dbc.Alert("No data available for the selected registers. Please wait for data collection.", color="warning")
        
        return dbc.Alert("Starting CSV export. If download doesn't appear, check browser settings.", color="success")
    
    return dash.no_update

# Ensure proper cleanup when application exits
def signal_handler(sig, frame):
    global client
    logger.info(f"Signal {sig} received, shutting down...")
    if client:
        try:
            logger.info("Closing Modbus connection before exit")
            client.close()
            logger.info("Connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing connection during shutdown: {str(e)}")
    logger.info("Exiting application")
    sys.exit(0)
    
    
    



# Register signal handlers for clean shutdown
signal.signal(signal.SIGINT, signal_handler)  # Handle Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Handle termination signal

# Add a cleanup function to release port on exit
def cleanup_on_exit():
    global client
    logger.info("Cleanup on exit called")
    if client:
        try:
            logger.info("Closing Modbus connection")
            client.close()
            logger.info("Modbus connection closed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            logger.error(traceback.format_exc())
    else:
        logger.info("No active client to close during cleanup")

# Add this near the top of the script where other constants are defined
DEFAULT_REGISTER_MAP_CSV = "register_map_default.csv"

# Then update the main code to load from this CSV on startup if it exists
if __name__ == '__main__':
    # Register the cleanup function to be called on exit
    import atexit
    atexit.register(cleanup_on_exit)
    
    logger.info("Starting Modbus RTU Web Viewer application")
    logger.info(f"Using {'unit' if USE_UNIT_PARAMETER else 'slave'} parameter based on pymodbus version detection")
    
    # Try to load register map from default CSV if it exists
    if os.path.exists(DEFAULT_REGISTER_MAP_CSV):
        logger.info(f"Loading default register map from {DEFAULT_REGISTER_MAP_CSV}")
        try:
            REGISTER_MAP = load_register_map_from_csv(DEFAULT_REGISTER_MAP_CSV)
            renamed_vars = {k: v['name'] for k, v in REGISTER_MAP.items()}
            logger.info(f"Loaded {len(REGISTER_MAP)} registers from default CSV")
        except Exception as e:
            logger.error(f"Error loading default register map: {str(e)}")
            # Continue with the hardcoded register map in this case
    else:
        logger.info(f"Default register map CSV not found: {DEFAULT_REGISTER_MAP_CSV}")
        logger.info("Using built-in register map")
    
    try:
        logger.info("Starting Dash server")
        app.run(debug=True)
    except Exception as e:
        error_msg = str(e)
        logger.critical(f"Error running app: {error_msg}")
        logger.critical(traceback.format_exc())
        cleanup_on_exit()
    
    logger.info("Application shutdown complete")
