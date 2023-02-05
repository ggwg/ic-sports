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

IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480

class Pipeline:
    def __init__(self) -> None:
        self.is_stopped = True

    def __gst_loop(self):
        bus = self.pipeline.get_bus()
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
                    if new_state == Gst.State.NULL:
                        self.is_stopped = False
                    else:
                        self.is_stopped = True

                    print(("Pipeline state changed from %s to %s." %
                        (old_state.value_nick, new_state.value_nick)))
                    if old_state == Gst.State.READY and new_state == Gst.State.NULL:
                        break

    def run(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        self.worker = threading.Thread(target=self.__gst_loop)
        self.worker.start()

    def stop(self):
        self.pipeline.set_state(Gst.State.NULL)
        self.worker.join()

    def __enter__(self):
        self.run()
        return self

    def __exit__(self, typ, value, traceback):
        self.stop()


class VideoEnc(Pipeline):
    def __init__(self, is_server: bool = False) -> None:
        super().__init__()
        self.is_server = is_server
        self.pipeline = Gst.parse_launch(
            f"appsrc name=src do-timestamp=1 is-live=1 max-buffers=2 ! video/x-raw,width={IMAGE_WIDTH},height={IMAGE_HEIGHT},format=BGR,framerate=30/1 ! videoconvert ! video/x-raw,format=I420 ! vtenc_h264_hw realtime=1 bitrate=2000 allow-frame-reordering=0 max-keyframe-interval=60 ! h264parse ! video/x-h264,alignment=au,stream-format=byte-stream ! appsink name=sink emit-signals=1 sync=0")
        
        self.src = self.pipeline.get_by_name("src")
        sink = self.pipeline.get_by_name("sink")

        sink.connect("new-sample", self.__new_h264_au, sink)
        self.queue = queue.Queue(30)
    
    def __new_h264_au(self, sink, data):
        sample = sink.emit("pull-sample")
        buf = sample.get_buffer()

        with suppress(queue.Full):
            self.queue.put_nowait(buf.extract_dup(0, buf.get_size()))

        return Gst.FlowReturn.OK
    
    def write_raw(self, buf):
        if self.is_stopped and self.is_server:
            return
        buf = Gst.Buffer.new_wrapped(buf.tobytes())
        self.src.emit("push-buffer", buf)

    def read_h264(self):
        return self.queue.get()
    
    async def read_h264_async(self):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, self.read_h264)


class VideoCap(Pipeline):
    def __init__(self) -> None:
        super().__init__()
        self.pipeline = Gst.parse_launch(
            f"autovideosrc sync=0 ! videoconvert ! video/x-raw,width={IMAGE_WIDTH},height={IMAGE_HEIGHT},format=BGR ! appsink name=rawsink emit-signals=1 sync=0")

        rawsink = self.pipeline.get_by_name("rawsink")

        rawsink.connect("new-sample", self.__new_frame, rawsink)

        self.raw_queue = queue.Queue(1)

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

    def read_raw(self):
        return self.raw_queue.get()
    
    async def read_raw_async(self):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, self.read_raw)

class VideoDec(Pipeline):
    def __init__(self) -> None:
        super().__init__()
        self.pipeline = Gst.parse_launch(
            "appsrc name=src do-timestamp=1 is-live=1 ! h264parse ! avdec_h264 ! videoconvert ! video/x-raw,format=BGR ! appsink name=sink emit-signals=1 sync=0")

        self.src = self.pipeline.get_by_name("src")
        self.sink = self.pipeline.get_by_name("sink")

        self.sink.connect("new-sample", self.__new_frame, self.sink)

        self.raw_queue = queue.Queue(2)

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

    def read_raw(self):
        return self.raw_queue.get()
    
    async def read_raw_async(self):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, self.read_raw)



if __name__ == "__main__":
    def myloop(cap: VideoCap, enc: VideoEnc):
        while True:
            frame = cap.read_raw()
            enc.write_raw(frame)

    def myloop2(enc: VideoEnc, dec: VideoDec):
        while True:
            frame = enc.read_h264()
            dec.write_h264(frame)

    import cv2

    with VideoCap() as cap:
        with VideoEnc() as enc:
            with VideoDec() as dec:
                threading.Thread(target=myloop, args=(cap, enc)).start()
                threading.Thread(target=myloop2, args=(enc, dec)).start()

                while True:
                    raw = dec.read_raw()
                    cv2.imshow("main", raw)
                    cv2.waitKey(10)
