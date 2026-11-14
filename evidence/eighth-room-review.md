# Oitava fase — 14/11/2026

O port de `$0B36` mantém posição, velocidade, apoio, escada e queda em coordenadas do Apple II. Ele calcula o próximo movimento com a velocidade anterior e testa os 53 registros de terreno usando as dimensões da pose corrente. `$0A62` seleciona as poses de locomoção. O segundo personagem usa seu próprio conjunto, a partir da pose 49.

O ciclo de espera do Fratelli segue `$61C8`: 26, 20, 57, 20. A pose 57 veio do renderizador HGR. O contador avança a cada cinco atualizações, como no original. A IA escolhe o comando da atualização seguinte e testa o primeiro personagem. O controle do elevador testa o segundo personagem. Trocar com G só muda quem recebe a entrada. O empurrão usa a velocidade positiva do personagem controlado. A segunda das quatro moedas desvia o Fratelli para a direita.

A comparação no XRoar com as rotinas 6502 confirmou 2.000 atualizações de física e pose, cobrindo 20 estados iniciais. Os 128 casos de portões e as 160 atualizações de plataforma, empurrão e moedas também conferiram. O replay parte do início da sala e entrega apenas entradas de controle. Em 1.213 ciclos, os dois personagens alcançam o tesouro com cinco vidas, o Fratelli já removido e 1.000 pontos pela saída. DAC e SSC chegam a `ending_finished`.

Para reproduzir a travessia, use `python tools/replay_second_room.py <build> replay.DSK --room eighth [--mode SSC]`. Para o teste isolado, use `python tools/test_eighth_room.py <build> teste.DSK` e interrompa em `test_passed`. Os 1.600 bytes do teste estão no início do banco físico `$08`. A comparação usa `python tools/verify_eighth_room.py <Apple.dsk> --trace evidence/eighth-6809-trace.bin`.

A comparação cobre o estado da física por atualização lógica. A duração em tempo real e o áudio do cartucho físico estão fora dos testes de emulação.
