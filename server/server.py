#!/bin/python3

# Import builtins
import sys
import webbrowser
import os
import flask

# 127.0.0.1 is several orders of magnitude faster than localhost on Windows due to hostname resolution being absolutely ass.
host = "127.0.0.1"
port = 7974 # This port was chosen because 0x7974 is "yt" in ASCII.
url = f"http://{host}:{port}/"
root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
app = flask.Flask("YTMusicOffline")

# Flask methods and endpoints
@app.route("/api/save_database", methods=["POST"])
def update_database():
    database_path = os.path.join(root, "database", "database.json")
    database_json = flask.request.data.decode("utf-8")
    with open(database_path, "w", encoding="utf-8") as file:
        file.write(database_json)
    return flask.make_response("", 200)

@app.route("/")
def serve_slash():
    file_path = os.path.join(root, "client", "index.html")
    return serve_file(file_path)

@app.route("/<path:file_name>")
def serve_slash_filename(file_name):
    file_path = os.path.join(root, "client", file_name)
    return serve_file(file_path)

@app.route("/database/<path:file_name>")
def serve_slash_database_slash_filename(file_name):
    file_path = os.path.join(root, "database", file_name)
    return serve_file(file_path)

def serve_file(file_path):
    response = flask.send_from_directory(os.path.dirname(file_path), os.path.basename(file_path))
    response.headers.pop("Content-Disposition", None)
    response.headers.pop("Date", None)
    response.headers["Accept-Ranges"] = "bytes"
    return response

# Run server and catch errors
try:
    print(f"Hosting {root} at {url}...")
    if not webbrowser.open(url):
        if (os.system(f"start {url}") != 0):
            if (os.system(f"xdg-open {url}") != 0):
                print(f"Failed to launch {url} please open manually.")
    app.run(host=host, port=port)
except KeyboardInterrupt:
    sys.exit(0)
except:
    raise