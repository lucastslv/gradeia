<script lang="ts">
	import { CONFLICT_BORDER, type GradeColor } from '$lib/colors';
	import type { GradeItem } from '$lib/grade.svelte';
	import {
		ALMOCO,
		FAIXA_PADRAO,
		faixaHoraria,
		formatHora,
		layoutSemana,
		marcasHorarias,
		type Bloco,
		type Faixa
	} from '$lib/layout';
	import { DAY_ABBR, DAY_NAMES, type Session } from '$lib/types';

	interface Props {
		/** As cadeiras da grade, já resolvidas na turma ativa (`Grade.items`). */
		items: GradeItem[];
		/** Início da faixa visível, em minutos; ela cresce se alguma aula começar antes. */
		start?: number;
		/** Fim da faixa visível, em minutos; ela cresce se alguma aula terminar depois. */
		end?: number;
		/** Altura de um minuto, em px — o zoom vertical da grade. */
		pxPerMin?: number;
		/** Faixa separadora desenhada atrás dos blocos; `null` esconde. */
		intervalo?: Faixa | null;
		/** Com isso os blocos ficam arrastáveis: segurar/arrastar mostra os horários
		 *  das outras turmas da mesma cadeira e soltar sobre eles troca a turma. */
		onescolher?: (code: string, letter: string) => void;
		/** Trocar para esta turma criaria conflito? Onde a marcação de conflito dos
		 *  fantasmas se apoia antes do clique/soltar. */
		turmaConflita?: (code: string, letter: string) => boolean;
	}

	let {
		items,
		start = FAIXA_PADRAO.start,
		end = FAIXA_PADRAO.end,
		pxPerMin = 1.3,
		intervalo = ALMOCO,
		onescolher,
		turmaConflita
	}: Props = $props();

	/** Cadeira segurada (`course.code`) — cujas turmas alternativas ganham fantasma. */
	let arrastando = $state<string | null>(null);
	/** A ativação veio de um "segurar" (toque), não de um arrasto de fato. Nesse
	 *  modo os fantasmas respondem a clique e um toque fora da grade fecha. */
	let segurando = $state(false);
	/** Soltar o dedo que ativou o modo dispara um `click` — não pode fechá-lo. */
	let ignorarProximoClick = false;
	let timerPressionar: ReturnType<typeof setTimeout> | undefined;
	/** Cadeira da última troca via drag — pisca para a troca ficar visível
	 *  mesmo quando a turma nova cai no mesmo horário da antiga. */
	let piscando = $state<string | null>(null);
	let timerPiscada: ReturnType<typeof setTimeout> | undefined;
	/** Onde o ponteiro que agora pode escolher um fantasma começou: num bloco
	 *  (soltar em cima espira; para escolher, move até o fantasma) ou já num
	 *  fantasma (o toque pós-espiada, escolhe direto). */
	let origemPressao: 'bloco' | 'fantasma' | null = null;
	let posPressao = { x: 0, y: 0 };

	const faixa = $derived(faixaHoraria(items, start, end));
	const dias = $derived(layoutSemana(items));

	const altura = $derived((faixa.end - faixa.start) * pxPerMin);
	const marcas = $derived(marcasHorarias(faixa));

	/** Só desenha o intervalo se ele estiver dentro da faixa visível. */
	const almoco = $derived(
		intervalo && intervalo.end > faixa.start && intervalo.start < faixa.end ? intervalo : null
	);

	/**
	 * Régua: a hora cheia que cai dentro do intervalo perde o rótulo, senão ele
	 * fica em cima do "almoço". A linha some junto — a faixa já a cobriria.
	 */
	const rotulos = $derived(
		almoco ? marcas.filter((m) => m <= almoco.start || m >= almoco.end) : marcas
	);

	/** Um horário alternativo de outra turma da cadeira segurada. */
	interface Fantasma {
		letter: string;
		cor: GradeColor;
		/** Trocar para esta turma cria conflito com o resto da grade. */
		conflita: boolean;
		d: number;
		session: Session;
		lane: number;
		lanes: number;
	}

	/**
	 * Fantasmas por dia: para cada turma alternativa da cadeira segurada, o layout
	 * é recalculado como se ela já estivesse ativa — o que dá a posição exata em
	 * que os blocos cairiam, colunas de sobreposição incluídas. Ver o layout
	 * simulado também resolve o conflito: um fantasma vermelho avisa antes do soltar.
	 */
	const fantasmasPorDia = $derived.by<Fantasma[][]>(() => {
		const vazio = Array.from({ length: 6 }, () => [] as Fantasma[]);
		if (!arrastando || !onescolher) return vazio;

		const item = items.find((i) => i.course.code === arrastando);
		if (!item) return vazio;

		for (const cand of item.course.turmas) {
			if (cand.letter === item.turma.letter) continue;

			const simulado = items.map((i) =>
				i.course.code === item.course.code ? { ...i, turma: cand } : i
			);
			const conflita = turmaConflita?.(item.course.code, cand.letter) ?? false;

			layoutSemana(simulado).forEach((blocos, d) => {
				for (const bloco of blocos) {
					if (bloco.item.course.code !== item.course.code) continue;
					vazio[d].push({
						letter: cand.letter,
						cor: item.color,
						conflita: conflita || bloco.conflicting,
						d,
						session: bloco.session,
						lane: bloco.lane,
						lanes: bloco.lanes
					});
				}
			});
		}

		return vazio;
	});

	/** No modo "segurar", um toque fora dos fantasmas encerra a visualização. */
	$effect(() => {
		if (!arrastando || !segurando) return;

		const fechar = (event: Event) => {
			if (ignorarProximoClick) {
				ignorarProximoClick = false;
				return;
			}
			const alvo = event.target as HTMLElement | null;
			if (alvo?.closest?.('[data-fantasma]')) return;
			fecharPressao();
		};
		window.addEventListener('click', fechar);
		return () => window.removeEventListener('click', fechar);
	});

	function fecharPressao(): void {
		arrastando = null;
		segurando = false;
		ignorarProximoClick = false;
	}

	/** Distância do topo da coluna, em px, para um horário em minutos. */
	function topo(minutos: number): number {
		return (minutos - faixa.start) * pxPerMin;
	}

	function iniciarPressao(code: string): void {
		cancelarPressao();
		timerPressionar = setTimeout(() => {
			arrastando = code;
			segurando = true;
			ignorarProximoClick = true;
		}, 300);
	}

	function cancelarPressao(): void {
		clearTimeout(timerPressionar);
	}

	/**
	 * No toque, o navegador captura o ponteiro no elemento tocado: todos os
	 * `pointerup` voltariam ao bloco, nunca ao fantasma embaixo do dedo.
	 * Soltar a captura devolve os eventos ao elemento sob o dedo.
	 */
	function soltarCaptura(event: PointerEvent): void {
		try {
			(event.currentTarget as HTMLElement).releasePointerCapture(event.pointerId);
		} catch {
			/* sem captura implícita (mouse) */
		}
	}

	function iniciarArrasto(event: DragEvent, code: string): void {
		cancelarPressao();
		segurando = false;
		arrastando = code;
		event.dataTransfer?.setData('text/plain', code);
		if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
	}

	function encerrarArrasto(): void {
		arrastando = null;
		segurando = false;
	}

	function escolherFantasma(code: string, letter: string): void {
		fecharPressao();
		piscar(code);
		onescolher?.(code, letter);
	}

	/**
	 * Soltar o ponteiro sobre um fantasma só escolhe a turma se o gesto foi de
	 * fato até ele: o ponteiro começou no fantasma (toque pós-espiada) ou
	 * percorreu mais de 8px desde o bloco (segurar → deslizar → soltar). Sem
	 * isso, soltar o "segurar" em cima do bloco — que o fantasma do mesmo
	 * horário cobre — trocaria a turma sem querer.
	 */
	function podeEscolherNoToque(event: PointerEvent | MouseEvent): boolean {
		if (origemPressao === 'fantasma') return true;
		if (origemPressao !== 'bloco') return false;
		const dx = event.clientX - posPressao.x;
		const dy = event.clientY - posPressao.y;
		return Math.hypot(dx, dy) > 8;
	}

	function piscar(code: string): void {
		piscando = code;
		clearTimeout(timerPiscada);
		timerPiscada = setTimeout(() => (piscando = null), 700);
	}

	/** Texto completo do bloco — o que não coube no espaço visível vai no `title`. */
	function legenda({ item, session, conflicting }: Bloco, escolhivel = true): string {
		const { course, turma } = item;
		const partes = [
			`${course.name} (${course.code})`,
			`Turma ${turma.letter}`,
			`${DAY_NAMES[session.day]} ${formatHora(session.start)}–${formatHora(session.end)}`
		];
		if (turma.campus) partes.push(turma.campus);
		if (turma.local) partes.push(turma.local);
		if (conflicting) partes.push('conflito de horário');
		if (!escolhivel) partes.push('única turma ofertada');
		return partes.join(' · ');
	}

	/** Texto do fantasma no `title` — o que ele é e para onde leva. */
	function legendaFantasma(f: Fantasma): string {
		const partes = [
			`Turma ${f.letter}`,
			`${DAY_NAMES[f.d]} ${formatHora(f.session.start)}–${formatHora(f.session.end)}`
		];
		if (f.conflita) partes.push('em conflito com a grade');
		return partes.join(' · ');
	}
</script>

<!-- Sem container: a grade se apoia nas hairlines horizontais e nos blocos
     retangulares de canto vivo. -->
<div class="text-gray-900">
	<!-- `overflow-x` também recorta na vertical: o padding evita cortar ao meio o
	     rótulo da última hora, que fica centrado na linha final. -->
	<div class="overflow-x-auto pb-2">
		<div
			class="grid min-w-[640px] grid-cols-[52px_repeat(6,minmax(0,1fr))]"
			style:touch-action={arrastando ? 'none' : undefined}
		>
			<div></div>
			{#each DAY_ABBR as dia, d (d)}
				<div
					class="pb-2 text-center text-[11px] font-semibold tracking-wide text-gray-500 uppercase"
				>
					<abbr class="no-underline" title={DAY_NAMES[d]}>{dia}</abbr>
				</div>
			{/each}

			<!-- Régua de horas -->
			<div class="relative" style:height="{altura}px">
				{#each rotulos as marca (marca)}
					<div
						class="absolute right-2 -translate-y-1/2 text-[11px] text-gray-400 tabular-nums"
						style:top="{topo(marca)}px"
					>
						{marca / 60}h
					</div>
				{/each}

				{#if almoco}
					<div
						class="absolute right-2 -translate-y-1/2 text-[10px] text-gray-400"
						style:top="{topo((almoco.start + almoco.end) / 2)}px"
					>
						almoço
					</div>
				{/if}
			</div>

			{#each dias as blocos, d (d)}
				<div class="relative border-t border-l border-gray-200" style:height="{altura}px">
					{#each rotulos as marca (marca)}
						<div
							class="absolute inset-x-0 border-t border-gray-100"
							style:top="{topo(marca)}px"
						></div>
					{/each}

					<!-- Depois das linhas de hora e antes dos blocos: cobre a linha das 13h
					     e continua atrás de qualquer aula marcada no meio do intervalo. -->
					{#if almoco}
						<div
							class="absolute inset-x-0 border-y border-dashed border-gray-300 bg-gray-100"
							style:top="{topo(almoco.start)}px"
							style:height="{(almoco.end - almoco.start) * pxPerMin}px"
						></div>
					{/if}

					{#each blocos as bloco (`${bloco.item.course.code}-${bloco.session.start}-${bloco.session.end}`)}
						{@const { course, turma, color } = bloco.item}
						{@const { start, end } = bloco.session}
						<!-- Arrastar é escolher turma: uma disciplina com uma única turma
						     não tem para onde trocar, então o bloco não anuncia interatividade
						     que não existe. -->
						{@const escolhivel = onescolher && course.turmas.length > 1}
						<div
							draggable={escolhivel ? 'true' : undefined}
							class="absolute overflow-hidden rounded-none border-solid px-1.5 py-1 select-none {escolhivel
								? arrastando === course.code
									? 'cursor-grabbing opacity-50'
									: 'cursor-grab'
									: 'cursor-default'} {piscando === course.code ? 'troca-flash' : ''}"
							style:top="{topo(start)}px"
							style:height="{(end - start) * pxPerMin - 2}px"
							style:left="calc({(bloco.lane / bloco.lanes) * 100}% + 2px)"
							style:width="calc({100 / bloco.lanes}% - 4px)"
							style:background={color.bg}
							style:border-width="{bloco.conflicting ? 2 : 1}px"
							style:border-color={bloco.conflicting ? CONFLICT_BORDER : color.border}
							style:color={color.text}
							title={legenda(bloco, escolhivel)}
							ondragstart={(event) => iniciarArrasto(event, course.code)}
							ondragend={encerrarArrasto}
							onpointerdown={(event) => {
								if (!escolhivel) return;
								origemPressao = 'bloco';
								posPressao = { x: event.clientX, y: event.clientY };
								iniciarPressao(course.code);
								soltarCaptura(event);
							}}
							onpointerup={cancelarPressao}
							onpointermove={cancelarPressao}
							onpointercancel={cancelarPressao}
							>
							<div class="text-[11px] leading-tight font-medium">
								{course.name} <span class="opacity-70">({turma.letter})</span>
							</div>
							<div class="text-[10px] opacity-85">{formatHora(start)}–{formatHora(end)}</div>
						</div>
					{/each}

					<!-- Horários alternativos da cadeira segurada. Pontilhado; vermelho
					     quando trocar para ali criaria conflito. -->
					{#if fantasmasPorDia[d].length}
						{#each fantasmasPorDia[d] as f (`${f.letter}-${f.d}-${f.session.start}`)}
							<div
								data-fantasma
								role="button"
								tabindex="0"
								aria-label={legendaFantasma(f)}
								class="absolute z-10 flex flex-col items-center justify-center overflow-hidden rounded-none border-2 border-dashed px-1 py-0.5 transition-colors {segurando
									? 'cursor-pointer hover:bg-gray-100/60'
									: ''}"
								style:top="{topo(f.session.start)}px"
								style:height="{(f.session.end - f.session.start) * pxPerMin - 4}px"
								style:left="calc({(f.lane / f.lanes) * 100}% + 2px)"
								style:width="calc({100 / f.lanes}% - 4px)"
								style:border-color={f.conflita ? CONFLICT_BORDER : f.cor.border}
								style:color={f.conflita ? CONFLICT_BORDER : f.cor.border}
								title={legendaFantasma(f)}
								ondragover={(event) => {
									event.preventDefault();
									if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
								}}
								ondrop={(event) => {
									event.preventDefault();
									if (arrastando) escolherFantasma(arrastando, f.letter);
								}}
								onclick={(event) =>
								segurando && arrastando && podeEscolherNoToque(event)
									? escolherFantasma(arrastando, f.letter)
									: undefined}
							onpointerdown={(event) => {
								origemPressao = 'fantasma';
								posPressao = { x: event.clientX, y: event.clientY };
							}}
							onpointerup={(event) => {
								if (segurando && arrastando && podeEscolherNoToque(event)) {
									escolherFantasma(arrastando, f.letter);
								}
							}}
								onkeydown={(event) => {
									if (event.key === 'Enter' || event.key === ' ') {
										event.preventDefault();
										if (arrastando) escolherFantasma(arrastando, f.letter);
									}
								}}
							>
								<span class="font-mono text-[10px] font-semibold uppercase tracking-wider">
									turma {f.letter}
								</span>
								<span class="font-mono text-[10px] tabular-nums">
									{formatHora(f.session.start)}–{formatHora(f.session.end)}
								</span>
							</div>
						{/each}
					{/if}
				</div>
			{/each}
		</div>
	</div>
</div>
