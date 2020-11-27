from gpiozero.tones import Tone
from time import sleep
from pygame import mixer
mixer.init()
sound = mixer.Sound('bottle_pop_2.wav')
#https://www.pacdv.com/sounds/mechanical_sounds.html

while True:
    #Tone(frequency=2000)
    sound.play()
    sleep(1)
