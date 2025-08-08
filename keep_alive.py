from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route("/", methods=["GET", "HEAD"])
def index():
    return "✅ Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080, debug=False)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

if __name__ == "__main__":
    print("🚀 Starting keep-alive server on port 8080...")
    app.run(host="0.0.0.0", port=8080, debug=False)
