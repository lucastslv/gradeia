<script lang="ts">
	import { CONFLICT_BORDER } from '$lib/colors';
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
	import { DAY_ABBR, DAY_NAMES } from '$lib/types';

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
	}

	let {
		items,
		start = FAIXA_PADRAO.start,
		end = FAIXA_PADRAO.end,
		pxPerMin = 1.3,
		intervalo = ALMOCO
	}: Props = $props();

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

	/** Distância do topo da coluna, em px, para um horário em minutos. */
	function topo(minutos: number): number {
		return (minutos - faixa.start) * pxPerMin;
	}

	/** Texto completo do bloco — o que não coube no espaço visível vai no `title`. */
	function legenda({ item, session, conflicting }: Bloco): string {
		const { course, turma } = item;
		const partes = [
			`${course.name} (${course.code})`,
			`Turma ${turma.letter}`,
			`${DAY_NAMES[session.day]} ${formatHora(session.start)}–${formatHora(session.end)}`
		];
		if (turma.campus) partes.push(turma.campus);
		if (turma.local) partes.push(turma.local);
		if (conflicting) partes.push('conflito de horário');
		return partes.join(' · ');
	}
</script>

<!-- Ilha clara dentro da página escura: a grade mantém o fundo branco para as
     cores das cadeiras (pensadas para fundo claro) continuarem legíveis. -->
<div class="rounded-xl border border-slate-200 bg-white p-3 text-gray-900 shadow-sm sm:p-4">
	<!-- `overflow-x` também recorta na vertical: o padding evita cortar ao meio o
	     rótulo da última hora, que fica centrado na linha final. -->
	<div class="overflow-x-auto pb-2">
		<div class="grid min-w-[640px] grid-cols-[52px_repeat(6,minmax(0,1fr))]">
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
						<div
							class="absolute overflow-hidden rounded-md border-solid px-1.5 py-1"
							style:top="{topo(start)}px"
							style:height="{(end - start) * pxPerMin - 2}px"
							style:left="calc({(bloco.lane / bloco.lanes) * 100}% + 2px)"
							style:width="calc({100 / bloco.lanes}% - 4px)"
							style:background={color.bg}
							style:border-width="{bloco.conflicting ? 2 : 1}px"
							style:border-color={bloco.conflicting ? CONFLICT_BORDER : color.border}
							style:color={color.text}
							title={legenda(bloco)}
						>
							<div class="text-[11px] leading-tight font-medium">
								{course.name} <span class="opacity-70">({turma.letter})</span>
							</div>
							<div class="text-[10px] opacity-85">{formatHora(start)}–{formatHora(end)}</div>
						</div>
					{/each}
				</div>
			{/each}
		</div>
	</div>
</div>
