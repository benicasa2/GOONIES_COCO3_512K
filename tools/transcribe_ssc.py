"""Convert a mono recording of square-wave music to three AY tone channels."""
import argparse
from itertools import groupby, permutations
from pathlib import Path
import subprocess
import wave

import numpy as np

RATE = 8000
TICKS = 60
STEP = 3
AY_BASE = 111860


def transcribe(samples):
    size = 640
    nfft = 4096
    frequencies = 440 * 2 ** ((np.arange(32, 93) - 69) / 12)
    bins = np.arange(nfft // 2 + 1)
    # Windowed odd harmonics distinguish fundamentals from square-wave overtones.
    templates = np.zeros((len(frequencies), len(bins)))
    for h in range(1, 12, 2):
        offset = bins - frequencies[:, None] * h * nfft / RATE
        tolerance = 3.4 + frequencies[:, None] * h * nfft / RATE * .004
        templates += np.exp(-.5 * (offset / tolerance)**2) / h
    templates /= np.linalg.norm(templates, axis=1)[:, None]
    window = np.hanning(size)
    padded = np.pad(samples, (size//2, size//2))
    result = []
    previous = (0, 0, 0)
    for at in range(0, len(samples), RATE * STEP // TICKS):
        frame = padded[at:at+size] * window
        spec = abs(np.fft.rfft(frame, nfft))
        spec[:26] = 0
        residual = spec.copy()
        notes = []
        first = 0
        for _ in range(3):
            scores = np.einsum("ij,j->i", templates, residual)
            idx = int(scores.argmax())
            level = scores[idx]
            if not notes:
                first = level
            if level < max(13000, first*.19):
                break
            notes.append(idx+32)
            residual = np.maximum(0, residual - templates[idx] * level * 1.20)
            # Suppress leakage from the selected fundamental, including adjacent pitches.
            lo = max(0, idx-1)
            hi = min(len(frequencies), idx+2)
            for nearby in range(lo, hi):
                center = round(frequencies[nearby]*nfft/RATE)
                residual[max(0,center-4):center+5] = 0
        notes += [0] * (3-len(notes))
        previous = min(permutations(notes), key=lambda p: sum(
            0 if a==b else abs(a-b) if a and b else 15 for a,b in zip(p,previous)))
        result.append(previous)
    return result


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('mp3', type=Path)
    cli.add_argument('output', type=Path)
    cli.add_argument('--ffmpeg', default='ffmpeg')
    cli.add_argument('--preview', type=Path)
    args = cli.parse_args()
    pcm = subprocess.check_output([args.ffmpeg,'-v','error','-i',str(args.mp3),
                                   '-ar',str(RATE),'-ac','1','-f','s16le','-'])
    notes = transcribe(np.frombuffer(pcm, '<i2').astype(float))
    periods = [0] + [round(AY_BASE / (440 * 2 ** ((n-69)/12))) for n in range(32,93)]
    stream = bytearray()
    last = (0,0,0)
    for chord, group in groupby(notes):
        frames = len(list(group))
        mask = sum(1<<i for i,(a,b) in enumerate(zip(chord,last)) if a!=b)
        while frames:
            count = min(31, frames)
            stream.append(count*8 | mask)
            stream.extend(n-31 if n else 0 for i,n in enumerate(chord) if mask & 1<<i)
            frames -= count
            mask = 0
        last = chord
    stream.append(0)
    args.output.write_bytes(stream)
    if args.preview:
        phase = np.zeros(3)
        with wave.open(str(args.preview),'wb') as out:
            out.setparams((1,2,RATE,0,'NONE','not compressed'))
            for chord in notes:
                freq = np.array([AY_BASE/periods[n-31] if n else 0 for n in chord])
                t = phase + np.arange(RATE*STEP//TICKS)[:,None]*freq/RATE
                mix = ((2*(t%1 < .5)-1)*(freq>0)).sum(axis=1)
                phase = (t[-1]+freq/RATE)%1
                out.writeframes((mix*6500).astype('<i2').tobytes())
    print(f'{len(notes)*STEP/TICKS:.2f}s; {len(stream)} bytes; ' 
          f'{sum(all(c) for c in notes)} frames with three active voices')


if __name__ == '__main__':
    main()
