from pathlib import Path

from flask import Flask, render_template, request, jsonify
import random

from models.player import Player
from models.tournament import Tournament
from models.match import Match
from services.event_store import EventStore
from services.pairing import swiss_pairing
from services.scoring import apply_match_result
from services.tiebreakers import OMW, OOMW, SSRL
from main import print_standings

app = Flask(__name__)

EVENT_STORE_PATH = Path(__file__).with_name("event_store.json")
event_store = EventStore(EVENT_STORE_PATH)

estado = {
    "tournament": None,
    "total_rounds": 0,
    "current_matches": [],
    "ranking_atual": [],
    "historico_rodadas": [],
    "historico_rankings": [],
    "player_snapshot": None,
    "player_snapshots": [],
    "finalizado": False,
    "event_store": event_store,
}


def registrar_evento(event_type, **data):
    return event_store.append(event_type, data)


def snapshot_ranking(t):
    ranked = sorted(
        t.players,
        key=lambda p: (p.points, OMW(p), OOMW(p), SSRL(p, t)),
        reverse=True,
    )
    return [
        {
            "nome": p.name,
            "pontos": p.points,
            "omw": round(OMW(p), 2),
            "oomw": round(OOMW(p), 2),
            "ssrl": SSRL(p, t),
        }
        for p in ranked
    ]


def salvar_player_snapshot(rodada_num):
    t = estado["tournament"]
    snapshot = {
        "rodada": rodada_num,
        "players": [
            {
                "id": p.id,
                "points": p.points,
                "opponent_ids": [op.id for op in p.opponents],
                "bye_count": getattr(p, "bye_count", 0),
            }
            for p in t.players
        ],
        "num_rounds_antes": len(t.rounds) - 1,
    }
    estado["player_snapshot"] = snapshot
    estado["player_snapshots"].append(snapshot)
    return snapshot


def restaurar_player_snapshot(snap):
    t = estado["tournament"]
    players_by_id = {p.id: p for p in t.players}

    for ps in snap["players"]:
        p = players_by_id[ps["id"]]
        p.points = ps["points"]
        p.opponents = [players_by_id[oid] for oid in ps["opponent_ids"]]
        if hasattr(p, "bye_count"):
            p.bye_count = ps["bye_count"]

    t.rounds = t.rounds[: snap["num_rounds_antes"]]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/iniciar', methods=['POST'])
def iniciar_torneio():
    estado["finalizado"] = False
    estado["historico_rodadas"] = []
    estado["historico_rankings"] = []
    estado["player_snapshot"] = None
    estado["player_snapshots"] = []

    dados = request.get_json()
    try:
        estado["total_rounds"] = int(dados.get('rounds', 3))
    except (TypeError, ValueError):
        return jsonify({"erro": "Número de rodadas deve ser maior que zero"}), 400

    nomes = dados.get('names', [])

    if not nomes:
        return jsonify({"erro": "Nenhum nome de jogador foi enviado"}), 400

    if estado["total_rounds"] <= 0:
        return jsonify({"erro": "Número de rodadas deve ser maior que zero"}), 400

    if event_store.replay():
        event_store.clear()

    registrar_evento("tournament_started", total_rounds=estado["total_rounds"], names=nomes)

    random.shuffle(nomes)
    players = [Player(i, nome) for i, nome in enumerate(nomes)]
    estado["tournament"] = Tournament(players)
    estado["ranking_atual"] = snapshot_ranking(estado["tournament"])

    return jsonify({"mensagem": "Torneio iniciado", "num_players": len(players)})


@app.route('/proxima_rodada', methods=['GET'])
def proxima_rodada():
    t = estado["tournament"]

    if len(t.rounds) >= estado["total_rounds"]:
        return jsonify({"finalizado": True})

    round_obj = t.start_new_round()

    # Usa len(t.rounds) como número autoritativo — o contador interno
    rodada_num = len(t.rounds)
    round_obj.number = rodada_num

    pairings = swiss_pairing(t)
    matches = [Match(p1, p2, rodada_num) for p1, p2 in pairings]
    round_obj.matches = matches
    estado["current_matches"] = matches

    partidas_json = [
        {
            "id": i,
            "p1": m.p1.name,
            "p2": m.p2.name if m.p2 else "BYE",
            "is_bye": m.is_bye(),
        }
        for i, m in enumerate(matches)
    ]

    registrar_evento(
        "round_started",
        rodada=rodada_num,
        pairings=[{"p1": m.p1.name, "p2": m.p2.name if m.p2 else "BYE"} for m in matches],
        partidas=partidas_json,
    )

    return jsonify({
        "rodada_atual": rodada_num,
        "partidas": partidas_json,
        "pode_voltar": bool(estado.get("player_snapshots")),
    })


@app.route('/enviar_resultados', methods=['POST'])
def enviar_resultados():
    resultados = request.json.get('resultados')
    matches = estado["current_matches"]
    t = estado["tournament"]
    rodada_num = len(t.rounds)

    salvar_player_snapshot(rodada_num)

    for i, match in enumerate(matches):
        if match.is_bye():
            apply_match_result(match)
            continue

        res = resultados[i]
        if res == "1":
            match.winner = match.p1
        elif res == "2":
            match.winner = match.p2
        else:
            match.winner = None

        apply_match_result(match)

    print_standings(t)

    partidas_snapshot = [
        {
            "id": i,
            "p1": m.p1.name,
            "p2": m.p2.name if m.p2 else "BYE",
            "is_bye": m.is_bye(),
            "vencedor": (
                m.p1.name if m.winner == m.p1
                else m.p2.name if m.winner == m.p2
                else None
            ) if not m.is_bye() else None,
        }
        for i, m in enumerate(matches)
    ]

    estado["historico_rodadas"].append({"rodada": rodada_num, "partidas": partidas_snapshot})

    ranking_snap = snapshot_ranking(t)
    estado["historico_rankings"].append({"rodada": rodada_num, "ranking": ranking_snap})
    estado["ranking_atual"] = ranking_snap
    estado["finalizado"] = rodada_num >= estado["total_rounds"]

    registrar_evento(
        "results_applied",
        rodada=rodada_num,
        resultados=[
            {"id": i, "vencedor": (m.p1.name if m.winner == m.p1 else m.p2.name if m.winner == m.p2 else None) if not m.is_bye() else None}
            for i, m in enumerate(matches)
        ],
        ranking=ranking_snap,
    )

    return jsonify({"mensagem": "Resultados aplicados com sucesso"})


@app.route('/voltar_rodada', methods=['POST'])
def voltar_rodada():
    t = estado["tournament"]

    if not t:
        return jsonify({"erro": "Nenhum torneio ativo"}), 400

    payload = request.get_json(silent=True) or {}
    quantidade = int(payload.get("quantidade", 1))

    if quantidade < 1:
        return jsonify({"erro": "Quantidade de rodadas para reverter deve ser maior que zero"}), 400

    if len(estado["player_snapshots"]) < quantidade:
        return jsonify({"erro": "Não há snapshots suficientes para reverter esse número de rodadas"}), 400

    rodadas_revertidas = []
    for _ in range(quantidade):
        snap = estado["player_snapshots"].pop()
        rodadas_revertidas.append(snap["rodada"])
        restaurar_player_snapshot(snap)

        estado["historico_rodadas"] = [r for r in estado["historico_rodadas"] if r["rodada"] != snap["rodada"]]
        estado["historico_rankings"] = [r for r in estado["historico_rankings"] if r["rodada"] != snap["rodada"]]

    estado["player_snapshot"] = estado["player_snapshots"][-1] if estado["player_snapshots"] else None
    estado["current_matches"] = []
    estado["finalizado"] = False
    estado["ranking_atual"] = snapshot_ranking(t)

    for rodada_revertida in rodadas_revertidas:
        registrar_evento("round_reverted", rodada=rodada_revertida, ranking=estado["ranking_atual"])

    return jsonify({"rodada_atual": len(t.rounds), "revertidas": quantidade})


@app.route('/resetar', methods=['POST'])
def resetar_torneio():
    estado.update({
        "tournament": None,
        "total_rounds": 0,
        "current_matches": [],
        "ranking_atual": [],
        "finalizado": False,
        "historico_rodadas": [],
        "historico_rankings": [],
        "player_snapshot": None,
        "player_snapshots": [],
    })

    event_store.clear()
    return jsonify({"mensagem": "Torneio resetado com sucesso"})


@app.route('/status', methods=['GET'])
def status_torneio():
    if estado["tournament"] is None:
        return jsonify({"ativo": False})

    t = estado["tournament"]

    partidas_json = [
        {
            "id": i,
            "p1": m.p1.name,
            "p2": m.p2.name if m.p2 else "BYE",
            "is_bye": m.is_bye(),
        }
        for i, m in enumerate(estado["current_matches"])
    ]

    return jsonify({
        "ativo": True,
        "finalizado": estado["finalizado"],
        "rodada_atual": len(t.rounds),
        "total_rounds": estado["total_rounds"],
        "pode_voltar": bool(estado.get("player_snapshots")),
        "partidas": partidas_json,
    })


@app.route('/classificacao', methods=['GET'])
def classificacao():
    return jsonify({"ranking": estado.get("ranking_atual", [])})


@app.route('/historico', methods=['GET'])
def historico():
    return jsonify({
        "historico_rodadas": estado.get("historico_rodadas", []),
        "historico_rankings": estado.get("historico_rankings", []),
    })


@app.route('/historico/rodada/<int:num>', methods=['GET'])
def historico_rodada(num):
    rodadas = estado.get("historico_rodadas", [])
    rankings = estado.get("historico_rankings", [])

    rodada = next((r for r in rodadas if r["rodada"] == num), None)
    if rodada is None:
        return jsonify({"erro": f"Rodada {num} não encontrada"}), 404

    ranking = next((r for r in rankings if r["rodada"] == num), None)

    return jsonify({
        "rodada": num,
        "partidas": rodada["partidas"],
        "ranking": ranking["ranking"] if ranking else [],
    })


if __name__ == '__main__':
    app.run(debug=True)