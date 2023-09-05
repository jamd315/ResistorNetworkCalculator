import math
import itertools
from typing import Dict
import sqlite3

import numpy as np

from ResistorNetwork import ResistorNetwork, ResistorNetworkType
from ResistorNetworkDatabaseManager import ResistorNetworkDatabaseManager

E6 = [1.0, 1.5, 2.2, 3.3, 4.7, 6.8]
E12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]
E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]


def generate_resistor_values(series, order=6):
    result = []
    for exp in range(order):
        result.extend(round(r * 10 ** exp, 2) for r in series)
    return result


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
                r1, o1 = ResistorNetwork.encode_resistance(network.resistors[0])
                r2, o2 = ResistorNetwork.encode_resistance(network.resistors[1])
                r3, o3 = ResistorNetwork.encode_resistance(network.resistors[2])
                c.execute("INSERT INTO resistor_networks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (resistance, series_name_full, network.configuration.value, r1, o1, r2, o2, r3, o3))
            arr = np.array(sorted(combos.keys()))
            np.save(f"{series_name_full}.npy", arr)
            print(f"{series_name_full} done")
    conn.commit()


def main():
    print("Building database files, this might take a while...")
    generate_database_files()


if __name__ == '__main__':
    main()
