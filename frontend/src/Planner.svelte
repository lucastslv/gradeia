<script lang="ts">
	import { onMount } from 'svelte';
	import Catalogo from './components/Catalogo.svelte';
	import GradeSemanal from './components/GradeSemanal.svelte';
	import SeletorTurmas from './components/SeletorTurmas.svelte';
	import { Grade } from '$lib/grade.svelte';
	import type { Course } from '$lib/types';

	interface Props {
		endpoint: string;
		saveUrl: string;
	}

	interface PlannerData {
		analise_id: string;
		curso: string;
		periodo: string;
		periodo_publicado: boolean;
		cursos: Course[];
		plano: { code: string; letter: string }[];
	}

	let { endpoint, saveUrl }: Props = $props();

	let dados = $state<PlannerData | null>(null);
	let erro = $state('');
	let pronto = $state(false);
	let salvando = $state(false);
	let salvo = $state(true);
	let ultimoPlano = $state('');
	const grade = new Grade();

	onMount(async () => {
		try {
			const response = await fetch(endpoint);
			if (!response.ok) throw new Error(`HTTP ${response.status}`);
			const data: PlannerData = await response.json();

			for (const escolha of data.plano) {
				const course = data.cursos.find((c) => c.code === escolha.code);
				if (course) grade.adicionarCadeira(course, escolha.letter);
			}

			ultimoPlano = serializar(data.plano);
			dados = data;
		} catch (error) {
			erro = error instanceof Error ? error.message : 'Não foi possível carregar o planejador.';
		} finally {
			pronto = true;
		}
	});

	onMount(() => {
		const handler = (event: Event) => {
			const detalhe = (event as CustomEvent<{ plano?: { code: string; letter: string }[] }>)
				.detail;
			if (detalhe?.plano) aplicarPlano(detalhe.plano);
		};

		window.addEventListener('plano-atualizado', handler);
		return () => window.removeEventListener('plano-atualizado', handler);
	});

	function serializar(plano: { code: string; letter: string }[]): string {
		return JSON.stringify(plano);
	}

	/** Aplica um plano alterado pelo chat sem disparar um PUT de volta. */
	function aplicarPlano(plano: { code: string; letter: string }[]): void {
		if (!dados) return;

		ultimoPlano = serializar(plano);
		salvo = true;
		grade.limpar();

		for (const escolha of plano) {
			const course = dados.cursos.find((c) => c.code === escolha.code);
			if (course) grade.adicionarCadeira(course, escolha.letter);
		}
	}

	let timer: ReturnType<typeof setTimeout> | undefined;

	$effect(() => {
		const escolhas = grade.items.map((item) => ({
			code: item.course.code,
			letter: item.turma.letter
		}));
		const chave = serializar(escolhas);
		if (!pronto || !dados || chave === ultimoPlano) return;

		salvo = false;
		clearTimeout(timer);
		timer = setTimeout(async () => {
			salvando = true;
			try {
				const response = await fetch(saveUrl, {
					method: 'PUT',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ escolhas })
				});
				if (!response.ok) throw new Error(`HTTP ${response.status}`);
				ultimoPlano = chave;
				salvo = true;
			} catch {
				salvo = false;
			} finally {
				salvando = false;
			}
		}, 500);
	});

	const selecionadas = $derived(grade.items.map((item) => item.course.code));

	function adicionar(course: Course): void {
		grade.adicionarCadeira(course);
	}

	function escolher(code: string, letter: string): void {
		grade.escolherTurma(code, letter);
	}

	function remover(code: string): void {
		grade.removerCadeira(code);
	}
</script>

{#if erro}
	<p class="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{erro}</p>
{:else if !dados}
	<p class="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-500">
		Carregando planejador…
	</p>
{:else}
	<div class="flex flex-col gap-4 xl:flex-row xl:items-start">
		<Catalogo courses={dados.cursos} {selecionadas} onadd={adicionar} />

		<div class="min-w-0 flex-1 space-y-3">
			<div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
				<span class="text-sm font-medium text-slate-900">{dados.curso}</span>
				<span>{dados.periodo}</span>
				<span>{grade.credits} créditos na grade</span>
				<span
					class:text-emerald-700={salvo && !salvando}
					class:text-amber-700={!salvo && !salvando}
				>
					{salvando ? 'salvando…' : salvo ? 'salvo' : 'não salvo'}
				</span>
			</div>

			<SeletorTurmas
				items={grade.items}
				onescolher={escolher}
				onremover={remover}
				turmaConflita={(code, letter) => grade.turmaConflita(code, letter)}
			/>

			{#if grade.hasConflict}
				<p class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
					{grade.conflicts.length} conflito(s) de horário — troque a turma de uma delas.
				</p>
			{/if}

			<GradeSemanal items={grade.items} />
		</div>
	</div>
{/if}
