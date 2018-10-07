#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygame
import random
import sys
import serial
import string
import os
import pygame.mixer
from time import time, sleep
import logging
import pdb

RECONNECT_TIME = 3
REPEAT_TIME = 3
DELTA = RECONNECT_TIME + 1
BLIND_FIND_ROUND = 2  #when finding letters during this round screen will blank, just audio, no grayscale (0 for off)
ROUNDS = 2 #number of rounds when finding letters
WINDOWED = True  #run game in a window or fullscreen
Lang = 'it/'
#Lang = 'en/'

script_dir = os.path.dirname(__file__)

logger = logging.getLogger('myapp')
hdlr = logging.FileHandler(os.path.join(script_dir, 'game.log'))
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.WARNING)


class character:

    def __init__(self, value, display):
        self.value = value
        self.display = display
        try:
            self.image = pygame.image.load(os.path.join(script_dir, 'images/' + Lang + value + '.png'))
        except:
            self.image = pygame.image.load(os.path.join(script_dir, 'images/missing_image.png'))
        try:
            self.gray_image = pygame.image.load(os.path.join(script_dir, 'images/' + Lang +'gray/' + value + '.png'))
        except:
            self.gray_image = pygame.image.load(os.path.join(script_dir, 'images/missing_image.png'))
        try:
            self.sound = pygame.mixer.Sound(os.path.join(script_dir, 'sounds/' + Lang + value + '.wav'))
        except:
            self.sound = pygame.mixer.Sound(os.path.join(script_dir, 'sounds/missing_sound.wav'))

    def draw(self, gray = False):
        """ place image on screen"""
        if gray:
            self.display.draw(self.gray_image)
        else:
            self.display.draw(self.image)

    def play(self):
        """play sound"""
        self.sound.play()

def get_input():

    letter = ''
    number = ''
    connected = False
    last_time = time()

    try:
         s = serial.Serial(port="/dev/serial0", baudrate=9600, timeout=5)
         connected = True
         logger.info("connected")
         print s.portstr
    except:
        logger.info("connection error")
    i = 0
    while(True):
        number = ''
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                logger.info("quit")
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                logger.info("mouse quit")
                sys.exit()

            if (event.type == pygame.KEYDOWN):
                if (event.key == pygame.K_ESCAPE):
                    sys.exit()
                if ((event.key >= ord('a') and event.key <= ord('z')) or
                    (event.key >= ord('A') and event.key <= ord('Z'))):
                    letter = chr(event.key).upper()
                    logger.info("Key "+ letter)
                    yield letter

        w = 0
        if (connected):
            try:
                w = s.inWaiting()
                #logger.info("got w")
            except:
                connected = False
                logger.info("not got w")
        else:
            delta = time() - last_time
            if (delta > RECONNECT_TIME):
                os.system("serial0 release serial0")
                ret = os.system("serial0 connect serial0")
                if (ret == 0):
                    try:
                        s = serial.Serial(port = "/dev/serial0", baudrate=9600, timeout=5)
                        connected = True
                        print s.portstr
                    except:
                        logger.info("connection error")

            last_time = time()

        if (w>0):
            logger.info("w>0")
            try:
                data = s.readline()
                logger.info(data)
                x = s.inWaiting()
                logger.info("X=")
                logger.info(x)
                if (x>0):
                    s.read(x)
                    logger.info(data)
                number = data.strip()
                logger.info(number)
            except:
                connected = False
                logger.info("not connected anymore")
                number=""

        yield number

def look_up(number, mapping):
    if number == 'X':
        return "ask_for_letters"
    if number == 'Z':
        return "EXIT"
    if number == '':
        return number
    if mapping.has_key(number):
        number = mapping[number]
        logger.info("lookup mapping "+ number)
    elif number in string.ascii_uppercase:
        return number
    else:
        logger.info("unknown card")
        with open(os.path.join(script_dir, 'unknown.txt'), 'a+') as f:
            f.write(number+'\n')
            number = ''
    return number

def wait_sound_end():
    while pygame.mixer.get_busy() > 0:
        pass

def make_letter_set(mapping, characters):
    get_in = get_input()
    letter_set = set()
    done = False
    characters["ask_for_letters"].draw()
    while not done:
        card = look_up(str(next(get_in)), mapping)
        if card == "ask_for_letters":
            done = True
        elif card !='':
            letter_set.add(card)
            characters[card].draw()

    return letter_set

class display_screen:

    def __init__(self):
        self.modes = pygame.display.list_modes()
        self.size = (self.width, self.height) = self.modes[0]
        if WINDOWED:
            self.screen = pygame.display.set_mode(self.size, pygame.RESIZABLE)
        else:
            self.screen = pygame.display.set_mode(self.size, pygame.FULLSCREEN)

    def draw(self, image):
        white = (255, 255, 255)
        orig_rect = image.get_rect()
        scalex = self.width * 1.0 / orig_rect.width
        scaley = self.height * 1.0 / orig_rect.height
        scale = min(scalex, scaley)
        current = pygame.transform.scale(image, (int(orig_rect.width
                  * scale), int(orig_rect.height * scale)))
        current_rect = current.get_rect()
        sys.stdout.flush()
        self.screen.fill(white)
        pos = ((self.width - current_rect.width) / 2, (self.height
               - current_rect.height) / 2)
        self.screen.blit(current, pos)
        pygame.display.flip()

def main():


    with open(os.path.join(script_dir, 'map.txt'), 'r') as f:
        lines = f.readlines()

    mapping = {}
    characters = {}
    last_time = time()
    last_time_wrong = time()
    letters = []
    GameType = "any_input"
    BLIND = False
    EXIT = False


    get_commands = False

    pygame.init()
    pygame.mixer.init()
    display = display_screen()

    cheer = pygame.mixer.Sound(os.path.join(script_dir, 'sounds/cheer.wav'))
    cheer2 = pygame.mixer.Sound(os.path.join(script_dir, 'sounds/cheer2.wav'))
    wrong = pygame.mixer.Sound(os.path.join(script_dir, 'sounds/wrong.wav'))
    find = pygame.mixer.Sound(os.path.join(script_dir, 'sounds/' + Lang + 'find.wav'))

    for line in lines:
        line = line.strip()
        if line == '-=commands=-':
            get_commands = True
            continue
        if line == '':
            continue
        (num, letter) = line.split('=')
        mapping[num] = letter
        characters[letter] = character(letter, display)
        if not get_commands:
            letters.append(letter)
    letter_image = {}

    start_screen = pygame.image.load(os.path.join(script_dir, 'images/main.png'))
    all_done = pygame.image.load(os.path.join(script_dir, 'images/marsha_bear.jpg'))
    white = (255, 255, 255)
    black = (0, 0, 0)

    display.screen.fill(white)
    pygame.mouse.set_visible(False)
    display.draw(start_screen)
    current_letter = 'default'


    done = False
    letters_done = set()
    get_in = get_input()

    while not done:

        number = str(next(get_in))
        letter = look_up(number, mapping)
        #logger.info("letter")
        #logger.info(letter)

        if GameType == "ask_for_letters":

            if letter == 'EXIT' or EXIT:
                GameType = 'any_input'
                letter = ''
                EXIT = True
                display.draw(start_screen)
                logger.info("EXIT TRUE")

            if not EXIT:

                if target == 'none' or target == letter:
                    if target == letter:
                        logger.info("TARGET==LETTER")
                        cheer.play()
                        characters[target].draw()
                        sleep(5)
                    current_letter = letter

                    #if correct, or first time, get next letter, which is random, and not a repeat.
                    while letter == target or target == 'none':
                        if len(letter_set) == 1:
                            letter = '' #to avoid endless loop if only one letter in the set
                        if len(letter_set) == len(letters_done):
                            letters_done.clear()
                            round_number += round_number #times whole set is being guessed
                        target = random.choice(tuple(letter_set - letters_done))

                    letters_done.add(target)
                    logger.info('TARGET ='+ target)
                    logger.info('round number ' + str(round_number))
                    logger.info('ROUNDS ' + str(ROUNDS))

                    if round_number <= ROUNDS:
                        if round_number == BLIND_FIND_ROUND:
                            BLIND = True
                        if BLIND:
                            display.screen.fill(black)
                            pygame.display.flip()
                        else:
                            characters[target].draw(True)
                        find.play()
                        wait_sound_end()
                        characters[target].play()
                        last_time = time()
                        wait_sound_end()
                        letter = ''
                        #pdb.set_trace()
                    else:
                        display.draw(all_done)
                        cheer2.play()
                        wait_sound_end()
                        EXIT = True

                elif letter == '':
                    delta = time() - last_time
                    if delta > REPEAT_TIME*2:
                        find.play()
                        wait_sound_end()
                        characters[target].play()
                        last_time = time()
                else:

                    if letter != target and letter != current_letter and not EXIT:
                        #delta = time() - last_time_wrong
                        #if delta > REPEAT_TIME:
                        wrong.play()
                        wait_sound_end()
                        current_letter = letter
                        #last_time_wrong = time()

        if letter == "ask_for_letters":
            letter_set = make_letter_set(mapping, characters)
            letter = ''
            round_number = 1
            BLIND = False
            if len(letter_set) > 0:
                GameType = "ask_for_letters"
                target = 'none'

        if GameType == "any_input":
            EXIT = False
            if letter == 'EXIT':
                sys.exit()

            if letter in letters:

                if current_letter != letter:
                    characters[letter].draw()
                    characters[letter].play()
                    current_letter = letter
                    last_time = time()

            delta = time() - last_time
            if current_letter == letter and delta > REPEAT_TIME:
                characters[letter].play()
                last_time = time()

        #if GameType == "ask_for_letters":
            #if letter in letters:
                #if letter == findLetter:



if __name__ == '__main__':
    main()