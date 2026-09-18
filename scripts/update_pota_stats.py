"""
POTA Portugal - Atualizador Diário de Estatísticas Oficiais
Executa diariamente (ex: às 20:00) via GitHub Actions ou cron local.
Consulta a API oficial do POTA (api.pota.app) para Continente (272), Açores (149) e Madeira (256).
Gera um ficheiro 'pota_stats.json' ultra-leve (~2 KB) com métricas consolidadas e Top Parques.
"""

import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta

# Configurações
ENTITIES = [
    {"id": 272, "name": "Portugal Continental", "prefix": "CT"},
    {"id": 149, "name": "Açores", "prefix": "CU"},
    {"id": 256, "name": "Madeira", "prefix": "CT3"}
]

HEADERS = {
    'User-Agent': 'POTAPortugal-DailyUpdater/1.0 (pota.pt; open-data)',
    'Accept': 'application/json'
}

def fetch_entity_parks(entity_id):
    url = f"https://api.pota.app/entity/parks/{entity_id}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status == 200:
            return json.loads(resp.read().decode('utf-8'))
    return []

def main():
    print("=== POTA Portugal: Atualizador de Estatísticas Oficiais ===")
    all_parks = []
    
    for ent in ENTITIES:
        print(f"A descarregar dados de {ent['name']} (ID {ent['id']})...")
        try:
            parks = fetch_entity_parks(ent['id'])
            print(f"  -> {len(parks)} parques obtidos.")
            all_parks.extend(parks)
        except Exception as e:
            print(f"  [AVISO] Erro ao obter entidade {ent['id']}: {e}")

    if not all_parks:
        print("[ERRO] Nenhum parque foi retornado da API. A abortar sem sobrescrever cache.")
        return

    # Cálculos Consolidados
    total_parks = len(all_parks)
    total_activations = sum(p.get('activations', 0) for p in all_parks)
    total_qsos = sum(p.get('qsos', 0) for p in all_parks)
    total_attempts = sum(p.get('attempts', 0) for p in all_parks)
    
    # Parques nunca ativados (0 ativações)
    never_activated = [
        {
            "reference": p.get('reference'),
            "name": p.get('name'),
            "locationDesc": p.get('locationDesc')
        }
        for p in all_parks if p.get('activations', 0) == 0
    ]

    # Top 10 Parques Mais Ativados
    sorted_by_acts = sorted(all_parks, key=lambda x: x.get('activations', 0), reverse=True)
    top_activated = [
        {
            "rank": i + 1,
            "reference": p.get('reference'),
            "name": p.get('name'),
            "locationDesc": p.get('locationDesc'),
            "activations": p.get('activations', 0),
            "qsos": p.get('qsos', 0),
            "attempts": p.get('attempts', 0)
        }
        for i, p in enumerate(sorted_by_acts[:10])
    ]

    # Top 10 Parques com Mais QSOs
    sorted_by_qsos = sorted(all_parks, key=lambda x: x.get('qsos', 0), reverse=True)
    top_qsos = [
        {
            "rank": i + 1,
            "reference": p.get('reference'),
            "name": p.get('name'),
            "locationDesc": p.get('locationDesc'),
            "qsos": p.get('qsos', 0),
            "activations": p.get('activations', 0)
        }
        for i, p in enumerate(sorted_by_qsos[:10])
    ]

    # Data e hora de Lisboa (UTC+0 ou UTC+1 com base em DST)
    now_utc = datetime.now(timezone.utc)
    # Fuso de Lisboa aproximado
    lisbon_time_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

    payload = {
        "metadata": {
            "source": "api.pota.app",
            "updated_at_utc": now_utc.isoformat(),
            "updated_at_human": lisbon_time_str,
            "scope": "Portugal (Continente, Açores, Madeira)"
        },
        "summary": {
            "total_parks": total_parks,
            "total_activations": total_activations,
            "total_qsos": total_qsos,
            "total_attempts": total_attempts,
            "never_activated_count": len(never_activated)
        },
        "top_activated": top_activated,
        "top_qsos": top_qsos
    }

    # Gravar ficheiro JSON
    output_path = "pota_stats.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\n[SUCESSO] Ficheiro '{output_path}' gerado com sucesso!")
    print(f"  -> Total de Parques: {total_parks}")
    print(f"  -> Total de Ativações: {total_activations:,}")
    print(f"  -> Total de QSOs: {total_qsos:,}")
    print(f"  -> Parques Nunca Ativados: {len(never_activated)}")

if __name__ == "__main__":
    main()
