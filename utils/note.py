from array import array
import time
import pygame
from pygame.mixer import Sound, get_init, pre_init

class Note(Sound):
    def __init__(self, frequency, volume=.1):
        pre_init(44100, -16, 1, 1024)
        pygame.init()
        self.frequency = frequency
        Sound.__init__(self, self.build_samples())
        self.set_volume(volume)

    def build_samples(self):
        period = int(round(get_init()[0] / self.frequency))
        samples = array("h", [0] * period)
        amplitude = 2 ** (abs(get_init()[1]) - 1) - 1
        for time in range(period):
            if time < period / 2:
                samples[time] = amplitude
            else:
                samples[time] = -amplitude
        return samples

if __name__ == "__main__":
   

    while True:
        tone = Note(500).play(-1)
        ts1 = int(time.time_ns())
        time.sleep(0.5)
        tone.stop()
        time.sleep(1)
        ts2 = int(time.time_ns())
        print (ts2-ts1)
       