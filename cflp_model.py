"""CFLP binaire, formulation forte du PDF (section 3.2, annexe A.2)."""

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import tempfile
import time

import pulp

from data import (
    CLIENTS, DEPOTS, PORT, CIRCUITY,
    INBOUND_EUR_PAL_KM, OUTBOUND_EUR_PAL_KM, road_km,
)


def build_model(inbound_rate=INBOUND_EUR_PAL_KM):
    """Construire le modèle sans imposer de réseau ni de coût de référence."""
    if not math.isfinite(inbound_rate) or inbound_rate < 0:
        raise ValueError("Le coût amont doit être fini et positif ou nul.")
    I, J = range(len(CLIENTS)), range(len(DEPOTS))
    m = pulp.LpProblem("CFLP", pulp.LpMinimize)
    y = pulp.LpVariable.dicts("open", J, cat=pulp.LpBinary)
    x = pulp.LpVariable.dicts("assign", (I, J), cat=pulp.LpBinary)
    unit_cost = {
        (i, j): road_km(PORT, DEPOTS[j]) * inbound_rate + DEPOTS[j][5]
        + road_km(DEPOTS[j], CLIENTS[i]) * OUTBOUND_EUR_PAL_KM
        for i in I for j in J
    }
    m += (
        pulp.lpSum(DEPOTS[j][3] * y[j] for j in J)
        + pulp.lpSum(CLIENTS[i][3] * unit_cost[i, j] * x[i][j] for i in I for j in J)
    ), "annual_logistics_cost"
    for i in I:
        m += pulp.lpSum(x[i][j] for j in J) == 1, f"demand_{i}"
    for j in J:
        m += pulp.lpSum(CLIENTS[i][3] * x[i][j] for i in I) <= DEPOTS[j][4] * y[j], f"cap_{j}"
    for i in I:
        for j in J:
            m += x[i][j] <= y[j], f"link_{i}_{j}"
    return m, x, y


def verify_solution(m, x, y):
    """Contrôler les valeurs CBC avant toute extraction ou présentation."""
    tol = 1e-6
    for v in m.variables():
        value = v.value()
        if value is None or not math.isfinite(value) or min(abs(value), abs(value - 1)) > tol:
            raise ValueError(f"Valeur binaire invalide : {v.name}={value}")
    for i in range(len(CLIENTS)):
        if abs(sum(x[i][j].value() for j in y) - 1) > tol:
            raise ValueError(f"Affectation non unique pour {CLIENTS[i][0]}")
        for j in y:
            if x[i][j].value() > y[j].value() + tol:
                raise ValueError("Affectation à un entrepôt fermé")
    for j in y:
        load = sum(CLIENTS[i][3] * x[i][j].value() for i in x)
        if load > DEPOTS[j][4] * y[j].value() + tol:
            raise ValueError(f"Capacité dépassée pour {DEPOTS[j][0]}")


def compare_reference(result):
    """Comparer a posteriori ; ces valeurs ne participent jamais au modèle."""
    expected = {"Kassel": (27200, 7), "Nuernberg": (24500, 7), "Ulm": (30200, 7)}
    actual = {w["name"]: (w["load_pal_year"], w["client_count"]) for w in result["warehouses"]}
    return {
        "reference_total_eur_rounded": 6742112,
        "difference_from_rounded_reference_eur": result["costs_eur_year"]["total"] - 6742112,
        "total_matches_at_nearest_euro": round(result["costs_eur_year"]["total"]) == 6742112,
        "open_warehouses_match": set(result["open_warehouses"]) == set(expected),
        "loads_and_client_counts_match": actual == expected,
        "variable_count_matches": result["model"]["variables"] == 198,
        "constraint_count_matches": result["model"]["constraints"] == 219,
    }


def solve_cflp(inbound_rate=INBOUND_EUR_PAL_KM, time_limit=120):
    m, x, y = build_model(inbound_rate)
    with tempfile.TemporaryDirectory(prefix="cflp-") as tmp:
        log_path = Path(tmp) / "cbc.log"
        solver = pulp.PULP_CBC_CMD(
            msg=False, timeLimit=time_limit, gapRel=0, gapAbs=0, threads=1,
            logPath=str(log_path),
        )
        if not solver.available():
            raise RuntimeError("CBC est indisponible. Installez requirements.txt et vérifiez son exécutable.")
        start = time.perf_counter()
        m.solve(solver)
        elapsed = time.perf_counter() - start
        log = log_path.read_text(encoding="utf-8", errors="replace")

    # LpStatus seul peut indiquer Optimal après une limite de temps !
    proven = (
        m.status == pulp.LpStatusOptimal
        and m.sol_status == pulp.LpSolutionOptimal
        and "Result - Optimal solution found\n" in log
    )
    feasible = m.sol_status in (pulp.LpSolutionOptimal, pulp.LpSolutionIntegerFeasible)
    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "port": PORT[0], "inbound_eur_pal_km": inbound_rate,
            "outbound_eur_pal_km": OUTBOUND_EUR_PAL_KM, "circuity": CIRCUITY,
            "total_demand_pal_year": sum(c[3] for c in CLIENTS),
            "inbound_precision_note": "Le texte indique 0,052 ; l'annexe utilise 1,70 / 33 = 0,051515…",
            "port_to_depot_km": {d[0]: road_km(PORT, d) for d in DEPOTS},
        },
        "model": {"variables": len(m.variables()), "constraints": len(m.constraints)},
        "solver": {
            "name": "CBC", "pulp_version": pulp.__version__,
            "status": pulp.LpStatus[m.status], "solution_status": pulp.LpSolution[m.sol_status],
            "optimality_proven": proven, "feasible_solution_available": feasible,
            "elapsed_seconds": elapsed, "time_limit_seconds": time_limit,
            "relative_gap": 0.0 if proven else None,
            "gap_basis": "Optimum prouvé par CBC (tolérances numériques du solveur)" if proven else "Non établi",
            "log": log,
        },
    }
    if not feasible:
        return result
    verify_solution(m, x, y)
    assignments = []
    for i, client in enumerate(CLIENTS):
        j = next(j for j in y if x[i][j].value() > 0.5)
        assignments.append({"client": client[0], "demand_pal_year": client[3], "warehouse": DEPOTS[j][0]})
    warehouses = []
    for j, depot in enumerate(DEPOTS):
        if y[j].value() < 0.5:
            continue
        served = [a for a in assignments if a["warehouse"] == depot[0]]
        load = sum(a["demand_pal_year"] for a in served)
        warehouses.append({
            "name": depot[0], "capacity_pal_year": depot[4], "load_pal_year": load,
            "utilization_percent": 100 * load / depot[4], "client_count": len(served),
            "clients": [a["client"] for a in served],
        })
    costs = {
        "fixed": sum(DEPOTS[j][3] * y[j].value() for j in y),
        "inbound": sum(CLIENTS[i][3] * x[i][j].value() * road_km(PORT, DEPOTS[j]) * inbound_rate for i in x for j in y),
        "handling": sum(CLIENTS[i][3] * x[i][j].value() * DEPOTS[j][5] for i in x for j in y),
        "outbound": sum(CLIENTS[i][3] * x[i][j].value() * road_km(DEPOTS[j], CLIENTS[i]) * OUTBOUND_EUR_PAL_KM for i in x for j in y),
    }
    costs["total"] = pulp.value(m.objective)
    if not math.isclose(sum(costs[k] for k in ("fixed", "inbound", "handling", "outbound")), costs["total"], abs_tol=1e-6, rel_tol=1e-12):
        raise ValueError("La décomposition des coûts ne correspond pas à l'objectif.")
    result.update({
        "open_warehouses": [w["name"] for w in warehouses],
        "open_warehouse_count": len(warehouses), "assignments": assignments,
        "warehouses": warehouses, "costs_eur_year": costs,
        "decision_variables": {
            "y": {DEPOTS[j][0]: y[j].value() for j in y},
            "x": {CLIENTS[i][0]: {DEPOTS[j][0]: x[i][j].value() for j in y} for i in x},
        },
        "feasibility_checks_passed": True,
    })
    result["reference_comparison"] = compare_reference(result)
    return result


def print_results(result):
    solver = result["solver"]
    print(f"CBC : {solver['status']} / {solver['solution_status']}")
    print(f"Optimalité prouvée : {'oui' if solver['optimality_proven'] else 'non'}")
    gap = solver["relative_gap"]
    print(f"Gap : {gap:.2%}" if gap is not None else "Gap : non établi")
    print(f"Temps de résolution : {solver['elapsed_seconds']:.4f} s")
    print(f"Modèle : {result['model']['variables']} variables, {result['model']['constraints']} contraintes")
    print(f"Coût amont utilisé : {result['parameters']['inbound_eur_pal_km']:.12f} €/palette/km")
    if not solver["feasible_solution_available"]:
        print("Aucune solution entière disponible ; aucun coût ni affectation présenté.")
        return
    print(f"\nEntrepôts ouverts ({result['open_warehouse_count']}) : {', '.join(result['open_warehouses'])}")
    print(f"\n{'Client':30s} {'Demande (pal/an)':>16s}  Entrepôt")
    for a in result["assignments"]:
        print(f"{a['client']:30s} {a['demand_pal_year']:16,d}  {a['warehouse']}")
    print(f"\n{'Entrepôt':12s} {'Capacité':>10s} {'Charge':>10s} {'Utilisation':>12s} {'Clients':>8s}")
    for w in result["warehouses"]:
        print(f"{w['name']:12s} {w['capacity_pal_year']:10,d} {w['load_pal_year']:10,d} {w['utilization_percent']:11.2f}% {w['client_count']:8d}")
    print("\nCoûts annuels :")
    for key, label in (("fixed", "Fixes"), ("inbound", "Transport amont"), ("handling", "Manutention"), ("outbound", "Transport aval"), ("total", "Total")):
        print(f"  {label:18s} : {result['costs_eur_year'][key]:,.2f} €")
    print("\nComparaison avec le PDF (références arrondies à l'euro) :")
    for key, value in result["reference_comparison"].items():
        print(f"  {key} : {value}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results.json"))
    parser.add_argument("--inbound-rate", type=float, default=INBOUND_EUR_PAL_KM,
                        help="€/palette/km ; défaut : fraction 1,70 / 33 de l'annexe")
    args = parser.parse_args()
    result = solve_cflp(inbound_rate=args.inbound_rate)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print_results(result)
    print(f"\nRésultats et journal CBC enregistrés dans {args.output}")
    return 0 if result["solver"]["optimality_proven"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
