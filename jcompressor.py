# jcompressor.py
# JCompressor przebudowany pod F4-RED (252 stany)
# Kompresja = redukcja ramienia + utrzymanie dopuszczalności konfiguracji

from dataclasses import dataclass
from typing import List, Optional

from filter_252 import F4State, F4Filter252


@dataclass
class JPoint:
    """
    Pojedynczy punkt w przestrzeni TIMDR:
    wektor 9 pierwiastków strukturalnych (ΔS, τ, Λ × 3 ramiona) w stanie ±1.
    """
    bits: List[int]

    def to_f4_state(self) -> F4State:
        return F4State(bits=self.bits)


class JCompressor:
    """
    JCompressor:
    - wykonuje redukcję jednego ramienia (kompresja strukturalna)
    - utrzymuje stan w dopuszczalnej przestrzeni 252 konfiguracji F4-RED
    """

    def __init__(self):
        self.filter = F4Filter252()

    def _arm_energy(self, arm: List[int]) -> int:
        """
        "Energia" ramienia = |suma bitów ramienia|.
        3  -> ramię jednorodne (+1,+1,+1) lub (-1,-1,-1): niesie najmniej
              nowej informacji, bo wszystkie trzy pierwiastki wskazują
              ten sam kierunek. To najlepszy kandydat do redukcji.
        1  -> ramię mieszane (2 na 1): niesie najwięcej lokalnej informacji,
              zostaje nietknięte jak najdłużej.
        """
        return abs(sum(arm))

    def _reduce_arm(self, point: JPoint) -> JPoint:
        """
        Redukcja jednego ramienia (rdzeń kompresji strukturalnej JCompressor).

        Zgodnie z modelem F4-RED (patrz MODEL_PC_TIMDR.md, sekcja 1):
        figura F4 ma 4 ramiona, jedno jest redukowane, a pozostałe trzy
        aktywne ramiona (ΔS, τ, Λ) przejmują jego rolę — sprzężenia J
        stają się "dociśnięte".

        Wektor bits reprezentuje już 3 aktywne ramiona x 3 pierwiastki
        (9 elementów). "Redukcja ramienia" na tym poziomie oznacza:

        1. Wybierz najbardziej jednorodne (najmniej informatywne) z trzech
           ramion — to ono jest redukowane do pojedynczej wartości
           reprezentatywnej (kolapsuje 3 niezależne bity do 1 stopnia
           swobody, powielonego x3).
        2. Redukcja zaburza globalny bilans |N+ - N-| <= 1 wymagany przez
           filtr F4-RED. Pozostałe dwa ramiona "przejmują rolę" zredukowanego:
           przywracamy równowagę, odwracając minimalną liczbę bitów w
           pozostałych ramionach — zaczynając od bitów należących do
           ramion o najniższej energii (najbardziej elastycznych, bo
           mieszanych), żeby zaburzyć strukturę jak najmniej.

        Operacja jest deterministyczna: to samo wejście zawsze daje to
        samo wyjście.
        """
        bits = list(point.bits)
        if len(bits) != 9:
            raise ValueError(
                "JPoint musi mieć dokładnie 9 elementów (3 ramiona x 3 pierwiastki)."
            )

        arms = [bits[0:3], bits[3:6], bits[6:9]]

        # 1. Wybór ramienia do redukcji: najbardziej jednorodne (energia = 3),
        #    przy remisie bierzemy pierwsze w kolejności (deterministycznie).
        idx_to_reduce = max(range(3), key=lambda i: (self._arm_energy(arms[i]), -i))
        dominant = 1 if sum(arms[idx_to_reduce]) >= 0 else -1

        reduced_arms = [list(a) for a in arms]
        reduced_arms[idx_to_reduce] = [dominant, dominant, dominant]
        new_bits = reduced_arms[0] + reduced_arms[1] + reduced_arms[2]

        # 2. Rebalans: przywróć |N+ - N-| <= 1, odwracając bity spoza
        #    zredukowanego ramienia, zaczynając od najbardziej "elastycznych"
        #    (ramię o najniższej energii = najbardziej mieszane).
        n_plus = sum(1 for b in new_bits if b == 1)
        n_minus = 9 - n_plus

        other_positions = [i for i in range(9) if i // 3 != idx_to_reduce]
        other_positions.sort(key=lambda i: (self._arm_energy(arms[i // 3]), i))

        for pos in other_positions:
            if abs(n_plus - n_minus) <= 1:
                break
            old_val = new_bits[pos]
            # Odwracamy tylko bit, który realnie zmniejsza przewagę
            # (np. jeśli N+ > N-, odwracamy +1 -> -1, nie odwrotnie).
            if n_plus - n_minus > 1 and old_val == 1:
                new_bits[pos] = -1
                n_plus -= 1
                n_minus += 1
            elif n_minus - n_plus > 1 and old_val == -1:
                new_bits[pos] = 1
                n_minus -= 1
                n_plus += 1

        return JPoint(bits=new_bits)

    def compress(self, point: JPoint) -> Optional[JPoint]:
        """
        Główna operacja:
        - redukcja ramienia
        - walidacja F4-RED (252 stany)
        - zwrot skompresowanego punktu albo None, jeśli stan jest niedopuszczalny
        """
        reduced = self._reduce_arm(point)
        state = reduced.to_f4_state()

        if self.filter.apply(state):
            return reduced
        return None

    def stats(self) -> dict:
        return self.filter.stats()
