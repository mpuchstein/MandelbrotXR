"""Print the de-anonymized rank matrix (folders x judges, mean rank) as a Markdown table.
Usage: judge_aggregate.py <repo> <judge-mapping.json>
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from judge_prompts import FOLDER
from judge_finalize import check_ranking

def matrix(R, mapping):
    ranks = {}
    for judge, folder in FOLDER.items():
        _, order = check_ranking(open(f"{R}/Judge/{folder}/RANKING.md").read())
        assert sorted(order) == list("ABCDEFGH"), (judge, order)
        for pos, letter in enumerate(order, 1):
            ranks.setdefault(mapping[judge][letter]["name"], {})[judge] = pos
    return ranks

if __name__ == "__main__":
    R, M = sys.argv[1], json.load(open(sys.argv[2]))
    ranks = matrix(R, M)
    judges = list(FOLDER)
    rows = sorted(ranks.items(), key=lambda kv: sum(kv[1].values()) / len(judges))
    print("| Folder | Prompt | " + " | ".join(FOLDER[j].replace("-Judge", "") for j in judges) + " | Mean |")
    print("|---|---|" + "---|" * len(judges) + "---|")
    for name, r in rows:
        assert len(r) == len(judges)
        print(f"| `{name}` | v{name[-1]} | " + " | ".join(str(r[j]) for j in judges) + f" | {sum(r.values()) / len(judges):.1f} |")
