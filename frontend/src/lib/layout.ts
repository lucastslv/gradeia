import { sessionsOverlap } from './conflicts';
import type { GradeItem } from './grade.svelte';
import { DAY_ABBR, DAY_NAMES, type Session } from './types';

/**
 * Cálculo de posição dos blocos da grade semanal: em que dia cada sessão cai,
 * em que faixa de horas a grade precisa caber e, quando duas aulas se cruzam,
 * em qual coluna cada uma é desenhada. É lógica pura — o componente só traduz
 * o resultado em CSS. Junto vêm os formatadores de horário, que a grade e os
 * chips de turma mostram no mesmo formato.
 */

/** Uma sessão de uma turma ativa, já posicionada dentro do seu dia. */
export interface Bloco {
	item: GradeItem;
	session: Session;
	/** Coluna do bloco dentro do dia; 0 é a mais à esquerda. */
	lane: number;
	/** Quantas colunas o grupo sobreposto ocupa. 1 quando o bloco está sozinho. */
	lanes: number;
	/** O bloco cruza o horário de alguma outra cadeira neste dia. */
	conflicting: boolean;
}

/** Um trecho do dia, em minutos desde meia-noite — como em `Session`. */
export interface Faixa {
	start: number;
	end: number;
}

const DIAS = 6;

/**
 * Faixa visível por padrão: 8:30 às 17:30, que é onde cabe praticamente toda
 * aula de graduação. Não é um limite — `faixaHoraria` estica para caber o que
 * ficar de fora.
 */
export const FAIXA_PADRAO: Faixa = { start: 8 * 60 + 30, end: 17 * 60 + 30 };

/** Intervalo de almoço, desenhado como faixa separadora atrás dos blocos. */
export const ALMOCO: Faixa = { start: 12 * 60 + 10, end: 13 * 60 + 30 };

/**
 * Blocos de cada dia da semana, indexados por `day` (0=Segunda … 5=Sábado).
 * Sempre devolve seis listas, mesmo que vazias.
 */
export function layoutSemana(items: readonly GradeItem[]): Bloco[][] {
	return Array.from({ length: DIAS }, (_, day) => layoutDia(items, day));
}

/**
 * Blocos de um dia, ordenados por horário de início. Aulas que se sobrepõem são
 * distribuídas em colunas lado a lado — sem isso uma esconderia a outra, que é
 * justamente o caso que o usuário precisa enxergar.
 */
export function layoutDia(items: readonly GradeItem[], day: number): Bloco[] {
	const blocos: Bloco[] = items
		.flatMap((item) =>
			item.turma.sessions
				.filter((session) => session.day === day)
				.map((session) => ({ item, session, lane: 0, lanes: 1, conflicting: false }))
		)
		.sort((a, b) => a.session.start - b.session.start || a.session.end - b.session.end);

	for (const bloco of blocos) {
		bloco.conflicting = blocos.some(
			(outro) =>
				outro.item.course.code !== bloco.item.course.code &&
				sessionsOverlap(bloco.session, outro.session)
		);
	}

	distribuirColunas(blocos);
	return blocos;
}

/**
 * Faixa visível: `min`..`max`, esticada para caber qualquer aula que caia fora
 * dela (a UFRGS já mexeu nos turnos, e um bloco fora da faixa seria desenhado
 * por cima do cabeçalho). O que estica vai até a hora cheia, para a régua não
 * começar num horário quebrado que ninguém pediu.
 */
export function faixaHoraria(
	items: readonly GradeItem[],
	min = FAIXA_PADRAO.start,
	max = FAIXA_PADRAO.end
): Faixa {
	let inicio = min;
	let fim = max;

	for (const { turma } of items) {
		for (const { start, end } of turma.sessions) {
			if (start < inicio) inicio = Math.floor(start / 60) * 60;
			if (end > fim) fim = Math.ceil(end / 60) * 60;
		}
	}

	return { start: inicio, end: Math.max(fim, inicio + 60) };
}

/**
 * Horas cheias dentro da faixa, em minutos — onde vão as linhas e os rótulos da
 * régua. Uma faixa que começa 8:30 tem a primeira marca às 9h.
 */
export function marcasHorarias({ start, end }: Faixa): number[] {
	const marcas: number[] = [];
	for (let minuto = Math.ceil(start / 60) * 60; minuto <= end; minuto += 60) marcas.push(minuto);
	return marcas;
}

/** Minutos desde meia-noite no formato "08:30". */
export function formatHora(minutos: number): string {
	const h = Math.floor(minutos / 60);
	const m = minutos % 60;
	return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

/**
 * Horários de uma turma em uma linha: "Seg 08:30–10:10, Qua 08:30–10:10". Vazio
 * quando a turma não tem sessões — o parser guarda turmas cujo horário não deu
 * para ler, e quem chama decide o que dizer no lugar.
 */
export function formatSessoes(sessions: readonly Session[], abreviado = true): string {
	const dias = abreviado ? DAY_ABBR : DAY_NAMES;

	return sessions
		.map(({ day, start, end }) => `${dias[day] ?? '?'} ${formatHora(start)}–${formatHora(end)}`)
		.join(', ');
}

/**
 * Preenche `lane`/`lanes` in-place. Blocos que se encavalam formam um grupo;
 * dentro do grupo cada bloco entra na primeira coluna já livre no seu horário,
 * e todos compartilham a mesma largura para ficarem alinhados.
 */
function distribuirColunas(blocos: Bloco[]): void {
	let grupo: Bloco[] = [];
	/** Fim da última aula de cada coluna do grupo atual. */
	let fins: number[] = [];

	const fecharGrupo = () => {
		for (const bloco of grupo) bloco.lanes = fins.length;
		grupo = [];
		fins = [];
	};

	for (const bloco of blocos) {
		// Nenhuma coluna ainda ocupada neste horário: o grupo anterior terminou.
		if (fins.every((fim) => fim <= bloco.session.start)) fecharGrupo();

		const livre = fins.findIndex((fim) => fim <= bloco.session.start);
		bloco.lane = livre === -1 ? fins.length : livre;
		fins[bloco.lane] = bloco.session.end;
		grupo.push(bloco);
	}

	fecharGrupo();
}
