import sounddevice as sd
import math

RATE = 44100

def remap(v: float, i: tuple[float, float], o: tuple[float, float]):
    t = (v - i[0]) / (i[1] - i[0])
    return o[0] * (1 - t) + o[1] * t

class Range:
    low: float
    high: float

    def __init__(self, low: float, high: float) -> None:
        self.low = low
        self.high = high

    def as_tuple(self) -> tuple[float, float]:
        return (self.low, self.high)

    def __str__(self) -> str:
        return f'Range({self.low}, {self.high})'


type Obj = Const | Sine | Remap

class Const:
    value: float

    def __init__(self, value: float) -> None:
        self.value = value

    def get(self) -> float:
        return self.value

    def tick(self) -> None:
        pass

    def range(self) -> Range:
        return Range(self.value, self.value)

    def __str__(self) -> str:
        return f'Const({self.value})'

class Sine:
    step: Obj
    ticks: float

    def __init__(self, step: Obj = Const(0)) -> None:
        self.step = step
        self.ticks = 0

    def get(self) -> float:
        return math.sin(self.ticks / RATE * math.tau)

    def tick(self) -> None:
        self.ticks += self.step.get()
        self.step.tick()

    def range(self) -> Range:
        return Range(-1, 1)

class Remap:
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

sound = Sine(Const(1))
sound = Remap(sound, Range(-1, 10))
sound = Sine(sound)
sound = Remap(sound, Range(100, 150))
sound = Sine(sound)

sound = Remap(sound, Range(-1, 1))

data = []
for i in range(RATE * 10):
    data.append(sound.get())
    sound.tick()

sd.play(data, RATE)
sd.wait()
