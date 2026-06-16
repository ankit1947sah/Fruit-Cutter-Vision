import cv2
import threading
import time
from logger import log
import config

class Camera:
    """Manages raw frame acquisition from the webcam in a dedicated thread."""
    
    def __init__(self, camera_id=None, width=None, height=None):
        self.camera_id = camera_id if camera_id is not None else config.CAMERA_ID
        self.width = width if width is not None else config.CAM_WIDTH
        self.height = height if height is not None else config.CAM_HEIGHT
        
        self.cap = None
        self.latest_frame = None
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        self.initialized = False
        self.fps = 0.0
        
    def start(self):
        """Starts the frame acquisition thread."""
        if self.running:
            log.warning("Camera thread is already running.")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, name="CameraThread", daemon=True)
        self.thread.start()
        log.info("Camera capture thread started.")
        
    def _capture_loop(self):
        """Internal capture loop running on the background thread."""
        try:
            log.info("Attempting to open camera %d...", self.camera_id)
            self.cap = cv2.VideoCapture(self.camera_id)
            if not self.cap.isOpened():
                log.error("Could not open video device %d. Permissions may be denied or camera is in use.", self.camera_id)
                self.initialized = False
                self.running = False
                return
                
            # Request specific frame dimensions
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            
            # Query actual dimensions
            actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            log.info("Webcam initialized: Requested (%dx%d), Got (%dx%d)", 
                     self.width, self.height, actual_w, actual_h)
            
            self.initialized = True
            
            # Warm up frame
            ret, frame = self.cap.read()
            if ret:
                if config.FLIP_HORIZONTAL:
                    frame = cv2.flip(frame, 1)
                with self.lock:
                    self.latest_frame = frame
            
            frame_count = 0
            fps_start_time = time.time()
            
            while self.running:
                ret, frame = self.cap.read()
                if ret:
                    if config.FLIP_HORIZONTAL:
                        frame = cv2.flip(frame, 1)
                        
                    with self.lock:
                        self.latest_frame = frame
                        
                    frame_count += 1
                    now = time.time()
                    elapsed = now - fps_start_time
                    if elapsed >= 1.0:
                        self.fps = frame_count / elapsed
                        frame_count = 0
                        fps_start_time = now
                else:
                    log.warning("Webcam frame acquisition failed.")
                    # Keep trying or back off slightly
                    time.sleep(0.01)
                    
        except Exception as e:
            log.exception("Exception in Camera capture thread: %s", e)
            self.initialized = False
            self.running = False
        finally:
            if self.cap:
                self.cap.release()
                log.info("Webcam video device released.")
                
    def get_frame(self):
        """Thread-safe acquisition of the latest frame."""
        with self.lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
            
    def stop(self):
        """Stops the camera capture thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            log.info("Camera capture thread stopped.")
        self.initialized = False
