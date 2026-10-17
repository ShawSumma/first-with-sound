from __future__ import annotations
import sounddevice as sd
import math

RATE = 44100

NOTES = {
    'C': 16.35,
    'C#': 17.32,
    'D': 18.35,
    'D#': 19.45,
    'E': 20.60,
    'F': 21.83,
    'F#': 23.12,
    'G': 24.50,
    'G#': 25.96,
    'A': 27.50,
    'A#': 29.14,
    'B': 30.87,
}

def remap(v: float, i: tuple[float, float], o: tuple[float, float]):
    t = (v - i[0]) / (i[1] - i[0])
    return o[0] * (1 - t) + o[1] * t

class Range:
    low: float
    high: float

    def __init__(self, low: float, high: float) -> None:
        assert low <= high
        self.low = low
        self.high = high

    def as_tuple(self) -> tuple[float, float]:
        return (self.low, self.high)

    def includes(self, value: float):
        return self.low <= value and value <= self.high

    def merge(self, other: Range) -> Range:
        return Range(min(self.low, other.low), max(self.high, other.high))

    def __str__(self) -> str:
        return f'Range({self.low}, {self.high})'


class Obj:
    def get(self) -> float:
        return NotImplemented

    def tick(self) -> None:
        return NotImplemented

    def range(self) -> Range:
        return NotImplemented

    def __str__(self) -> str:
        return NotImplemented

class Const(Obj):
    value: float

    def __init__(self, value: float) -> None:
        self.value = value

    @staticmethod
    def from_note(name: str) -> Const:
        for note in sorted(NOTES.keys(), key=lambda x: -len(x)):
            if name.startswith(note):
                return Const(NOTES[note] * (2 ** int(name.removeprefix(note))))
        assert False

    def get(self) -> float:
        return self.value

    def tick(self) -> None:
        pass

    def range(self) -> Range:
        return Range(self.value, self.value)

    def __str__(self) -> str:
        return f'Const({self.value})'

class Sine(Obj):
    step: Obj
    ticks: float

    def __init__(self, step: Obj = Const(0)) -> None:
        self.step = step
        self.ticks = 0

    @staticmethod
    def from_note(name: str) -> Sine:
        return Sine(Const.from_note(name))

    def get(self) -> float:
        return math.sin(self.ticks / RATE * math.tau)

    def tick(self) -> None:
        self.ticks += self.step.get()
        self.step.tick()

    def range(self) -> Range:
        return Range(-1, 1)

    def __str__(self) -> str:
        return f'Sine({self.step})'

class Remap(Obj):
    next: Obj
    to: Range

    def __init__(self, next: Obj, to: Range) -> None:
        self.next = next
        self.to = to

    def get(self) -> float:
        r = remap(
            self.next.get(),
            self.next.range().as_tuple(),
            self.to.as_tuple(),
        )
        return r

    def tick(self) -> None:
        self.next.tick()

    def range(self) -> Range:
        return self.to

    def __str__(self) -> str:
        return f'Remap({self.next}, {self.next})'

class Item:
    pause: bool
    length: Obj
    next: Obj

    def __init__(self, length: Obj, next: Obj, pause: bool = True) -> None:
        self.pause = pause
        self.length = length
        self.next = next

class Seq(Obj):
    seqs: tuple[Item, ...]
    cur: int
    time: float

    def __init__(self, *seqs: Item) -> None:
        self.seqs = seqs
        self.cur = 0
        self.time = 0

    def get(self) -> float:
        return self.seqs[self.cur].next.get()

    def tick(self) -> None:
        self.time += 1 / RATE
        while self.time > self.seqs[self.cur].length.get():
            self.time -= self.seqs[self.cur].length.get()
            self.cur = (self.cur + 1) % len(self.seqs)
        for index, seq in enumerate(self.seqs):
            if index == self.cur or not seq.pause:
                seq.next.tick()
                seq.length.tick()

    def range(self) -> Range:
        r = self.seqs[0].next.range()
        for seq in self.seqs[1:]:
            r = r.merge(seq.next.range())
        return r

    def __str__(self) -> str:
        args = ', '.join(str(i) for i in self.seqs)
        return f'Seq({args})'

match 3:
    case 1:
        sound = Sine(Const(1))
        sound = Remap(sound, Range(-1, 10))
        sound = Sine(sound)
        sound = Remap(sound, Range(100, 150))
        sound = Sine(sound)
    case 2:
        sound = Sine(Const(150))
        sound = Seq(
            Item(Const(1/2), Sine(Remap(Sine(Const(3)), Range(Const.from_note('E4').value, Const.from_note('A#4').value)))),
            Item(Const(1/8), Sine.from_note('A#4')),
            Item(Const(1/4), Sine.from_note('C#4')),
            Item(Const(1/8), Sine.from_note('E4')),
        )
    case 3:
        sound = Sine(Const(1/2))
        sound = Sine(Remap(sound, Range(0, 2)))
        sound = Sine(Remap(sound, Range(0, 16)))
        sound = Sine(Remap(sound, Range(100/1.5, 100*1.5)))

sound = Remap(sound, Range(-1, 1))

data = []
for i in range(RATE * 100):
    data.append(sound.get())
    sound.tick()

sd.play(data, RATE)
sd.wait()
