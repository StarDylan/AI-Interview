import wave
import json
from vosk import Model, KaldiRecognizer, SetLogLevel

SetLogLevel(0)

wf = wave.open("transcription.wav", "rb")

print(wf.getframerate())
model = Model("vosk_models/vosk-model-small-en-us-0.15")
rec = KaldiRecognizer(model, wf.getframerate())
rec.SetWords(True)
rec.SetPartialWords(True)
                
text = []    
while True:
    print("Reading...")
    data = wf.readframes(999999009)
    if len(data) == 0:
         break
    # if silence detected save result
    if rec.AcceptWaveform(data):
        text.append(json.loads(rec.Result())["text"])
text.append(json.loads(rec.FinalResult())["text"])

print(f"\n{text}")