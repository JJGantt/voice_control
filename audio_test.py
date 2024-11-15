import numpy as np

class AudioTester:
    def __init__(self, sample_rate=16000, frame_length=512):
        """
        Initializes the AudioTester class.
        """
        self.sample_rate = sample_rate
        self.frame_length = frame_length

    def check_audio_data(self, audio_data):
        """
        Checks if the audio data is coming in correctly and prints statistics.
        """
        if audio_data is None or len(audio_data) == 0:
            print("No audio data received.")
            return False

        # Convert raw audio data to NumPy array for analysis
        audio_array = np.array(audio_data, dtype=np.int16)

        # Calculate basic statistics
        max_val = np.max(audio_array)
        min_val = np.min(audio_array)
        mean_val = np.mean(audio_array)
        non_zero_count = np.count_nonzero(audio_array)

        print(f"Audio Data Check - Max: {max_val}, Min: {min_val}, Mean: {mean_val}, Non-zero samples: {non_zero_count}/{len(audio_array)}")

        # Check if there's any non-zero data (indicating audio is coming in)
        if non_zero_count > 0:
            print("Audio data is coming in correctly.")
            return True
        else:
            print("Audio data is silent or not coming through.")
            return False

    def print_audio_samples(self, audio_data, num_samples=10):
        """
        Prints the first few samples of the audio data for inspection.
        """
        if audio_data is None or len(audio_data) == 0:
            print("No audio data to print.")
            return

        print("First few audio samples:")
        for i in range(min(num_samples, len(audio_data))):
            print(f"Sample {i}: {audio_data[i]}")
        print("-------------------")
