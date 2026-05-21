# Gerenciador de Torneio Suíço

Um sistema web robusto para gerenciamento de torneios no formato Suíço, construído com **Python (Flask)**. Projetado para garantir integridade competitiva, este aplicativo realiza o emparceiramento de jogadores sem repetição de partidas e calcula os desempates seguindo regras oficiais de torneios de Yu-Gi-Oh! TCG.

## Funcionalidades Principais

* **Emparceiramento Suíço Avançado (Global Backtracking):** O núcleo da aplicação resolve o problema clássico de *deadlocks* em rodadas finais. Utilizando *backtracking* global, o algoritmo avalia a tabela completa para garantir que dois jogadores nunca se enfrentem mais de uma vez no mesmo torneio, priorizando sempre confrontos entre pontuações iguais ou semelhantes.
* **Gestão de Rodadas e Tempo:** Interface intuitiva para iniciar rodadas, rodar cronômetros persistentes, registrar vitórias e, se necessário, reverter para a rodada anterior para correção de erros.
* **Tratamento Inteligente de *Byes*:** Em torneios com número ímpar de participantes, o sistema identifica e atribui o *Bye* automaticamente ao jogador de menor pontuação que ainda não tenha ficado de fora de nenhuma rodada.
**Sistema de Desempate Oficial (Tie-Breakers):** A lógica de desempate é baseada nas políticas rigorosas do software de torneios da Konami (KTS). O sistema calcula automaticamente:


  * **Pontuação Base (AA):** 3 pontos por vitória, 0 pontos por derrota.


  * **OMW - *Opponent's Match-Win Percentage* (BBB):** A porcentagem de vitórias dos oponentes enfrentados.


  * **OOMW - *Opponent's Opponent's Match-Win Percentage* (CCC):** A porcentagem de vitórias dos oponentes dos oponentes.


  * **SSRL (DDD):** A soma dos quadrados das rodadas em que o jogador perdeu partidas.





## Tecnologias Utilizadas

* **Backend:** Python, Flask
* **Frontend:** HTML, CSS, JavaScript (para controle de UI e relógios)
* **Deploy e Integração:** GitHub, Render

## Lógica do Algoritmo (`global_try_pairing`)

Diferente de abordagens gulosas (*greedy*) que pareiam jogadores do topo da tabela apenas para travar nas rodadas finais por falta de oponentes inéditos, nosso sistema previne falhas através de recursão.

Os jogadores entram na função ordenados por pontos e desempates (`build_tiebreaker`). O algoritmo tenta o casamento ideal; se nas sub-listas seguintes o emparceiramento for impossível devido ao histórico de partidas (`can_play`), ele retorna `None`, desfazendo o nó atual e tentando o próximo oponente válido para o topo da tabela. Isso garante um torneio matematicamente perfeito sempre que as combinações permitirem.

---

**Desenvolvido por Peterson Batista**
