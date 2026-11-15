import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import torch
from PIL import Image, ImageDraw
from transformers import AutoProcessor, AutoModelForCausalLM

proc = AutoProcessor.from_pretrained('microsoft/Florence-2-base', trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained('microsoft/Florence-2-base', trust_remote_code=True)

img = Image.new('RGB', (500, 300), color='white')
draw = ImageDraw.Draw(img)
draw.rectangle([50, 50, 200, 150], fill='navy')
draw.text((70, 90), 'HELLO WORLD', fill='white')
draw.ellipse([300, 50, 450, 200], fill='red')

questions = [
    'What is written inside the navy box?',
    'What color is the shape on the right?',
    'How many shapes are in the image?',
]

for q in questions:
    inp = proc(text=q, images=img, return_tensors='pt')
    out = model.generate(**inp, max_new_tokens=40)
    print(q, "-->", repr(proc.batch_decode(out, skip_special_tokens=True)[0]))
