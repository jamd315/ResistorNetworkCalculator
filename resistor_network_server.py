import sys

import flask
from flask import request, current_app
from markupsafe import Markup

from resistor_combos import ResistorNetwork

app = flask.Flask(__name__)


def pretty_resistance(resistance: float) -> str:
    if resistance >= 1e6:
        return f"{resistance / 1e6:.2f}MΩ"
    elif resistance >= 1e3:
        return f"{resistance / 1e3:.2f}kΩ"
    else:
        return f"{resistance:.2f}Ω"

# Let flask use this function
@app.context_processor
def utility_processor():
    return {
        "pretty_resistance": pretty_resistance
    }


class ResistorCalc:
    def __init__(self):
        self.networks = {
            "e6o3": self._load("e6o3.bin"),
            "e6o6": self._load("e6o6.bin"),
            "e12o3": self._load("e12o3.bin"),
            "e12o6": self._load("e12o6.bin"),
            "e24o3": self._load("e24o3.bin"),
            "e24o6": self._load("e24o6.bin"),
        }

    def _load(self, filename) -> dict:
        d = {}
        with open(filename, "rb") as f:
            struct_size = ResistorNetwork.struct_size()
            while True:
                data = f.read(struct_size)
                if not data:
                    break
                network = ResistorNetwork.decode(data)
                d.update({network.resistance: network})
        return d
    
    def nearest_network(self, resistance: float, series_name: str) -> ResistorNetwork:
        if series_name not in self.networks:
            raise ValueError(f"Invalid series name: {series_name}")
        network = self.networks[series_name]
        # Naive approach
        return network[min(network.keys(), key=lambda x: abs(x - resistance))]


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        resistance = float(request.form["resistance"])
        if resistance <= 0:
            return flask.abort(400)
        series_name = request.form["series_name"]
        network = current_app.resistor_calc.nearest_network(float(resistance), series_name)
        return flask.render_template("index.html", 
                                     network=network, 
                                     resistance=resistance,
                                     svg=Markup(make_svg(network)))
    return flask.render_template("index.html")


def make_svg(network):
    configuration = network.configuration_name()
    r1, r2, r3 = network.resistors
    if configuration is None or configuration not in ["1s", "2s", "3s", "2p", "3p", "1s2p", "2s1p"]:
        return flask.abort(400)
    if r1 is None or r2 is None or r3 is None:
        return flask.abort(400)
    r1 = pretty_resistance(float(r1))
    r2 = pretty_resistance(float(r2))
    r3 = pretty_resistance(float(r3))
    return flask.render_template(f"{configuration}.svg", r1=r1, r2=r2, r3=r3)



if __name__ == "__main__":
    app.resistor_calc = ResistorCalc()
    print(sys.getsizeof(app.resistor_calc.networks["e24o6"][3.0]))
    #app.run("0.0.0.0", 80, debug=True)
