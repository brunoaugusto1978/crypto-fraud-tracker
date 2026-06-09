"""
INVESTIGATION SCORER - Scoring inteligente sem diluicao de media.
"""
from typing import List, Dict

CATEGORY_RISK = {
    "ransomware": 100, "scam": 90, "darknet": 85, "mixer": 80,
    "gambling": 40, "marketplace": 35, "exchange": 25,
    "unknown": 10, "legitimate": 0,
}


class InvestigationScorer:
    def score_investigation(self, initial_wallet, wallets, enrichments, risk_scores):
        score_map = {s.get("wallet"): s.get("risk_score", 0) for s in risk_scores}
        initial_score = score_map.get(initial_wallet, 0)
        all_scores = [s.get("risk_score", 0) for s in risk_scores] or [0]
        max_score = max(all_scores)
        avg_score = sum(all_scores) / len(all_scores)

        weighted_sum = 0.0
        weight_total = 0.0
        for idx, wallet in enumerate(wallets):
            weight = 1.0 / (idx + 1)
            weighted_sum += score_map.get(wallet, 0) * weight
            weight_total += weight
        weighted_score = weighted_sum / weight_total if weight_total else 0

        dangerous = []
        propagation_risk = 0
        for wallet in wallets:
            category = enrichments.get(wallet, {}).get("category", "unknown")
            cat_risk = CATEGORY_RISK.get(category, 0)
            if category in ("ransomware", "scam", "darknet", "mixer") and wallet != initial_wallet:
                dangerous.append({"wallet": wallet, "category": category})
            propagation_risk = max(propagation_risk, cat_risk)

        initial_category = enrichments.get(initial_wallet, {}).get("category", "unknown")

        overall = max(initial_score, weighted_score, propagation_risk if dangerous else 0)
        overall = round(min(100.0, overall), 1)

        return {
            "overall_risk_score": overall,
            "risk_level": self._level(overall),
            "initial_wallet_category": initial_category,
            "initial_wallet_score": round(initial_score, 1),
            "max_risk_score": round(max_score, 1),
            "weighted_risk_score": round(weighted_score, 1),
            "propagation_risk": propagation_risk,
            "average_risk_score": round(avg_score, 1),
            "dangerous_destinations": dangerous,
            "explanation": self._explain(initial_score, weighted_score, propagation_risk, dangerous, initial_category),
        }

    @staticmethod
    def _level(score):
        if score >= 80: return "critical"
        if score >= 50: return "high"
        if score >= 25: return "medium"
        return "low"

    @staticmethod
    def _explain(initial, weighted, propagation, dangerous, initial_category="unknown"):
        category_desc = {
            "ransomware": "a carteira investigada esta associada a ransomware",
            "scam": "a carteira investigada esta associada a scam",
            "darknet": "a carteira investigada esta associada a darknet",
            "mixer": "a carteira investigada e um mixer (servico de anonimizacao)",
            "exchange": "a carteira investigada e uma exchange (ponto de cash-out)",
            "gambling": "a carteira investigada e de gambling",
            "marketplace": "a carteira investigada e um marketplace",
        }
        parts = []
        if initial_category in category_desc:
            parts.append(category_desc[initial_category])
        elif initial >= 50:
            parts.append(f"carteira inicial de alto risco (score {round(initial, 1)})")
        if dangerous:
            cats = ", ".join(sorted({d["category"] for d in dangerous}))
            parts.append(f"fundos fluem para destinos perigosos: {cats}")
        if weighted >= 50 and not parts:
            parts.append("alto risco ponderado nas wallets proximas a origem")
        if not parts:
            parts.append("nenhum indicador critico identificado na cadeia")
        return "; ".join(parts)
