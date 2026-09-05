# Downstream node, written with an explicit run_task() entrypoint. Exercises the
# "run_task() file" code path (the importer must NOT double-wrap this).
import waveassist


def run_task():
    seed = waveassist.fetch_data("seed_value")
    if seed is None:
        # Fail loudly so the run is recorded FAILED and the test exits nonzero.
        raise RuntimeError("seed_value missing; the produce node did not run first")
    final = int(seed) * 2
    waveassist.store_data("final_result", final)
    return final
