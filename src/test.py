import time
from grafana import GrafanaLiveStreamer

streamer = GrafanaLiveStreamer()

for i in range(10):
    now_ns = time.time_ns()
    streamer.send(now_ns, {"temp": 20 + i, "pressure": 1.0 + i * 0.01})
    time.sleep(1)

streamer.close()