<script lang="ts">
	import type { Course } from '$lib/types';

	interface Props {
		courses: Course[];
		selecionadas: string[];
		onadd: (course: Course) => void;
	}

	let { courses, selecionadas, onadd }: Props = $props();

	let query = $state('');
	let estado = $state('todas');
	let carater = $state('todos');

	function normalizar(texto: string): string {
		return texto
			.toLowerCase()
			.normalize('NFD')
			.replace(/[\u0300-\u036f]/g, '');
	}

	const filtrados = $derived.by(() => {
		const alvo = normalizar(query.trim());
		return courses.filter((course) => {
			if (estado !== 'todas' && course.estado !== estado) return false;
			if (carater !== 'todos' && normalizar(course.carater) !== normalizar(carater)) {
				return false;
			}
			if (
				alvo &&
				!normalizar(course.name).includes(alvo) &&
				!course.code.toLowerCase().includes(alvo)
			) {
				return false;
			}
			return true;
		});
	});

	function rotuloEstado(estado: string): string {
		if (estado === 'nao_ofertada') return 'não ofertada';
		if (estado === 'nao_publicado') return 'não publicado';
		return 'ofertada';
	}
</script>

<aside
	class="w-full shrink-0 rounded-xl border border-slate-200 bg-white p-3 shadow-sm xl:w-72"
>
	<div class="flex items-baseline justify-between gap-2">
		<h2 class="text-sm font-semibold text-slate-900">Catálogo</h2>
		<span class="text-[11px] text-slate-500">{filtrados.length} de {courses.length}</span>
	</div>

	<input
		type="search"
		bind:value={query}
		placeholder="Buscar disciplina ou sigla"
		class="mt-2 w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm shadow-sm focus:border-emerald-500 focus:outline-none"
	>

	<div class="mt-2 space-y-1.5">
		<select
			bind:value={estado}
			class="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-xs shadow-sm focus:border-emerald-500 focus:outline-none"
		>
			<option value="todas">Todos os estados</option>
			<option value="ofertada">Ofertadas</option>
			<option value="nao_ofertada">Não ofertadas</option>
			<option value="nao_publicado">Não publicadas</option>
		</select>
		<select
			bind:value={carater}
			class="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-xs shadow-sm focus:border-emerald-500 focus:outline-none"
		>
			<option value="todos">Todos os caráteres</option>
			<option value="Obrigatória">Obrigatórias</option>
			<option value="Eletiva">Eletivas</option>
		</select>
	</div>

	<ul class="mt-3 max-h-[30rem] space-y-1 overflow-y-auto pr-1">
		{#each filtrados as course (course.code)}
			<li class="rounded-lg border border-slate-100 p-2">
				<div class="flex items-start justify-between gap-2">
					<div class="min-w-0">
						<p class="truncate text-sm font-medium text-slate-900" title={course.name}>
							{course.name}
						</p>
						<p class="text-[11px] text-slate-500">
							{course.code} · {course.credits} créditos · {course.carater}
							{#if course.etapa !== null}· etapa {course.etapa}{/if}
						</p>
					</div>

					{#if course.estado === 'ofertada'}
						{#if selecionadas.includes(course.code)}
							<span class="shrink-0 text-[11px] font-medium text-emerald-700">na grade</span>
						{:else}
							<button
								type="button"
								title="Adicionar à grade"
								class="shrink-0 rounded-md border border-slate-300 px-2 py-1 text-xs font-medium text-slate-600 transition-colors hover:border-emerald-500 hover:text-emerald-700"
								onclick={() => onadd(course)}
							>
								+
							</button>
						{/if}
					{:else}
						<span class="shrink-0 text-[11px] text-slate-400">
							{rotuloEstado(course.estado)}
						</span>
					{/if}
				</div>
			</li>
		{:else}
			<li class="px-1 py-3 text-xs text-slate-400">Nenhuma disciplina com esses filtros.</li>
		{/each}
	</ul>
</aside>
