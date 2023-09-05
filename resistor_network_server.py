import sys

import flask
from flask import request, current_app
from markupsafe import Markup

from ResistorNetwork import ResistorNetwork
from ResistorNetworkDatabaseManager import ResistorNetworkDatabaseManager

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
    app.resistor_calc = ResistorNetworkDatabaseManager()
    app.run("0.0.0.0", 80, debug=True)
