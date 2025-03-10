import pyaudio
import numpy as np
import time
import logging
import datetime
import collections

# Set up logging
logging.basicConfig(
    filename='voice_activity.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

class VoiceTracker:
    def __init__(self):
        # Audio parameters
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK = 1024
        self.THRESHOLD = 20  # Adjust dynamically later
        self.SILENCE_LIMIT = 2  # Seconds of silence to end conversation
        self.MIN_CALL_DURATION = 5  # Minimum seconds to consider a call
        self.BACKGROUND_NOISE_WINDOW = 30  # Number of samples for noise adaptation

        # State tracking
        self.is_speaking = False
        self.silence_start = None
        self.conversation_start = None
        self.background_noise_levels = collections.deque(maxlen=self.BACKGROUND_NOISE_WINDOW)

        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()

    def _calculate_energy(self, data):
        """Calculate audio energy (volume) from the audio chunk"""
        data_np = np.frombuffer(data, dtype=np.int16)
        mean_square = np.mean(np.square(data_np))
        return np.sqrt(max(mean_square, 0))

    def _adapt_threshold(self):
        """Dynamically adjust the threshold based on background noise levels"""
        if self.background_noise_levels:
            avg_noise = np.mean(self.background_noise_levels)
            return max(avg_noise * 2, 10)  # Ensure a minimum threshold
        return self.THRESHOLD  # Default threshold if no data

    def start_tracking(self):
        """Start tracking voice activity and possible calls"""
        try:
            stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )

            print("Voice tracking started. Press Ctrl+C to stop.")
            logging.info("Voice tracking started")

            while True:
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                energy = self._calculate_energy(data)

                # Update background noise level
                self.background_noise_levels.append(energy)
                dynamic_threshold = self._adapt_threshold()
                
                print(energy, dynamic_threshold)

                # Voice detected
                if energy > dynamic_threshold:
                    if not self.is_speaking:
                        self.conversation_start = time.time()
                        self.is_speaking = True
                        current_time = datetime.datetime.now().strftime("%H:%M:%S")
                        print(f"Voice detected at {current_time}")
                        logging.info(f"Voice activity started")

                    # Reset silence timer
                    self.silence_start = None

                # No voice detected
                else:
                    if self.is_speaking:
                        if self.silence_start is None:
                            self.silence_start = time.time()

                        # If silence duration exceeds limit, end conversation
                        if time.time() - self.silence_start > self.SILENCE_LIMIT:
                            duration = time.time() - self.conversation_start
                            current_time = datetime.datetime.now().strftime("%H:%M:%S")
                            
                            # Classify if it's a call
                            if duration >= self.MIN_CALL_DURATION:
                                print(f"Call detected! Ended at {current_time} (Duration: {duration:.1f}s)")
                                logging.info(f"Call detected - Duration: {duration:.1f} seconds")
                            else:
                                print(f"Normal conversation ended at {current_time} (Duration: {duration:.1f}s)")
                                logging.info(f"Voice activity ended - Duration: {duration:.1f} seconds")

                            self.is_speaking = False

        except KeyboardInterrupt:
            print("Voice tracking stopped.")
            logging.info("Voice tracking stopped")
        except Exception as e:
            print(f"Error: {e}")
            logging.error(f"Error occurred: {e}")
        finally:
            if 'stream' in locals() and stream is not None:
                stream.stop_stream()
                stream.close()
            self.audio.terminate()

if __name__ == "__main__":
    tracker = VoiceTracker()
    tracker.start_tracking()
