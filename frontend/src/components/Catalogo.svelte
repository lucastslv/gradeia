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

<aside class="w-full shrink-0 xl:w-72 xl:border-r xl:border-slate-300 xl:pr-6">
	<div class="flex items-baseline justify-between gap-2">
		<h2 class="text-sm font-semibold text-slate-900">Catálogo</h2>
		<span class="font-mono text-[11px] tabular-nums text-slate-400">
			{filtrados.length}/{courses.length}
		</span>
	</div>

	<input
		type="search"
		bind:value={query}
		placeholder="Buscar disciplina ou sigla"
		class="mt-3 w-full rounded-none border border-slate-900 px-2.5 py-1.5 text-sm placeholder:text-slate-400 focus:border-[#00539F] focus:shadow-[2px_2px_0_0_#00539F] focus:outline-none"
	>

	<div class="mt-2 space-y-2">
		<select
			bind:value={estado}
			class="w-full rounded-none border border-slate-900 px-2 py-1.5 text-xs focus:border-[#00539F] focus:shadow-[2px_2px_0_0_#00539F] focus:outline-none"
		>
			<option value="todas">Todos os estados</option>
			<option value="ofertada">Ofertadas</option>
			<option value="nao_ofertada">Não ofertadas</option>
			<option value="nao_publicado">Não publicadas</option>
		</select>
		<select
			bind:value={carater}
			class="w-full rounded-none border border-slate-900 px-2 py-1.5 text-xs focus:border-[#00539F] focus:shadow-[2px_2px_0_0_#00539F] focus:outline-none"
		>
			<option value="todos">Todos os caráteres</option>
			<option value="Obrigatória">Obrigatórias</option>
			<option value="Eletiva">Eletivas</option>
		</select>
	</div>

	<ul class="mt-4 max-h-[30rem] divide-y divide-slate-100 overflow-y-auto pr-1">
		{#each filtrados as course (course.code)}
			<li class="py-2.5 first:pt-0">
				<div class="flex items-start justify-between gap-3">
					<div class="min-w-0">
						<p class="truncate text-sm font-medium text-slate-900" title={course.name}>
							{course.name}
						</p>
						<p class="mt-0.5 font-mono text-[11px] text-slate-500">
							{course.code} · {course.credits}cr · {course.carater}
							{#if course.etapa !== null} · et{course.etapa}{/if}
						</p>
					</div>

					{#if course.estado === 'ofertada'}
						{#if selecionadas.includes(course.code)}
							<span class="shrink-0 font-mono text-[11px] font-semibold uppercase tracking-wider text-[#00539F]">
								na grade
							</span>
						{:else}
							<button
								type="button"
								title="Adicionar à grade"
								class="shrink-0 rounded-none border border-slate-900 px-2 py-0.5 text-xs font-semibold text-slate-900 transition-colors hover:bg-slate-900 hover:text-white"
								onclick={() => onadd(course)}
							>
								+
							</button>
						{/if}
					{:else}
						<span class="shrink-0 font-mono text-[11px] uppercase tracking-wider text-slate-400">
							{rotuloEstado(course.estado)}
						</span>
					{/if}
				</div>
			</li>
		{:else}
			<li class="py-3 font-mono text-[11px] uppercase tracking-wider text-slate-400">
				Nenhuma disciplina com esses filtros.
			</li>
		{/each}
	</ul>
</aside>
