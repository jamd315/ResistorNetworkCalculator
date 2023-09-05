from dataclasses import dataclass
import math
import struct
from enum import Enum


class ResistorNetworkType(Enum):
    SINGLE_SERIES = 0
    DOUBLE_SERIES = 1
    TRIPLE_SERIES = 2
    SINGLE_PARALLEL = 3
    DOUBLE_PARALLEL = 4
    TRIPLE_PARALLEL = 5
    SINGLE_SERIES_DOUBLE_PARALLEL = 6
    DOUBLE_SERIES_SINGLE_PARALLEL = 7


@dataclass
class ResistorNetwork:
    configuration: ResistorNetworkType
    resistors: tuple
    resistance: float

    resistor_network_type_friendly_names = {
        ResistorNetworkType.SINGLE_SERIES: "1s",
        ResistorNetworkType.DOUBLE_SERIES: "2s",
        ResistorNetworkType.TRIPLE_SERIES: "3s",
        ResistorNetworkType.SINGLE_SERIES_DOUBLE_PARALLEL: "1s2p",
        ResistorNetworkType.DOUBLE_SERIES_SINGLE_PARALLEL: "2s1p",
        ResistorNetworkType.DOUBLE_PARALLEL: "2p",
        ResistorNetworkType.TRIPLE_PARALLEL: "3p",
    }

    def __init__(self, configuration, resistors):
        self.configuration = configuration
        if len(resistors) != 3:
            raise ValueError("ResistorNetwork must have 3 resistors")
        self.resistors = resistors
        self.resistance = self.calculate_resistance()

    def __len__(self):
        return len(self.resistors)
    
    def __str__(self):
        return f"{self.configuration}:{self.resistors}"
    
    def configuration_name(self) -> str:
        return self.resistor_network_type_friendly_names[self.configuration]
    
    def encode(self):
        struct_fmt = "@fBBBBBBB"  # 11 bytes per
        r1, o1 = self.encode_resistance(self.resistors[0])
        r2, o2 = self.encode_resistance(self.resistors[1])
        r3, o3 = self.encode_resistance(self.resistors[2])
        return struct.pack(struct_fmt, self.resistance, self.configuration.value, r1, o1, r2, o2, r3, o3)
    
    @classmethod
    def decode(cls, data):
        struct_fmt = "@fBBBBBBB"  # 11 bytes per
        resistance, configuration, r1, o1, r2, o2, r3, o3 = struct.unpack(struct_fmt, data)
        configuration = ResistorNetworkType(configuration)
        resistors = (cls.decode_resistance(r1, o1), cls.decode_resistance(r2, o2), cls.decode_resistance(r3, o3))
        return cls(configuration, resistors)
    
    @staticmethod
    def struct_size():
        return struct.calcsize("@fBBBBBBB")
    
    
    # Encode a resistance into its value and order of magnitude
    # The resistance is really 10 times the normal resistance, so that we can use integers
    # e.g. 1.2k is encoded as (12, 3) because 12 * 10^3 = 12000
    @staticmethod
    def encode_resistance(resistance):
        if resistance == 0:
            return 0, 0
        order = int(math.log10(resistance))
        resistance = int(resistance / 10 ** (order - 1))
        return resistance, order

    @staticmethod
    def decode_resistance(resistance, order):
        return resistance * 10 ** (order - 1)
    
    def calculate_resistance(self):
        match self.configuration:
            # All symmetrical configurations except 1s2p and 2s1p
            case ResistorNetworkType.SINGLE_SERIES | ResistorNetworkType.DOUBLE_SERIES | ResistorNetworkType.TRIPLE_SERIES:
                return sum(self.resistors)
            case ResistorNetworkType.TRIPLE_PARALLEL:
                return 1.0 / (1.0 / self.resistors[0] + 1.0 / self.resistors[1] + 1.0 / self.resistors[2])
            case ResistorNetworkType.DOUBLE_PARALLEL:
                return 1.0 / (1.0 / self.resistors[0] + 1.0 / self.resistors[1])
            case ResistorNetworkType.SINGLE_SERIES_DOUBLE_PARALLEL:  # Asymmetrical
                return self.resistors[0] + 1.0 / (1.0 / self.resistors[1] + 1.0 / self.resistors[2])
            case ResistorNetworkType.DOUBLE_SERIES_SINGLE_PARALLEL:  # Asymmetrical
                return 1.0 / (1.0 / (self.resistors[0] + self.resistors[1]) + 1 / self.resistors[2])
