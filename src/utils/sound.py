from gpiozero.tones import Tone
from time import sleep
from pygame import mixer
import soundfile as sf

import pygame.examples.scaletest
pygame.examples.scaletest.main()

filename = 'sounds/bottle_pop_2.wav'
mixer.init()
sound = mixer.Sound(filename)
#https://www.pacdv.com/sounds/mechanical_sounds.html

f = sf.SoundFile(filename)
print('samples = {}'.format(len(f)))
print('sample rate = {}'.format(f.samplerate))
print('seconds = {}'.format(len(f) / f.samplerate))


while True:
    #Tone(frequency=2000)
    sound.play()
    sleep(0.6)


