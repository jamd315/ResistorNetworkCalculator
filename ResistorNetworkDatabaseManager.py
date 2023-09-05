import sqlite3
import sys

from ResistorNetwork import ResistorNetwork, ResistorNetworkType

class ResistorNetworkDatabaseManager:
    def __init__(self):
        self.available_resistances = {
            "e6o3": self._load("e6o3.txt"),
            "e6o6": self._load("e6o6.txt"),
            "e12o3": self._load("e12o3.txt"),
            "e12o6": self._load("e12o6.txt"),
            "e24o3": self._load("e24o3.txt"),
            "e24o6": self._load("e24o6.txt"),
        }
        print(f"Loaded ResistorNetworkDatabase, consuming {sum(sys.getsizeof(x) for x in self.available_resistances.values())} bytes")

    def _load(self, filename) -> list:
        with open(filename, "r") as f:
            return [float(x) for x in f.read().split(",")]
        
    def nearest_network(self, resistance: float, series_name: str) -> ResistorNetwork:
        if series_name not in self.available_resistances:
            raise ValueError(f"Invalid series name: {series_name}")
        chosen_series = self.available_resistances[series_name]
        # Naive approach, could be log(n) with a binary search but that's hard
        nearest_resistance = min(chosen_series, key=lambda x: abs(x - resistance))
        with sqlite3.connect("resistor_networks.db") as conn:
            result = conn.execute("SELECT * FROM resistor_networks WHERE resistance = ? AND series = ? LIMIT 1", (nearest_resistance, series_name))
            if not result:
                raise ValueError(f"No results for {nearest_resistance} {series_name}")
            found_resistance, series_name_full, configuration, r1, o1, r2, o2, r3, o3 = result.fetchone()
            configuration = ResistorNetworkType(configuration)
            resistors = (ResistorNetwork.decode_resistance(r1, o1), ResistorNetwork.decode_resistance(r2, o2), ResistorNetwork.decode_resistance(r3, o3))
            return ResistorNetwork(configuration, resistors)
