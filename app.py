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

# Variáveis globais para armazenar o estado do torneio em memória
estado = {
    "tournament": None,
    "total_rounds": 0,
    "current_matches": [],
    "current_ranking": []
}

def atualizar_snapshot_ranking():
    t = estado["tournament"]
    if not t:
        return
        
    ranked = sorted(
        t.players,
        key=lambda p: (p.points, OMW(p), OOMW(p), SSRL(p, t)),
        reverse=True
    )
    
    ranking_json = []
    for p in ranked:
        ranking_json.append({
            "nome": p.name,
            "pontos": p.points,
            "omw": round(OMW(p), 2),
            "oomw": round(OOMW(p), 2),
            "ssrl": SSRL(p, t)
        })
        
    estado["ranking_atual"] = ranking_json

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/iniciar', methods=['POST'])
def iniciar_torneio():
    dados = request.get_json()
    print(f"DEBUG: Dados recebidos no servidor: {dados}") # Isso aparecerá nos logs do Render
    
    estado["total_rounds"] = int(dados.get('rounds', 3))
    nomes = dados.get('names', [])

    if not nomes or len(nomes) == 0:
        return jsonify({"erro": "Nenhum nome de jogador foi enviado ou a lista está vazia"}), 400

    try:
        with open('players.txt', 'w', encoding='utf-8') as f:
            for nome in nomes:
                f.write(f"{nome}\n")
    except Exception as e:
        print(f"Erro ao salvar arquivo: {e}")

    
    random.shuffle(nomes)
    players = [Player(i, nome) for i, nome in enumerate(nomes)]
    estado["tournament"] = Tournament(players)
    
    
    atualizar_snapshot_ranking()
    
    return jsonify({
        "mensagem": "Torneio iniciado e nomes salvos", 
        "num_players": len(players)
    })

@app.route('/proxima_rodada', methods=['GET'])
def proxima_rodada():
    t = estado["tournament"]
    
    if len(t.rounds) >= estado["total_rounds"]:
        return jsonify({"finalizado": True})

    round_obj = t.start_new_round()
    pairings = swiss_pairing(t)
    matches = []
    
    for p1, p2 in pairings:
        match = Match(p1, p2, round_obj.number)
        matches.append(match)
        
    round_obj.matches = matches
    estado["current_matches"] = matches

    # Formatar as partidas para enviar ao front-end
    partidas_json = []
    for i, m in enumerate(matches):
        p1_name = m.p1.name
        p2_name = m.p2.name if m.p2 else "BYE"
        partidas_json.append({"id": i, "p1": p1_name, "p2": p2_name, "is_bye": m.is_bye()})

    return jsonify({
        "rodada_atual": round_obj.number,
        "partidas": partidas_json
    })

@app.route('/enviar_resultados', methods=['POST'])
def enviar_resultados():
    resultados = request.json.get('resultados') # Lista de resultados [1, 2, 0, etc]
    matches = estado["current_matches"]
    
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
            match.winner = None # Empate / Double Loss
            
        apply_match_result(match)

    print_standings(estado["tournament"])
    print("\n")
    
    atualizar_snapshot_ranking()

    return jsonify({"mensagem": "Resultados aplicados com sucesso"})


@app.route('/classificacao', methods=['GET'])
def classificacao():
    t = estado["tournament"]
    ranked = sorted(
        t.players,
        key=lambda p: (p.points, OMW(p), OOMW(p), SSRL(p, t)),
        reverse=True
    )
    
    ranking_json = []
    for p in ranked:
        ranking_json.append({
            "nome": p.name,
            "pontos": p.points,
            "omw": round(OMW(p), 2),
            "oomw": round(OOMW(p), 2),
            "ssrl": SSRL(p, t)
        })
        
    return jsonify({"ranking": estado.get("ranking_atual", [])})

if __name__ == '__main__':
    app.run(debug=True)