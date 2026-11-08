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
	<p
		class="rounded-lg border border-dashed border-slate-200 px-3 py-4 text-center text-xs text-slate-400"
	>
		Nenhuma disciplina na grade — adicione pelo catálogo.
	</p>
{:else}
	<ul class="space-y-2">
		{#each items as { course, turma, color } (course.code)}
			{@const emConflito = turmaConflita?.(course.code, turma.letter) ?? false}
			<li class="rounded-lg border border-slate-200 bg-white p-2.5 shadow-sm">
				<div class="flex items-start justify-between gap-2">
					<div class="min-w-0">
						<p class="truncate text-sm font-medium text-slate-900" title={course.name}>
							{course.name}
						</p>
						<p class="text-[11px] text-slate-500">
							{course.code} · {course.credits} créditos
							{#if emConflito}
								<span class="font-medium text-red-600">· em conflito</span>
							{/if}
						</p>
					</div>
					<button
						type="button"
						aria-label="Remover {course.name}"
						title="Remover da grade"
						class="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-500 transition-colors hover:border-red-400 hover:text-red-600"
						onclick={() => onremover(course.code)}
					>
						✕
					</button>
				</div>

				<div class="mt-1.5 flex flex-wrap gap-1.5">
					{#each course.turmas as opcao (opcao.letter)}
						{@const ativa = opcao.letter === turma.letter}
						{@const conflita = turmaConflita?.(course.code, opcao.letter) ?? false}
						<button
							type="button"
							aria-pressed={ativa}
							title={legenda(opcao, conflita)}
							class="rounded-md border px-2 py-1 text-xs transition-colors"
							class:border-dashed={conflita && !ativa}
							class:bg-slate-50={!ativa}
							class:text-slate-500={!ativa}
							style:border-color={ativa
								? conflita
									? CONFLICT_BORDER
									: color.border
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
