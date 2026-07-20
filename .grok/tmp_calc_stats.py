def calc_stats(scores: list[int], threshold: int = 60) -> dict[str, int | float]:
    passed: list[int] = [s for s in scores if s >= threshold]
    return {
        "total": len(scores),
        "passed": len(passed),
        "average": sum(scores) / len(scores) if scores else 0,
    }


def calc_stats_user(scores: list[int], threshold: int = 60):
    passed: list[int] = [s for s in scores if s >= threshold]
    return {
        "total": len(scores),
        "passed": len(passed),
        "average": sum(scores) / len(scores) if scores else 0,
    }