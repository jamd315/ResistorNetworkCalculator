import math
import itertools
from dataclasses import dataclass
from typing import Dict
import struct
from enum import Enum
import sqlite3

import tqdm

E6 = [1.0, 1.5, 2.2, 3.3, 4.7, 6.8]
E12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]
E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]


def generate_resistor_values(series, order=6):
    result = []
    for exp in range(order):
        result.extend(round(r * 10 ** exp, 2) for r in series)
    return result


class ResistorNetworkType(Enum):
    SINGLE_SERIES = 0
    DOUBLE_SERIES = 1
    TRIPLE_SERIES = 2
    SINGLE_PARALLEL = 3
    DOUBLE_PARALLEL = 4
    TRIPLE_PARALLEL = 5
    SINGLE_SERIES_DOUBLE_PARALLEL = 6
    DOUBLE_SERIES_SINGLE_PARALLEL = 7

# Encode a resistance into its value and order of magnitude
# The resistance is really 10 times the normal resistance, so that we can use integers
# e.g. 1.2k is encoded as (12, 3) because 12 * 10^3 = 12000
def encode_resistance(resistance):
    if resistance == 0:
        return 0, 0
    order = int(math.log10(resistance))
    resistance = int(resistance / 10 ** (order - 1))
    return resistance, order


def decode_resistance(resistance, order):
    return resistance * 10 ** (order - 1)


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
        r1, o1 = encode_resistance(self.resistors[0])
        r2, o2 = encode_resistance(self.resistors[1])
        r3, o3 = encode_resistance(self.resistors[2])
        return struct.pack(struct_fmt, self.resistance, self.configuration.value, r1, o1, r2, o2, r3, o3)
    
    @classmethod
    def decode(cls, data):
        struct_fmt = "@fBBBBBBB"  # 11 bytes per
        resistance, configuration, r1, o1, r2, o2, r3, o3 = struct.unpack(struct_fmt, data)
        configuration = ResistorNetworkType(configuration)
        resistors = (decode_resistance(r1, o1), decode_resistance(r2, o2), decode_resistance(r3, o3))
        return cls(configuration, resistors)
    
    @staticmethod
    def struct_size():
        return struct.calcsize("@fBBBBBBB")
    
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


def apply_combinatorics(resistor_values):
    combos: Dict[float, ResistorNetwork] = {}
    # Do the 3 resistors combos first, since if there are duplicates, the results with fewer resistors will overwrite them
    # n choose 3, twice
    for r_triple in itertools.combinations_with_replacement(resistor_values, 3):
        network_3s = ResistorNetwork(ResistorNetworkType.TRIPLE_SERIES, r_triple)
        combos[network_3s.resistance] = network_3s
        network_3p = ResistorNetwork(ResistorNetworkType.TRIPLE_PARALLEL, r_triple)
        combos[network_3p.resistance] = network_3p
    # n ^ 3, twice
    for r_triple in itertools.product(resistor_values, repeat=3):
        network_1s2p = ResistorNetwork(ResistorNetworkType.SINGLE_SERIES_DOUBLE_PARALLEL, r_triple)
        combos[network_1s2p.resistance] = network_1s2p
        network_2s1p = ResistorNetwork(ResistorNetworkType.DOUBLE_SERIES_SINGLE_PARALLEL, r_triple)
        combos[network_2s1p.resistance] = network_2s1p
    # n choose 2, twice
    for r_double in itertools.combinations_with_replacement(resistor_values, 2):
        r_double = (*r_double, 0)
        network_2s = ResistorNetwork(ResistorNetworkType.DOUBLE_SERIES, r_double)
        combos[network_2s.resistance] = network_2s
        network_2p = ResistorNetwork(ResistorNetworkType.DOUBLE_PARALLEL, r_double)
        combos[network_2p.resistance] = network_2p
    # n
    for r_single in resistor_values:
        r_single = (r_single, 0, 0)
        network_1s = ResistorNetwork(ResistorNetworkType.SINGLE_SERIES, r_single)
        combos[network_1s.resistance] = network_1s
    return combos


def predict_combinatorics_len(num_resistors):
    result = 0
    result += 2 * math.comb(num_resistors + 3 - 1, 3)
    result += 2 * math.comb(num_resistors + 2 - 1, 2)
    result += num_resistors
    result += 2 * num_resistors ** 3
    return result


def find_nearest_value_naive(resistor_values, target):
    return min(resistor_values, key=lambda x: abs(x - target))


def save_combos(combos, filename):
    with open(filename, "wb") as f:
        for network in combos.values():
            f.write(network.encode())
        

def generate_binaries():
    for series_name, series in tqdm.tqdm([("E6", E6), ("E12", E12), ("E24", E24)]):
        for order in [3, 6]:
            resistor_values = generate_resistor_values(series, order)
            combos = apply_combinatorics(resistor_values)
            print(f"{series_name} {order} order: {len(combos)} combos")
            save_combos(combos, f"{series_name.lower()}o{order}.bin")


def generate_database_files():
    conn = sqlite3.connect("resistor_networks.db")
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS resistor_networks")
    c.execute("CREATE TABLE resistor_networks (resistance REAL, series TEXT, configuration INTEGER, r1 INTEGER, o1 INTEGER, r2 INTEGER, o2 INTEGER, r3 INTEGER, o3 INTEGER)")
    for series_name, series in [("E6", E6), ("E12", E12), ("E24", E24)]:
        for order in [3, 6]:
            series_name_full = f"{series_name.lower()}o{order}"
            resistor_values = generate_resistor_values(series, order)
            combos = apply_combinatorics(resistor_values)
            for resistance, network in combos.items():
                r1, o1 = encode_resistance(network.resistors[0])
                r2, o2 = encode_resistance(network.resistors[1])
                r3, o3 = encode_resistance(network.resistors[2])
                c.execute("INSERT INTO resistor_networks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (resistance, series_name_full, network.configuration.value, r1, o1, r2, o2, r3, o3))
            print(f"{series_name_full} db done")
            with open(f"{series_name_full}.txt", "w") as f:
                f.write(",".join(str(x) for x in sorted(combos.keys())))
            print(f"{series_name_full} txt done")
    conn.commit()
                


def main():
    generate_database_files()


if __name__ == '__main__':
    main()
