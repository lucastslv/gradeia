<script lang="ts">
	import { CONFLICT_BORDER } from '$lib/colors';
	import type { GradeItem } from '$lib/grade.svelte';
	import { formatSessoes } from '$lib/layout';
	import type { Turma } from '$lib/types';

	interface Props {
		items: GradeItem[];
		onescolher: (code: string, letter: string) => void;
		onremover: (code: string) => void;
		turmaConflita?: (code: string, letter: string) => boolean;
	}

	let { items, onescolher, onremover, turmaConflita }: Props = $props();

	function legenda(turma: Turma, conflita: boolean): string {
		const partes = [`Turma ${turma.letter}`];
		if (turma.campus) partes.push(turma.campus);
		if (turma.local) partes.push(turma.local);
		if (turma.sessions.length === 0) partes.push('horário não reconhecido');
		if (conflita) partes.push('conflita com o resto da grade');
		return partes.join(' · ');
	}
</script>

{#if items.length === 0}
	<p class="py-4 font-mono text-[11px] uppercase tracking-wider text-slate-400">
		Nenhuma disciplina na grade — adicione pelo catálogo.
	</p>
{:else}
	<ul class="divide-y divide-slate-200">
		{#each items as { course, turma, color } (course.code)}
			{@const emConflito = turmaConflita?.(course.code, turma.letter) ?? false}
			<li class="py-3 first:pt-0">
				<div class="flex items-start justify-between gap-2">
					<div class="min-w-0">
						<p class="truncate text-sm font-medium text-slate-900" title={course.name}>
							{course.name}
						</p>
						<p class="mt-0.5 font-mono text-[11px] text-slate-500">
							{course.code} · {course.credits}cr
							{#if emConflito}
								<span class="font-semibold text-[#CE1126]">· em conflito</span>
							{/if}
						</p>
					</div>
					<button
						type="button"
						aria-label="Remover {course.name}"
						title="Remover da grade"
						class="shrink-0 rounded-none border border-slate-300 px-2 py-0.5 text-xs text-slate-500 transition-colors hover:border-[#CE1126] hover:text-[#CE1126]"
						onclick={() => onremover(course.code)}
					>
						✕
					</button>
				</div>

				<div class="mt-2 flex flex-wrap gap-1.5">
					{#each course.turmas as opcao (opcao.letter)}
						{@const ativa = opcao.letter === turma.letter}
						{@const conflita = turmaConflita?.(course.code, opcao.letter) ?? false}
						<button
							type="button"
							aria-pressed={ativa}
							title={legenda(opcao, conflita)}
							class="rounded-none border px-2 py-1 text-xs transition-colors"
							class:border-dashed={conflita && !ativa}
							class:border-slate-300={!ativa}
							class:text-slate-500={!ativa}
							class:hover:border-slate-900={!ativa}
							style:border-color={ativa
								? conflita
									? CONFLICT_BORDER
									: '#0f172a'
								: undefined}
							style:background={ativa ? color.bg : undefined}
							style:color={ativa ? color.text : undefined}
							onclick={() => onescolher(course.code, opcao.letter)}
						>
							Turma {opcao.letter} · {formatSessoes(opcao.sessions) || 'sem horário'}
						</button>
					{/each}
				</div>
			</li>
		{/each}
	</ul>
{/if}
