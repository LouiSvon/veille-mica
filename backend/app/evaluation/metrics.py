"""Métriques d'évaluation. Les effectifs sont petits : on affiche toujours k sur n et un intervalle de Wilson."""
import math


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalle de Wilson à 95 % pour une proportion k/n. Pour n = 0, renvoie (0, 1) : aucune information."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    demi = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - demi), min(1.0, centre + demi))


def recall_at_k(rangs: list[int | None], k: int) -> tuple[int, int]:
    """(nombre de questions dont le premier passage de référence est dans les k premiers, nombre de questions)."""
    return (sum(1 for r in rangs if r is not None and r <= k), len(rangs))


def mrr(rangs: list[int | None]) -> float:
    """Rang réciproque moyen. Un passage non retrouvé compte pour 0."""
    return sum(1 / r for r in rangs if r) / len(rangs) if rangs else 0.0


def premier_rang(classement: list[str], references: set[str]) -> int | None:
    """Rang (à partir de 1) du premier passage classé qui figure dans les références, ou None."""
    for rang, chunk_id in enumerate(classement, start=1):
        if chunk_id in references:
            return rang
    return None
