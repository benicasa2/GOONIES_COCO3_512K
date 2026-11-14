# Sexta fase: correções e validação — 12/11/2026

Implementados os nove objetos cadentes, suas animações e colisões, o acionamento automático das três placas e a faixa letal inferior. A travessia com esses mecanismos ativos passou nas duas compilações de áudio.

## Código original e tradução

- Apple `$6196`: inicialização dos nove atores de tipo 12; posições, limites e temporizadores extraídos do original.
- Apple `$61CA`: preparação, queda acelerada, impacto e reinício. Os cinco desenhos são as poses 43–47 do renderizador original, convertidas com a mesma paleta do port.
- Apple `$624B–$6265`: os objetos centrais de índices 3, 4 e 5 atribuem 16 ao temporizador da respectiva placa.
- Apple `$636B` e `$610B`: redução dos temporizadores, seleção das plataformas e atualização por contato do personagem. A seleção agora respeita essa ordem. O acionamento por personagem continua atribuindo quatro.
- Apple `$6169`: faixa letal em Y=178, projetada horizontalmente para as coordenadas do port; vale para os dois personagens.
- Foram preservados os efeitos do carry 6502 no cálculo dos intervalos de reinício, incluindo os acréscimos implícitos de uma atualização.

## Verificação

1. Comparação diferencial: 160 atualizações × nove objetos no XRoar contra a execução do Apple II com o mesmo cursor aleatório inicial. Coincidiram posição, pose, velocidade, temporizador, três temporizadores de placas, máscara das plataformas e cursor aleatório. São 8.000 bytes comparados. Essa igualdade é por atualização, não uma medição do tempo físico entre quadros nas duas máquinas.
2. Teste isolado 6809: cada um dos nove objetos provoca morte ao contato; a faixa inferior não mata em Y=160 e mata em Y=161, considerando a altura do personagem. A faixa foi testada com os dois Goonies.
3. Replay de 349 atualizações, desde as posições iniciais da sexta fase. Entradas somente de controle, incluindo G. Sem R, alteração de posições, invulnerabilidade ou desativação de perigos. DAC e SSC chegaram à sétima fase, com cinco vidas e contador de morte zero.
4. Regressão: as travessias das fases quatro e cinco continuam chegando às fases seguintes.
5. O disco de produção abre a apresentação no XRoar. A captura da sexta fase foi inspecionada com os objetos desenhados.

O teste isolado injeta estados para exercitar colisões; o replay de travessia não injeta estados. O XRoar foi configurado como CoCo 3 NTSC de 512 KiB. Os testes usaram saída de áudio desabilitada: não validam a reprodução sonora do cartucho físico. Montagem com lwasm; asm6809 não foi executado nesta revisão.

## Reprodução

- `python tools/verify_sixth_room.py <Apple.dsk> --trace evidence/sixth-6809-trace.bin`
- `python tools/test_sixth_room.py <build> teste.DSK`: monta o teste isolado; interromper no símbolo test_passed. O registro de 8.000 bytes ocupa o início do banco físico `$3D` no snapshot. test_failed indica falha de colisão.
- `python tools/replay_second_room.py <build> replay.DSK --room sixth` (acrescentar `--mode SSC` para a segunda compilação).
- `evidence/sixth-room-input.txt`: controles compactados em pares duração/máscara, terminados por zero.
- `evidence/sixth-playable-room.txt`: rastros dos pontos de aprovação e hashes dos discos.

## Limites remanescentes da apresentação

Estas correções cobrem os mecanismos solicitados. As linhas das plataformas e os indicadores ainda usam o desenho simplificado já existente. A animação decorativa inferior da rotina Apple `$607D` não foi portada nesta alteração. Não se declara equivalência visual integral da fase.
