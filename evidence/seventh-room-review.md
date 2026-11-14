# Sétima fase — 14/11/2026

A fase usa as 37 linhas de colisão originais para os Goonies e as cinco linhas próprias da caixa. A barra superior solta a caixa, que pode ser empurrada e usada como apoio. A barra inferior destrava a alavanca esquerda, que drena a água e baixa o polvo. A alavanca direita mantém o comportamento original de trampolim. O port usa as rotinas $642B, $63DE, $62FA e $6231 como referência.

Foram extraídos os desenhos HGR da caixa, das alavancas, do polvo, dos morcegos e das ondas. As 16 ondas usam as trajetórias de $613B. A lógica inclui as três correntes, o sorteio e as trajetórias dos morcegos e os contatos letais do polvo e do poço.

A comparação 6502/6809 confirmou 456 ciclos consecutivos de posição, velocidade, pose, estado da caixa, drenagem, altura do polvo, índice aleatório e estado das ondas. O replay completo usou somente controles, incluindo G. DAC e SSC chegaram à fase 8 com cinco vidas e 1.550 pontos (50 pela caixa, 500 pela drenagem e 1.000 pela saída). O replay da fase 8 em DAC também voltou a alcançar o encerramento.

Para reproduzir, use `python tools/replay_second_room.py <build> replay.DSK --room seventh [--mode SSC]`. A validação foi feita no XRoar. A cadência em hardware físico e a equivalência visual pixel a pixel com o vídeo composto ainda não foram medidas. O respawn usa a reinicialização de sala do port.
