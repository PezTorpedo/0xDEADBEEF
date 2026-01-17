#!/bin/sh
#This script will blink a Philips Hue light in Morse code for "SOS" using the user token '$TOKEN' and a defualt light '$LIGHT = 2'.

BRIDGE=http://127.0.0.1/api/$TOKEN
LIGHT=2

DOT=1
DASH=3
INTRA=1
LETTER_GAP=3
WORD_GAP=7

on() {
  curl -s -X PUT $BRIDGE/lights/$LIGHT/state -d '{"on":true,"transitiontime":0}' >/dev/null
}

off() {
  curl -s -X PUT $BRIDGE/lights/$LIGHT/state -d '{"on":false,"transitiontime":0}' >/dev/null
}

dot() {
  on
  sleep $DOT
  off
  sleep $INTRA
}

dash() {
  on
  sleep $DASH
  off
  sleep $INTRA
}

letter_gap() {
  sleep $((LETTER_GAP - INTRA))
}

word_gap() {
  sleep $((WORD_GAP - INTRA))
}

while true; do
  # S: ...
  dot
  dot
  dot
  letter_gap

  # O: ---
  dash
  dash
  dash
  letter_gap

  # S: ...
  dot
  dot
  dot
  word_gap
done
