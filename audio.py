import numpy as np
import pygame
from logger import log
import config

class AudioSynthesizer:
    """Procedurally synthesizes and caches game audio effects using NumPy and pygame.mixer."""
    
    def __init__(self):
        self.sounds = {}
        self.initialized = False
        
    def init_mixer(self):
        """Initializes the pygame mixer with standard settings."""
        try:
            # Pre-initialize mixer to match our synthesis parameters (44.1kHz, 16-bit signed, stereo)
            pygame.mixer.pre_init(frequency=config.SAMPLE_RATE, size=-16, channels=2)
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            log.info("Pygame mixer initialized: %s", pygame.mixer.get_init())
            self.initialized = True
        except Exception as e:
            log.error("Failed to initialize pygame mixer: %s", e)
            self.initialized = False

    def generate_all_sounds(self):
        """Synthesizes all audio effects and caches them.
        
        This can be run in the Loading state. It completes in a fraction of a second.
        """
        if not self.initialized:
            log.warning("Mixer not initialized. Audio synthesis aborted.")
            return
            
        try:
            log.info("Generating procedural sound effects...")
            self.sounds["slice"] = self._create_slice_sound()
            self.sounds["splat"] = self._create_splat_sound()
            self.sounds["explosion"] = self._create_explosion_sound()
            self.sounds["combo"] = self._create_combo_sound()
            self.sounds["click"] = self._create_click_sound()
            log.info("Procedural sound generation complete. %d sounds created.", len(self.sounds))
        except Exception as e:
            log.exception("Error during sound generation: %s", e)

    def play(self, name):
        """Plays the requested sound effect by name."""
        if not self.initialized:
            return
            
        sound = self.sounds.get(name)
        if sound:
            # Set volume from config
            sound.set_volume(config.VOLUME)
            sound.play()
        else:
            log.warning("Sound '%s' not found or failed to generate.", name)

    def set_volume(self, volume):
        """Updates global sound volume settings."""
        config.VOLUME = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            sound.set_volume(config.VOLUME)

    def _wave_to_sound(self, mono_wave):
        """Helper to convert a normalized 1D float wave array to a stereo pygame.Sound object.
        
        Args:
            mono_wave (numpy.ndarray): Float array with values between -1.0 and 1.0.
            
        Returns:
            pygame.mixer.Sound: Pygame sound object.
        """
        # Clamp to [-1.0, 1.0] to prevent clipping distortion
        mono_wave = np.clip(mono_wave, -1.0, 1.0)
        
        # Convert to 16-bit signed integers (-32768 to 32767)
        audio_int16 = (mono_wave * 32767).astype(np.int16)
        
        # Duplicate to create a stereo layout (shape: N x 2)
        stereo_audio = np.column_stack((audio_int16, audio_int16))
        
        # Create sound using pygame's sndarray module
        return pygame.sndarray.make_sound(stereo_audio)

    def _create_slice_sound(self):
        """Synthesizes a high-frequency cutting 'whoosh' sound."""
        duration = 0.12 # seconds
        num_samples = int(config.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False)
        
        # Linear frequency sweep: 1400 Hz down to 350 Hz
        f0, f1 = 1400.0, 350.0
        frequencies = f0 + (f1 - f0) * (t / duration)
        phases = 2.0 * np.pi * np.cumsum(frequencies) / config.SAMPLE_RATE
        wave = np.sin(phases)
        
        # Envelope: sharp attack, exponential decay
        # Attack: linear up to 0.01s, decay: exponential after
        envelope = np.ones_like(t)
        attack_samples = int(config.SAMPLE_RATE * 0.01)
        envelope[:attack_samples] = np.linspace(0.0, 1.0, attack_samples)
        
        decay_t = t[attack_samples:] - t[attack_samples]
        envelope[attack_samples:] = np.exp(-25.0 * decay_t)
        
        # Mix a tiny bit of white noise for a soft 'shh' sound
        noise = np.random.uniform(-1.0, 1.0, num_samples)
        # Simple moving average to low-pass filter the noise
        noise_filtered = np.convolve(noise, np.ones(3)/3, mode='same')
        
        mixed = 0.85 * wave + 0.15 * noise_filtered
        return self._wave_to_sound(mixed * envelope)

    def _create_splat_sound(self):
        """Synthesizes a squishy 'splat' sound using FM and low-pass noise."""
        duration = 0.22 # seconds
        num_samples = int(config.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False)
        
        # Modulated low frequency: 180 Hz down to 50 Hz
        f0, f1 = 180.0, 50.0
        frequencies = f0 + (f1 - f0) * (t / duration)
        # FM modulation: add a secondary sine wave to phase
        modulator = np.sin(2.0 * np.pi * 35.0 * t) * 8.0
        phases = 2.0 * np.pi * np.cumsum(frequencies) / config.SAMPLE_RATE + modulator
        wave = np.sin(phases)
        
        # Generate white noise and filter it heavily (moving average window of 10)
        noise = np.random.uniform(-1.0, 1.0, num_samples)
        noise_filtered = np.convolve(noise, np.ones(10)/10, mode='same')
        
        # Envelope: immediate attack, medium decay
        envelope = np.exp(-12.0 * t)
        
        mixed = 0.4 * wave + 0.6 * noise_filtered
        return self._wave_to_sound(mixed * envelope)

    def _create_explosion_sound(self):
        """Synthesizes a deep bassy explosion rumble."""
        duration = 0.8 # seconds
        num_samples = int(config.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False)
        
        # Deep frequency sweep: 90 Hz down to 20 Hz
        f0, f1 = 90.0, 20.0
        frequencies = f0 + (f1 - f0) * (t / duration)
        phases = 2.0 * np.pi * np.cumsum(frequencies) / config.SAMPLE_RATE
        wave = np.sin(phases)
        
        # Generate white noise and filter heavily for a brown noise rumble effect
        noise = np.random.uniform(-1.0, 1.0, num_samples)
        noise_filtered = np.convolve(noise, np.ones(35)/35, mode='same')
        
        # Envelope: quick attack, long decay
        envelope = np.ones_like(t)
        attack_samples = int(config.SAMPLE_RATE * 0.005)
        envelope[:attack_samples] = np.linspace(0.0, 1.0, attack_samples)
        envelope[attack_samples:] = np.exp(-4.5 * (t[attack_samples:] - t[attack_samples]))
        
        mixed = 0.3 * wave + 0.7 * noise_filtered
        return self._wave_to_sound(mixed * envelope)

    def _create_combo_sound(self):
        """Synthesizes a pleasant bell chime arpeggio (C6 -> E6 -> G6)."""
        duration = 0.4 # seconds
        num_samples = int(config.SAMPLE_RATE * duration)
        wave = np.zeros(num_samples)
        t = np.linspace(0, duration, num_samples, endpoint=False)
        
        # Define notes (frequencies in Hz) and delays (seconds)
        notes = [1046.50, 1318.51, 1568.0] # C6, E6, G6
        delays = [0.0, 0.06, 0.12]
        
        for freq, delay in zip(notes, delays):
            delay_samples = int(config.SAMPLE_RATE * delay)
            if delay_samples < num_samples:
                # Active time for this note
                note_t = t[delay_samples:] - delay
                note_wave = np.sin(2.0 * np.pi * freq * note_t) * np.exp(-12.0 * note_t)
                wave[delay_samples:] += note_wave * 0.35 # scale note volume
                
        return self._wave_to_sound(wave)

    def _create_click_sound(self):
        """Synthesizes a clean, short UI navigation beep."""
        duration = 0.06 # seconds
        num_samples = int(config.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False)
        
        # Constant frequency 880 Hz (A5)
        wave = np.sin(2.0 * np.pi * 880.0 * t)
        
        # Envelope: immediate decay
        envelope = np.exp(-35.0 * t)
        
        return self._wave_to_sound(wave * envelope)

# Global synth instance
synth = AudioSynthesizer()
