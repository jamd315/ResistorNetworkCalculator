import time
import sqlite3
import sys

import numpy as np

from ResistorNetwork import ResistorNetwork, ResistorNetworkType

class ResistorNetworkDatabaseManager:
    def __init__(self):
        self.available_resistances = {
            "e6o3": self._load("e6o3.npy"),
            "e6o6": self._load("e6o6.npy"),
            "e12o3": self._load("e12o3.npy"),
            "e12o6": self._load("e12o6.npy"),
            "e24o3": self._load("e24o3.npy"),
            "e24o6": self._load("e24o6.npy"),
        }
        print(f"Loaded ResistorNetworkDatabase, consuming {sum(sys.getsizeof(x) for x in self.available_resistances.values())} bytes")

    def _load(self, filename) -> np.ndarray:
        return np.load(filename)
        
    def nearest_network(self, resistance: float, series_name: str) -> ResistorNetwork:
        if series_name not in self.available_resistances:
            raise ValueError(f"Invalid series name: {series_name}")
        chosen_series = self.available_resistances[series_name]
        # log(n) with a binary search
        left_idx = np.searchsorted(chosen_series, resistance)
        if (left_idx == len(chosen_series)):
            nearest_resistance = chosen_series[-1]
        else:
            nearest_resistance = min(chosen_series[left_idx], chosen_series[left_idx + 1], key=lambda x: abs(resistance - x))
        with sqlite3.connect("resistor_networks.db") as conn:
            result = conn.execute("SELECT * FROM resistor_networks WHERE resistance = ? AND series = ? LIMIT 1", (nearest_resistance, series_name))
            if not result:
                raise ValueError(f"No results for {nearest_resistance} {series_name}")
            found_resistance, series_name_full, configuration, r1, o1, r2, o2, r3, o3 = result.fetchone()
            configuration = ResistorNetworkType(configuration)
            resistors = (ResistorNetwork.decode_resistance(r1, o1), ResistorNetwork.decode_resistance(r2, o2), ResistorNetwork.decode_resistance(r3, o3))
            return ResistorNetwork(configuration, resistors)


def main():
    t0 = time.perf_counter()
    a = ResistorNetworkDatabaseManager()
    t1 = time.perf_counter()
    network = a.nearest_network(414.14, "e24o6")
    t2 = time.perf_counter()
    print(f"Loaded in {t1 - t0}s, found {network}={network.resistance} in {t2 - t1}s")


if __name__ == '__main__':
    main()
