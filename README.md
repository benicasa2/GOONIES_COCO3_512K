# The Goonies no CoCo 3

Port para CoCo 3 NTSC com 512 KiB. Cenários, poses, paleta de referência, colisões e mecanismos vêm da Apple II. O C64 é a fonte da música.

## Executar

No Windows, abra `Jogar-Goonies.cmd` na mesma pasta de `GOON-DAC.DSK`. O script abre o XRoar e carrega a tela de apresentação. Pressione e solte Espaço para entrar na primeira sala.

Monte `GOON-DAC.DSK` na unidade 0 de um CoCo 3 com Disk Extended Color BASIC. No XRoar, selecione 512 KiB e vídeo RGB.

```basic
PCLEAR 1
RUN"START"
```

| Tecla | Ação |
|---|---|
| ← / → | Mover o Goonie controlado |
| ↑ / ↓ | Subir ou descer uma escada |
| Espaço | Pular quando apoiado |
| G | Alternar o personagem controlado |
| R | Percorrer as salas pelo índice de disco para inspecioná-las |

### Como passar da primeira sala

1. Com o primeiro Goonie, suba pela escada à direita até o andar da cadeira. Passe para a esquerda da cadeira e empurre-a para a direita, até a abertura da escada do sótão. Pule sobre a cadeira e use **↑** para alcançar a escada.
2. No sótão, vá até a máquina à direita e deixe o Goonie junto dela. Espere as notas caírem e a Fratelli ir para a direita para pegá-las. Use **G** para controlar o outro Goonie.
3. Vá até o bebedouro no lado esquerdo do andar de baixo e pressione **→ + Espaço** ao lado dele para derrubá-lo. Espere a água apagar a lareira e use **↓** sobre a abertura e siga pelo porão até a saída à direita.
4. Use **G**, desça do sótão com o primeiro Goonie e leve-o pelo mesmo caminho. A próxima sala carrega quando os dois estiverem na saída.

As transições usam as zonas de saída e a ordem dos overlays do original, 1 → 3 → 2 → 4 → 5 → 6 → 7 → 8. Esses números são os índices do disco usados no relatório.

`GOON-SSC.DSK` usa o Tandy Speech/Sound Cartridge. Os discos incluem a apresentação. Os binários autônomos entram diretamente na primeira sala. Use `EXEC &H2000` após `LOADM`. Reinicie para voltar ao BASIC.

### Estratégia da segunda fase

1. Passe pelas prensas superiores quando recolherem. À direita, entre no elevador com um Goonie. Ele desce sob o peso de qualquer personagem e sobe vazio.
2. Desça pela escada direita e deixe esse Goonie no acionador do piso inferior para levantar a pedra. Pressione **G** e traga o segundo pelo elevador.
3. Ao alcançar a plataforma flutuante pela direita, pressione **→** para deslocá-la para a esquerda. As hastes de retorno exigem atenção durante a travessia. Pule para a saliência esquerda e pegue a chave.
4. Desça com o segundo Goonie para a saída embaixo à esquerda. Use **G** e leve até lá o Goonie que estava no acionador. Ao deixá-lo, a pedra desce e muda a rota do morcego.

A travessia foi reproduzida no XRoar com as duas compilações de áudio. O teste entra diretamente na segunda fase, usa as posições iniciais normais e fornece ao motor apenas os estados dos controles. As sete hastes usam quadros extraídos do Apple II para cada altura. A plataforma carrega os personagens apoiados quando oscila para cima.

Para gerar um disco de reprodução, execute `python tools/replay_second_room.py <pasta-da-compilação> replay.DSK` depois de executar `build.py`. Use `--mode SSC` para a outra compilação. Ao iniciar o disco no XRoar com `RUN"START"`, a fase começa e a sequência de controles é aplicada automaticamente. O arquivo `evidence/second-playable-room.txt` registra o ponto de transição para conferir no emulador.

### Terceira fase

A saída abre quando um Goonie está no interruptor superior direito e o outro no interruptor da plataforma central. Depois de destravar a porta, conduza os dois à saída direita, evitando os disparos do lançador. A porta abre em quatro quadros extraídos do Apple II. O mecanismo do teto percorre o ciclo original de 789 atualizações e solta duas armadilhas verticais com colisão. O lançador entra em ação quando a porta abre ou quando termina a contagem regressiva. A posição vertical de cada atualização vem da execução do código do Apple II, inclusive na primeira troca de faixa após um reinício.

A reprodução de teste entra diretamente nessa fase e usa os controles desde as posições iniciais normais. Gere o disco de reprodução com `python tools/replay_second_room.py <pasta-da-compilação> replay.DSK --room third`.

### Quarta fase

Leve um Goonie de cada vez à saída no canto inferior esquerdo. Para reproduzir a travessia validada, vá para a esquerda pelo andar superior, desça pelos apoios e use **G** quando o primeiro chegar à saída. A chegada dos dois concede três vidas, até o limite de nove.

O puzzle da peça móvel é opcional para a saída. Os três interruptores centrais redirecionam a peça quando ela chega aos cruzamentos. Use um Goonie junto ao desvio inferior para mudar sua direção. Uma chegada ao lado esquerdo remove um degrau e vale 35 pontos. O contador à direita avança quando a peça chega à outra extremidade e, ao reiniciar, pisca e solta cinco partículas que podem atingir os Goonies. A saída também vale 1.000 pontos. O placar mostra a pontuação da partida e o recorde da sessão.

O teste de travessia também aciona o interruptor superior com um pulo. Use `python tools/replay_second_room.py <pasta-da-compilação> replay.DSK --room fourth` para gerar o disco de reprodução.

### Quinta fase

A saída fica na direita. Use as passagens que ligam os corredores centrais e atravesse quando o inimigo voador estiver longe da saída. Leve um Goonie de cada vez e use **G** para trocar. O replay validado espera antes de avançar e usa as passagens centrais com os dois personagens.

Para elevar a plataforma inferior, deixe um Goonie no interruptor superior direito para desligar a armadilha desse lado. Use o outro para conduzir à direita o ovo que cai no piso inferior. Quando o ovo chega ao ponto de detecção, a plataforma sobe um nível e o placar soma 50 pontos. A saída vale 1.000 pontos.

Use `python tools/replay_second_room.py <pasta-da-compilação> replay.DSK --room fifth` para gerar o disco de reprodução. É possível empurrar ovos nas duas direções e conduzi-los pelas passagens em outros pisos. O ovo some durante a travessia da passagem e a criatura eclode a partir da posição onde ele ficou. O contato com o Goonie usa a área de colisão do motor do CoCo 3.

### Sexta fase

Os nove objetos cadentes usam os cinco quadros extraídos do Apple II, aceleram durante a queda e matam ao atingir qualquer Goonie. Os três centrais acionam as placas por 16 atualizações; os temporizadores e a tabela original determinam quais plataformas ficam disponíveis. O contato dos personagens com as placas mantém a regra original de quatro atualizações. A faixa inferior também é letal.

Para atravessar, leve o primeiro Goonie à barra da região central esquerda e use **G**. Com o segundo, espere os ciclos dos objetos e das plataformas para chegar à passagem central inferior, que leva à região superior direita. Deixe-o na barra direita, troque de personagem e conduza o primeiro até a saída inferior direita. Por fim, solte o segundo da barra e leve-o à mesma saída. Evite descer até a faixa azul inferior.

A travessia com todas essas armadilhas ativas passou no XRoar nas compilações DAC e SSC, sem perder vidas. Gere o replay com `python tools/replay_second_room.py <build> replay.DSK --room sixth`. Veja [a validação e seus limites](evidence/sixth-room-review.md).

### Sétima fase

Use a barra superior para liberar a caixa. Empurre a caixa até ela servir de apoio para alcançar a barra inferior. Mantenha um personagem na trava e use o outro para acionar a alavanca esquerda. Depois que o polvo baixar, leve os dois até a saída. A travessia de 456 ciclos passou no XRoar em DAC e SSC. Consulte [o relatório da sétima fase](evidence/seventh-room-review.md).

### Oitava fase

Os quatro acionadores e as três zonas de segurança controlam os portões. Os dois Goonies e o Fratelli usam as velocidades, os apoios, as escadas e as caixas de colisão por pose do Apple II. O segundo personagem aciona o elevador mesmo depois de uma troca com **G**. O Fratelli persegue o primeiro personagem quando ele entra na área de ataque.

A rota faz os personagens alternarem entre as barras e os portões até chegarem ao porão. O segundo personagem sobe à direita e empurra o objeto para soltar quatro moedas. Na segunda emissão, o Fratelli segue para a direita e pode cair no poço. Depois, um personagem embarca no elevador e o segundo aciona a subida. A saída concede 1.000 pontos quando os dois chegam ao tesouro e inicia o encerramento original.

O replay de 1.213 ciclos de controle chegou ao encerramento com cinco vidas no XRoar nas versões DAC e SSC. Use `python tools/replay_second_room.py <build> replay.DSK --room eighth`. Os detalhes da comparação estão em [evidence/eighth-room-review.md](evidence/eighth-room-review.md).

## Apresentação

A apresentação usa a captura da tela de título original da Apple II fornecida pelo usuário, incluída em `assets/title-apple2.png`. O extrator converte a captura de 560×384 para 280×192, centraliza a imagem e aproxima suas cores com uma paleta GIME de 16 entradas. O tema do C64 começa na apresentação. Ao pressionar e soltar Espaço, a primeira sala entra com a sua própria paleta e a música continua.

## Vídeo e fidelidade

Os oito fundos aparecem em 280×192 pixels, sem reamostragem, no centro do modo GIME de 320×192, com margens pretas de 20 pixels. A paleta RGB de 16 cores do GIME é calibrada com a captura Apple II em `assets/gameplay-apple2.png`. A conversão usa a fase HGR e as amostras vizinhas para aproximar as cores de vídeo composto nos oito cenários e no encerramento. Os personagens e inimigos usam quadros coloridos extraídos do renderizador original, de 16×22 pixels, com transparência por pixel. Cada Goonie tem quatro quadros no ciclo de caminhada. O motor projeta as coordenadas lógicas de colisão para a área visível. O mapa de engenharia reversa indica quais mecanismos foram portados e quais ainda precisam de implementação.

## Vidas, mecanismos e armadilhas

O jogo começa com cinco vidas. Depois dos dois quadros de morte, a sala é recarregada e o contador diminui. O zero ainda permite jogar. A morte seguinte mostra a mensagem original de fim de jogo e volta à apresentação nos discos completos. A saída cooperativa do overlay 4 concede três vidas até o limite de nove.

- **Overlay 1.** O Fratelli procura um Goonie na mesma faixa vertical e usa a geometria das paredes. A cadeira móvel dá acesso ao sótão. A máquina distrai a Fratelli por um intervalo e o salto contra o bebedouro inicia a queda animada que apaga a lareira e abre a passagem. As notas são renderizadas a partir dos gráficos HGR. A altura das notas controla a distração e a coleta. O deslocamento geral da Fratelli continua adaptado à física do port.
- **Overlay 2.** Os interruptores cooperativos destravam a saída. A combinação também seleciona as armadilhas letais. Os desenhos dos estados foram extraídos do renderizador HGR da Apple II. O lançador percorre as faixas do original após a abertura da porta ou o fim da contagem regressiva. Ele dispara se houver um Goonie na trajetória.
- **Overlay 3.** As quatro prensas atualizam a colisão conforme a posição. O interruptor libera a saída e permanece acionado ao perder uma vida. As prensas usam máscaras extraídas do original.

- **Overlay 5.** As seis passagens usam a direção de entrada e o deslocamento da tabela original da Apple II em `$658F`. Acione a seta horizontal correspondente ao entrar no ponto da passagem.
- **Overlay 6.** Um Goonie pode ficar suspenso em uma das duas barras e habilitar a passagem do outro. As três placas de pressão, marcadas em laranja e verde, alteram quais das 13 plataformas podem ser usadas. Os oito estados vêm da tabela original em `$63DE`. A mesma tabela define as linhas desenhadas e as superfícies de colisão.
- **Overlay 8.** Quatro pontos de acionamento e três pontos de segurança selecionam a configuração de três portões. As imagens abertas e fechadas vêm da rotina HGR original. O Fratelli persegue o personagem controlado na região de alcance extraída, respeita paredes e segue para a direita após a segunda emissão do objeto empurrável. A plataforma móvel, o empurrão e as quatro quedas estão implementados. O poço mata o Goonie ou anima a morte do Fratelli por oito atualizações antes de removê-lo.
- **Encerramento.** Depois que os dois Goonies chegam à saída final, o port reproduz os 358 quadros lógicos capturados do overlay Apple II e volta à primeira sala. O encerramento está disponível nos discos completos.
- O motor reaproveita os pontos e as temporizações do original. Os obstáculos móveis do overlay 6 continuam pendentes. As linhas de plataforma e os indicadores de pressão são representações simplificadas.

## Reconstruir com os anexos

Use Python 3.10+, Py65, Pillow e LWASM.

```powershell
python -m pip install py65 Pillow
$dsk = "<caminho para o DSK Apple II>"
python tools/prepare.py $dsk build/assets
python tools/verify_apple.py $dsk
python tools/verify_room_mechanisms.py $dsk
python tools/sid_music.py evidence/c64-sid.json build/assets/music.inc
python tools/build.py build/assets build/out
```

As quatro montagens usam LWASM 4.25. A opção `--assembler asm6809` ainda precisa de teste.

## Engenharia reversa e implementação

| Fonte | Rotinas e dados |
|---|---|
| Apple II | `$027E` ordena setores físicos. `$1BAC` decodifica HGR. `$0F2E` seleciona vetores de terreno. `$0BBF` testa colisões. `$0D2A` incrementa e limita a velocidade vertical. |
| Apple II em execução | O harness executa a inicialização até `$086A`, substitui o I/O do disco e a espera em ROM e recupera os slots e as saídas das oito salas. |
| C64 em execução | A captura controlada registra as escritas no SID e seus ciclos aproximados. |
| REA/Ghidra | Os mapas registram a análise estática do descompactado 6510 e do decodificador Apple II. A regra de tradução de `$0951` reconhece a busca de um slot vazio e emite uma implementação 6809. |

A variante DAC mantém o ciclo SID de 49,9 segundos em dois osciladores. A variante SSC toca uma transcrição de toda a gravação fornecida `GOONIES-3VOZES.mp3`, com cerca de 3min20s por volta. A transcrição estima até três notas simultâneas a partir da mixagem mono, sintetizadas pelo AY nos canais A, B e C. Os efeitos do jogo usam brevemente o canal A, depois o sequenciador restaura as três vozes. Para gerar a sequência a partir do áudio, use `python tools/transcribe_ssc.py GOONIES-3VOZES.mp3 assets/ssc-theme.bin` com NumPy e FFmpeg. A tabela resultante já acompanha o projeto.


O motor usa DP=0 e páginas de 8 KiB. Os framebuffers ocupam `$08–$0B` e `$0C–$0F`. Cada fase reserva cinco páginas em `$10–$37`, quatro para bitmap e uma para geometria. O encerramento usa `$00–$03` para o fundo e `$04–$07` para as alterações entre quadros, com o último trecho no banco de geometria da sala 4. Cada linha ocupa 160 bytes e o blitter muda a janela da MMU ao cruzar uma página. O Disk BASIC carrega os blocos a partir de `$4000` e descomprime os bancos de cada sala com LZ. A janela de destino usa `$FFA3` para a janela `$6000–$7FFF`. O motor restaura e redesenha retângulos de 16×22 pixels no framebuffer traseiro por `$FFA2`. O IRQ VBORD alterna `$FF9D/$FF9E` depois que o quadro está pronto.

No DAC, o FIRQ avança o acumulador de fase e escreve as amostras em `$FF20`. No SSC, o FIRQ consulta o bit 7 em `$FF7E` antes de enviar comandos. `$FF7D` reinicia o cartucho. Boot e vídeo foram exercitados no XRoar. O som do SSC em hardware ainda precisa de validação. [Manual do cartucho Tandy](https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Speech-Sound%20Cartridge%20%28Tandy%29.pdf).

## Evidências

- `evidence/assets.json` registra as oito capturas, a geometria, as saídas, as poses e o contraste.
- `evidence/verification.txt` contém a comparação HGR e os rastros anteriores.
- `evidence/mechanisms-verification.txt` registra as comparações 6502 e as três transições no XRoar. Os arquivos `room1-input.hex`, `room5-input.hex` e `room6-input.hex` guardam as sequências injetadas. O byte usa os bits 0–3 para cima, baixo, esquerda e direita, o bit 5 para alternar o jogador, o bit 6 para pular e o bit 7 para mudar a sala de inspeção. O último byte FF termina a sequência.
- Os arquivos `.sym` e `.map` separam os endereços por plataforma e fase de carregamento.
- `evidence/analise-apple-ii.md` documenta os endereços dos puzzles, armadilhas, inimigos e do encerramento.
- `evidence/final-theme-verification.txt` registra os testes desta revisão.
- `evidence/video-280-verification.txt` registra as verificações dos discos e os rastros do modo de vídeo atual. Os comparativos de cores anteriores são históricos.
- Os objetivos cooperativos constam do manual distribuído sob licença da Datasoft. [Manual de The Goonies](https://uta.pokefinder.org/Ultimate_Tape_Archive/Goonies%2C_The_%281986_American_Action_AB%29_%5B6951%5D/Extras/Instructions.pdf).

A sexta fase usa o banco físico `$3C` para gráficos e dados dos objetos. Durante o BASIC, `CODE6` e `NATIVE8` são carregados em bancos ocultos do segundo framebuffer. Após `EXEC`, o motor copia esses bancos para `$3C` e `$3E` e carrega a apresentação a partir da cópia mantida com a geometria das salas. Os nove slots e o histórico de desenho da sexta fase são compartilhados com a quinta.

A oitava fase instala sua rotina em `$0400`, junto com a inicialização dos overlays após EXEC. Os desenhos ficam no banco físico `$3D`, reutilizado somente após o BASIC terminar. Os dados comprimidos são transportados na área invisível dos bitmaps das salas 2 e 3. As paletas ficam em `$1DE0`, separadas do motor e da pilha, para manter as duas versões dentro da janela de carregamento. O disco continua no formato de 35 trilhas.
