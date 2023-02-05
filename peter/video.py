import threading
import numpy as np
import queue
from contextlib import suppress
import asyncio
import concurrent

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)

executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)

def common_gst_loop(bus):
    while True:
        msg = bus.timed_pop_filtered(
            Gst.CLOCK_TIME_NONE,
            Gst.MessageType.ERROR | Gst.MessageType.EOS | Gst.MessageType.STATE_CHANGED
        )
        if msg.type == Gst.MessageType.ERROR:
            err, debug = msg.parse_error()
            print(("Error received from element %s: %s" % (
                msg.src.get_name(), err)))
            print(("Debugging information: %s" % debug))
            break
        elif msg.type == Gst.MessageType.EOS:
            print("End-Of-Stream reached.")
            break
        elif msg.type == Gst.MessageType.STATE_CHANGED:
            if isinstance(msg.src, Gst.Pipeline):
                old_state, new_state, pending_state = msg.parse_state_changed()
                print(("Pipeline state changed from %s to %s." %
                       (old_state.value_nick, new_state.value_nick)))
                if old_state == Gst.State.PAUSED and new_state == Gst.State.READY:
                    break


class VideoCap:
    def __init__(self) -> None:
        self.pipeline = Gst.parse_launch(
            "autovideosrc sync=0 ! tee name=raw ! queue ! vtenc_h264_hw realtime=1 bitrate=8000 ! h264parse ! video/x-h264,alignment=au,stream-format=byte-stream ! appsink name=h264sink emit-signals=1 sync=0 raw. ! queue ! videoconvert ! video/x-raw,format=BGR ! appsink name=rawsink emit-signals=1 sync=0")

        h264sink = self.pipeline.get_by_name("h264sink")
        rawsink = self.pipeline.get_by_name("rawsink")

        h264sink.connect("new-sample", self.__new_h264_au, h264sink)
        rawsink.connect("new-sample", self.__new_frame, rawsink)

        self.raw_queue = queue.Queue(1)
        self.h264_queue = queue.Queue(10)

    def __new_h264_au(self, sink, data):
        # print("new h264 nal")
        sample = sink.emit("pull-sample")
        buf = sample.get_buffer()

        with suppress(queue.Full):
            self.h264_queue.put_nowait(buf.extract_dup(0, buf.get_size()))

        return Gst.FlowReturn.OK

    def __new_frame(self, sink, data):
        # print("new frame")
        sample = sink.emit("pull-sample")
        buf = sample.get_buffer()
        caps = sample.get_caps()
        height = caps.get_structure(0).get_value("height")
        width = caps.get_structure(0).get_value("width")
        arr = np.ndarray(
            (height,
             width,
             3),
            buffer=buf.extract_dup(0, buf.get_size()),
            dtype=np.uint8)

        with suppress(queue.Full):
            self.raw_queue.put_nowait(arr)

        return Gst.FlowReturn.OK

    def __gst_loop(self):
        common_gst_loop(self.pipeline.get_bus())

    def run(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        self.worker = threading.Thread(target=self.__gst_loop)
        self.worker.start()

    def stop(self):
        self.pipeline.set_state(Gst.State.READY)
        self.worker.join()

    def __enter__(self):
        self.run()
        return self

    def __exit__(self, typ, value, traceback):
        self.stop()

    def read_h264(self):
        return self.h264_queue.get()

    def read_raw(self):
        return self.raw_queue.get()
    
    async def read_raw_async(self):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, self.read_raw)
    
    async def read_h264_async(self):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, self.read_h264)

class VideoDec:
    def __init__(self) -> None:
        self.pipeline = Gst.parse_launch(
            "appsrc name=src do-timestamp=1 is-live=1 ! h264parse ! avdec_h264 ! videoconvert ! video/x-raw,format=BGR ! appsink name=sink emit-signals=1 sync=0")

        self.src = self.pipeline.get_by_name("src")
        self.sink = self.pipeline.get_by_name("sink")

        self.sink.connect("new-sample", self.__new_frame, self.sink)

        self.raw_queue = queue.Queue(10)

    def write_h264(self, buf):
        buf = Gst.Buffer.new_wrapped(buf)
        self.src.emit("push-buffer", buf)

    def __new_frame(self, sink, data):
        print("Decoded new frame")
        sample = sink.emit("pull-sample")
        buf = sample.get_buffer()
        caps = sample.get_caps()
        height = caps.get_structure(0).get_value("height")
        width = caps.get_structure(0).get_value("width")
        arr = np.ndarray(
            (height,
             width,
             3),
            buffer=buf.extract_dup(0, buf.get_size()),
            dtype=np.uint8)

        with suppress(queue.Full):
            self.raw_queue.put_nowait(arr)
        
        return Gst.FlowReturn.OK

    def __gst_loop(self):
        common_gst_loop(self.pipeline.get_bus())

    def run(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        self.worker = threading.Thread(target=self.__gst_loop)
        self.worker.start()

    def stop(self):
        self.worker.join()

    def read_raw(self):
        return self.raw_queue.get()
    
    async def read_raw_async(self):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, self.read_raw)

    def __enter__(self):
        self.run()
        return self

    def __exit__(self, typ, value, traceback):
        self.stop()



if __name__ == "__main__":
    def myloop(cap, dec):
        while True:
            frame = cap.read_raw()
            h264au = cap.read_h264()
            dec.write_h264(h264au)

    import cv2

    with VideoCap() as cap:
        with VideoDec() as dec:
            threading.Thread(target=myloop, args=(cap, dec)).start()
            while True:
                raw = dec.read_raw()
                cv2.imshow("main", raw)
                cv2.waitKey(10)
