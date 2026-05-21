from flask import Flask, render_template, request, jsonify
import random

from models.player import Player
from models.tournament import Tournament
from models.match import Match
from services.pairing import swiss_pairing
from services.scoring import apply_match_result
from services.tiebreakers import OMW, OOMW, SSRL
from main import print_standings

app = Flask(__name__)

estado = {
    "tournament": None,
    "total_rounds": 0,
    "current_matches": [],
    "ranking_atual": [],
    "finalizado": False,
    "historico_rodadas": [],
    "historico_rankings": [],
    "player_snapshot": None,
}


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
    estado["player_snapshot"] = {
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

    dados = request.get_json()
    estado["total_rounds"] = int(dados.get('rounds', 3))
    nomes = dados.get('names', [])

    if not nomes:
        return jsonify({"erro": "Nenhum nome de jogador foi enviado"}), 400

    try:
        with open('players.txt', 'w', encoding='utf-8') as f:
            f.writelines(f"{nome}\n" for nome in nomes)
    except Exception as e:
        print(f"Erro ao salvar players.txt: {e}")

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

    return jsonify({
        "rodada_atual": rodada_num,
        "partidas": partidas_json,
        "pode_voltar": estado["player_snapshot"] is not None,
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

    return jsonify({"mensagem": "Resultados aplicados com sucesso"})


@app.route('/voltar_rodada', methods=['POST'])
def voltar_rodada():
    t = estado["tournament"]

    if not t:
        return jsonify({"erro": "Nenhum torneio ativo"}), 400

    if estado["player_snapshot"] is None:
        return jsonify({"erro": "Não é possível voltar mais de uma rodada seguida"}), 400

    snap = estado["player_snapshot"]
    estado["player_snapshot"] = None
    rodada_revertida = snap["rodada"]

    restaurar_player_snapshot(snap)

    estado["historico_rodadas"] = [r for r in estado["historico_rodadas"] if r["rodada"] != rodada_revertida]
    estado["historico_rankings"] = [r for r in estado["historico_rankings"] if r["rodada"] != rodada_revertida]
    estado["current_matches"] = []
    estado["finalizado"] = False
    estado["ranking_atual"] = snapshot_ranking(t)

    return jsonify({"rodada_atual": len(t.rounds)})


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
    })

    try:
        open('players.txt', 'w').close()
    except Exception as e:
        print(f"Erro ao esvaziar players.txt: {e}")

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
        "pode_voltar": estado["player_snapshot"] is not None,
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